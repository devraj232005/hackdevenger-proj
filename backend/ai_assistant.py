"""LogicCore AI assistant API with role-scoped project analytics fallback."""
import json
import logging
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

import requests

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv('MOSPI_DATABASE_PATH', str(Path(__file__).with_name('paimana.db')))).expanduser()
assistant_router = APIRouter(prefix='/api/v1/assistant', tags=['AI Assistant'])
logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '').strip()
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash').strip()
GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b').strip()


def connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def current_user(x_user_id: Optional[str] = Header(None), x_user_role: Optional[str] = Header(None)):
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=401, detail='Authentication required')
    try:
        user_id = int(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail='Invalid session') from exc
    with closing(connection()) as conn:
        user = conn.execute('SELECT id, name, role FROM users WHERE id = ? AND role = ?', (user_id, x_user_role)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail='Invalid session')
    return user


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)


def scope(role: str, user_id: int):
    return (' AND assigned_officer_id = ?', [user_id]) if role == 'inspector' else ('', [])


def projects(role: str, user_id: int, risk_level: str = '', status: str = '', limit: int = 10):
    clause, params = scope(role, user_id)
    filters = [clause] if clause else []
    if risk_level in ('high', 'critical'):
        filters.append(' AND risk_score > 75')
    elif risk_level == 'medium':
        filters.append(' AND risk_score BETWEEN 50 AND 75')
    elif risk_level == 'low':
        filters.append(' AND risk_score < 50')
    if status:
        filters.append(' AND lower(status) = lower(?)')
        params.append(status)
    query = ('SELECT id, name, sector, location, status, risk_score, time_delay_prob, '
             'physical_progress, revised_cost FROM projects WHERE 1=1' + ''.join(filters) +
             ' ORDER BY risk_score DESC LIMIT ?')
    params.append(min(max(limit, 1), 20))
    with closing(connection()) as conn:
        rows = conn.execute(query, params).fetchall()
    values = [dict(row) for row in rows]
    return values, [{'project_id': row['id'], 'project_name': row['name']} for row in values]


def overview(role: str, user_id: int):
    clause, params = scope(role, user_id)
    with closing(connection()) as conn:
        row = conn.execute(
            'SELECT COUNT(*) total, COALESCE(SUM(original_cost), 0) original_cost, '
            'COALESCE(SUM(revised_cost), 0) revised_cost, COALESCE(SUM(expenditure), 0) expenditure, '
            'COALESCE(AVG(risk_score), 0) average_risk, '
            'COALESCE(SUM(CASE WHEN risk_score > 75 THEN 1 ELSE 0 END), 0) high_risk, '
            'COALESCE(SUM(CASE WHEN risk_score > 80 OR time_delay_prob > 0.7 THEN 1 ELSE 0 END), 0) alerts '
            'FROM projects WHERE 1=1' + clause, params).fetchone()
    return dict(row)


def suggestions(message: str, role: str):
    lowered = message.lower()
    if 'alert' in lowered or 'warning' in lowered:
        result = ['Show portfolio overview', 'Which sectors are riskiest?', 'List delayed projects']
    elif 'sector' in lowered:
        result = ['Show high risk projects', 'Portfolio overview', 'Current alerts']
    elif 'risk' in lowered:
        result = ['Portfolio overview', 'Show sector analytics', 'Current alerts']
    else:
        result = ['Show portfolio overview', 'Which projects are high risk?', 'What are the current alerts?']
    if role == 'inspector':
        result.append('Show my assigned projects')
    return result[:4]


def assistant_context(user: sqlite3.Row):
    role, user_id = user['role'], user['id']
    values, sources = projects(role, user_id, limit=20)
    return {
        'user_role': role,
        'portfolio': overview(role, user_id),
        'projects': values,
    }, sources


def system_prompt(user: sqlite3.Row, context: dict):
    return (
        'You are LogicCore AI, an infrastructure project intelligence assistant. '
        'Answer only from the supplied project data. Never invent project names, IDs, '
        'costs, or statistics. Use concise markdown and format money as INR Crore. '
        f"The current user role is {user['role']}. Data context:\n"
        f"{json.dumps(context, default=str)}"
    )


