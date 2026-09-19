import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  Bot,
  ChevronRight,
  ExternalLink,
  Loader2,
  Minus,
  Send,
  Sparkles,
  User,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { sendChatMessage } from '../services/api';
import './AIChatAssistant.css';

function renderInline(text) {
  return text.split(/(\*\*.*?\*\*)/g).map((part, index) => (
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={index}>{part.slice(2, -2)}</strong>
      : <span key={index}>{part}</span>
  ));
}

function MessageContent({ text }) {
  return (
    <div className="ai-md">
      {(text || '').split('\n').map((line, index) => {
        if (line.startsWith('## ')) return <h4 key={index}>{line.slice(3)}</h4>;
        if (line.startsWith('### ')) return <h5 key={index}>{line.slice(4)}</h5>;
        if (/^\|[\s-:|]+\|$/.test(line)) return null;
        if (line.startsWith('|') && line.endsWith('|')) {
          return <div key={index} className="ai-md-row">{line.split('|').filter(Boolean).map((cell, cellIndex) => <span key={cellIndex}>{renderInline(cell.trim())}</span>)}</div>;
        }
        if (/^[-•] /.test(line)) return <div key={index} className="ai-md-list">• {renderInline(line.slice(2))}</div>;
        return <div key={index} className={line ? '' : 'ai-md-space'}>{renderInline(line)}</div>;
      })}
    </div>
  );
}

function welcomeMessage(user) {
  const firstName = user?.name?.split(' ')[0];
  return `Hello${firstName ? `, ${firstName}` : ''}! I'm **LogicCore AI**, your Project Intelligence Assistant. I can help with portfolio analytics, project details, risk assessments, alerts, sector comparisons, and audit history.`;
}

export default function AIChatAssistant() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);

  const openChat = () => {
    setOpen(true);
    if (!messages.length) {
      setMessages([{ role: 'assistant', content: welcomeMessage(user) }]);
      setSuggestions(['Show portfolio overview', 'Which projects are high risk?', 'What are the current alerts?', user?.role === 'inspector' ? 'Show my assigned projects' : 'Show sector analytics']);
    }
  };

  const send = async (suggestedText = input) => {
    const message = suggestedText.trim();
    if (!message || loading) return;
    setInput('');
    setSuggestions([]);
    setMessages(previous => [...previous, { role: 'user', content: message }]);
    setLoading(true);
    try {
      const history = messages.map(item => ({ role: item.role, content: item.content }));
      const response = await sendChatMessage(message, history, user);
      setMessages(previous => [...previous, { role: 'assistant', content: response.reply, sources: response.sources || [] }]);
      setSuggestions(response.suggested_questions || []);
    } catch (error) {
      setMessages(previous => [...previous, { role: 'assistant', content: error.message || 'The assistant is temporarily unavailable.', error: true }]);
      setSuggestions(['Show portfolio overview', 'Which projects are high risk?', 'What are the current alerts?']);
    } finally {
      setLoading(false);
    }
  };

  const openProject = (projectId) => {
    window.dispatchEvent(new CustomEvent('open-project-dossier', { detail: { projectId } }));
    setOpen(false);
  };

  if (!user) return null;
  return (
    <>
      {!open && <button className="ai-chat-fab" onClick={openChat} title="LogicCore AI Assistant" aria-label="Open AI assistant"><Sparkles size={24} /></button>}
      {open && (
        <section className="ai-chat-panel" role="dialog" aria-label="LogicCore AI Assistant">
          <header className="ai-chat-header">
            <div className="ai-chat-header-icon"><Bot size={20} /></div>
            <div className="ai-chat-header-text"><strong>LogicCore AI</strong><span>Project Intelligence</span></div>
            <div className="ai-chat-header-actions">
              <button onClick={() => setOpen(false)} title="Minimise" aria-label="Minimise"><Minus size={16} /></button>
              <button onClick={() => { setOpen(false); setMessages([]); setSuggestions([]); }} title="Close" aria-label="Close"><X size={16} /></button>
            </div>
          </header>
          <div className="ai-chat-messages">
            {messages.map((message, index) => (
              <div key={index} className={`ai-msg ${message.role === 'user' ? 'ai-msg-user' : 'ai-msg-bot'}${message.error ? ' ai-msg-error' : ''}`}>
                <div className="ai-msg-avatar">{message.role === 'user' ? <User size={14} /> : message.error ? <AlertTriangle size={14} /> : <Bot size={14} />}</div>
                <div className="ai-msg-body"><MessageContent text={message.content} />{message.sources?.length > 0 && <div className="ai-msg-sources">{message.sources.slice(0, 5).map(source => <button key={source.project_id} onClick={() => openProject(source.project_id)}><ExternalLink size={10} />{source.project_id}</button>)}</div>}</div>
              </div>
            ))}
            {loading && <div className="ai-msg ai-msg-bot"><div className="ai-msg-avatar"><Bot size={14} /></div><div className="ai-msg-body ai-typing"><span /><span /><span /></div></div>}
            <div ref={endRef} />
          </div>
          {!loading && suggestions.length > 0 && <div className="ai-chat-suggestions">{suggestions.map(suggestion => <button key={suggestion} onClick={() => send(suggestion)}><ChevronRight size={12} />{suggestion}</button>)}</div>}
          <div className="ai-chat-input-area">
            <textarea ref={inputRef} value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask about projects, risks, alerts..." rows={1} disabled={loading} />
            <button className="ai-chat-send" onClick={() => send()} disabled={!input.trim() || loading} title="Send" aria-label="Send message">{loading ? <Loader2 size={18} className="ai-spin" /> : <Send size={18} />}</button>
          </div>
          <footer className="ai-chat-footer">Powered by <strong>LogicCore AI</strong></footer>
        </section>
      )}
    </>
  );
}