def ask_gemini(message: str, history: List[ChatMessage], user: sqlite3.Row, context: dict):
    if not GEMINI_API_KEY:
        raise RuntimeError('Gemini API key is not configured')
    response = requests.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent',
        params={'key': GEMINI_API_KEY},
        json={
            'system_instruction': {'parts': [{'text': system_prompt(user, context)}]},
            'contents': [
                {'role': 'user' if item.role == 'user' else 'model', 'parts': [{'text': item.content}]}
                for item in history[-6:]
            ] + [{'role': 'user', 'parts': [{'text': message}]}],
            'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 1200},
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    text = ''.join(
        part.get('text', '')
        for part in payload.get('candidates', [{}])[0].get('content', {}).get('parts', [])
    ).strip()
    if not text:
        raise RuntimeError('Gemini returned an empty response')
    return text


def ask_groq(message: str, history: List[ChatMessage], user: sqlite3.Row, context: dict):
    if not GROQ_API_KEY:
        raise RuntimeError('Groq API key is not configured')
    messages = [{'role': 'system', 'content': system_prompt(user, context)}]
    messages.extend({'role': item.role, 'content': item.content} for item in history[-6:])
    messages.append({'role': 'user', 'content': message})
    response = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
        json={'model': GROQ_MODEL, 'messages': messages, 'temperature': 0.3, 'max_tokens': 1200},
        timeout=45,
    )
    response.raise_for_status()
    text = response.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    if not text:
        raise RuntimeError('Groq returned an empty response')
    return text


async def fallback(message: str, user: sqlite3.Row):
    lowered = message.lower()
    role, user_id = user['role'], user['id']
    if any(word in lowered for word in ('overview', 'portfolio', 'dashboard', 'summary', 'total', 'how many')):
        data = overview(role, user_id)
        reply = (f"## Portfolio Overview\n\n- **Total Projects:** {data['total']}\n"
                 f"- **Original Cost:** ₹{data['original_cost']:,.2f} Cr\n"
                 f"- **Revised Cost:** ₹{data['revised_cost']:,.2f} Cr\n"
                 f"- **Expenditure:** ₹{data['expenditure']:,.2f} Cr\n"
                 f"- **Average Risk:** {data['average_risk']:.1f}%\n"
                 f"- **High Risk Projects:** {data['high_risk']}\n- **Critical Alerts:** {data['alerts']}")
        return ChatResponse(reply=reply, suggested_questions=suggestions(message, role))

    if any(word in lowered for word in ('alert', 'warning', 'critical')):
        values, sources = projects(role, user_id, risk_level='high')
        reply = 'No critical alerts found.' if not values else '## Early Warning Alerts\n\n' + ''.join(
            f"- **{row['name']}** ({row['id']}) — Risk: {row['risk_score']:.0f}% · {row['sector']}\n" for row in values)
        return ChatResponse(reply=reply, sources=sources, suggested_questions=suggestions(message, role))

    if 'delayed' in lowered or 'delay' in lowered:
        values, sources = projects(role, user_id, status='Delayed')
        reply = 'No delayed projects found.' if not values else '## Delayed Projects\n\n' + ''.join(
            f"- **{row['name']}** ({row['id']}) — Delay probability: {row['time_delay_prob']:.0%}\n" for row in values)
        return ChatResponse(reply=reply, sources=sources, suggested_questions=suggestions(message, role))

    risk = 'high' if 'high risk' in lowered or 'risky' in lowered or 'at risk' in lowered else ''
    ids = re.findall(r'PRJ[-\s]?\d+', message, re.IGNORECASE)
    if risk or ids:
        values, sources = projects(role, user_id, risk_level=risk, limit=10)
        if ids:
            requested = {item.replace(' ', '-').upper() for item in ids}
            values = [row for row in values if row['id'].upper() in requested]
            sources = [source for source in sources if source['project_id'].upper() in requested]
        reply = 'No matching projects found.' if not values else ''.join(
            f"- **{row['name']}** ({row['id']}) — Risk: {row['risk_score']:.0f}% · {row['sector']} · {row['location']}\n" for row in values)
        return ChatResponse(reply=reply, sources=sources, suggested_questions=suggestions(message, role))

    return ChatResponse(
        reply='I can help with portfolio overview, high-risk projects, alerts, delayed projects, and project IDs such as PRJ-1001.',
        suggested_questions=suggestions(message, role),
    )


@assistant_router.post('/chat', response_model=ChatResponse)
async def assistant_chat(request: ChatRequest, user: sqlite3.Row = Depends(current_user)):
    context, sources = assistant_context(user)
    if GEMINI_API_KEY:
        try:
            reply = ask_gemini(request.message, request.conversation_history, user, context)
            return ChatResponse(reply=reply, sources=sources, suggested_questions=suggestions(request.message, user['role']))
        except Exception:
            logger.error('Gemini assistant request failed; trying Groq')
    if GROQ_API_KEY:
        try:
            reply = ask_groq(request.message, request.conversation_history, user, context)
            return ChatResponse(reply=reply, sources=sources, suggested_questions=suggestions(request.message, user['role']))
        except Exception:
            logger.error('Groq assistant request failed; using local fallback')
    return await fallback(request.message, user)
