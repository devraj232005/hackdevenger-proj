# PAIMANA Infrastructure Intelligence

PAIMANA is a public infrastructure monitoring and predictive risk analytics platform. It combines a React frontend, FastAPI backend, SQLite persistence, machine-learning risk scoring, early-warning alerts, project history, role-based access, and the LogicCore AI project assistant.

## Features

### Dashboard

- Portfolio overview with total projects, original cost, revised cost, expenditure, high-risk projects, and critical alerts.
- Risk distribution and project progress visualizations.
- Sector, ministry, state, and project status analytics.
- Role-aware dashboard data for inspectors and government-affiliated viewers.
- Dark/light theme support.
- English/Hindi login experience.

### Project Management

- Project listing with search, filters, risk ranking, status, sector, location, cost, expenditure, and physical progress.
- Project dossier with full project details, risk score, delay probability, cost-overrun probability, inspection notes, and assignment information.
- Add projects with automatic ML risk assessment.
- Update project status, physical progress, revised completion date, inspection notes, and assigned inspector.
- Assign projects to inspector officers.
- Delete projects with recoverable admin backups.
- Restore or permanently delete project backups.
- Project comments with optional image uploads.
- Project audit history showing changes, actors, timestamps, and snapshots.

### Machine Learning and Alerts

- Real-time project risk prediction.
- Cost-overrun probability and time-delay probability.
- Predicted cost overrun and delay duration.
- Risk factors and recommended actions.
- Batch model refresh for all projects or inspector-assigned projects.
- Early-warning alerts for high risk and severe schedule delay.
- Risk trend and project history views.

### LogicCore AI Assistant

- Floating chat assistant available after login.
- Gemini-first provider integration with Groq fallback.
- Local database fallback if external providers are unavailable.
- Portfolio overview, project risk questions, alerts, delayed projects, project IDs, and sector questions.
- Role-scoped context: inspectors only receive data for assigned projects.
- Project source chips can reopen the related project dossier.
- Conversation history and suggested follow-up questions.

### Users and Authentication

- Role-based access for Super Admin, Inspector Officer, and Citizen/Public Viewer.
- Admin user creation and deletion.
- Inspector registration and admin approval workflow.
- Admin access requests from ministry-affiliated viewers.
- Online inspector presence heartbeat.
- Password change workflow and temporary-password support for invited officers.
- OTP verification and SMTP invitation support when email settings are configured.
- Session persistence in browser local storage.

## Roles and Permissions

| Role | Access |
| --- | --- |
| Super Admin (`admin`) | Full dashboard, add/delete projects, project assignments, ML predictions, user management, deleted backups, comments, history, and AI assistant. |
| Inspector Officer (`inspector`) | Assigned project dashboard, project dossiers, status/progress updates, inspection notes, ML predictions, history, alerts, and AI assistant scoped to assigned projects. |
| Citizen/Public Viewer (`user`) | Read-only project listing, public project data, risk information, and AI assistant. Cannot add, delete, assign, or update projects. |

## Demo Accounts

The login form uses the account name or email, not the numeric ID. The seeded demo password is `admin` for the built-in accounts.

| Database ID | Login name | Role | Password |
| --- | --- | --- | --- |
| 1 | `Administrator` | Super Admin | `admin` |
| 2 | `Inspector Sharma` | Inspector Officer | `admin` |
| 3 | `Inspector Rajesh Patel` | Inspector Officer | `admin` |
| 4 | `Operations User` | Citizen/Public Viewer | `admin` |
| 5 | `Citizen User` | Citizen/Public Viewer | `admin` |

Use the role selector that matches the account. These are development/demo credentials only and must be changed or removed before production deployment.

## Technology

- Frontend: React 19, Vite, React Router, Recharts, Lucide React.
- Backend: Python, FastAPI, Pydantic, Uvicorn.
- Database: SQLite at `backend/paimana.db`.
- ML: joblib/scikit-learn/XGBoost model support with formula fallback.
- AI providers: Gemini and Groq through HTTPS APIs, with a local fallback engine.

## Project Structure

```text
backend/
  main.py                 FastAPI application, database, auth, projects, ML, alerts
  ai_assistant.py         Gemini/Groq integration and local AI fallback
  requirements.txt        Python dependencies
  paimana.db              Local SQLite database, created/updated at runtime
  comment_uploads/        Uploaded project comment images
frontend/
  src/App.jsx             Authenticated application shell
  src/components/         Header, sidebar, tables, alerts, widgets, AI assistant
  src/pages/               Dashboard, projects, ML, users, login, backups
  src/services/api.js     Frontend API client
ml-mayank/
  risk_model_v2.joblib    Trained risk model
  feature_config_v2.json  Model feature configuration
```

## Requirements

- Node.js 18 or newer.
- Python 3.10 or newer.
- PowerShell on Windows or an equivalent shell.

## Setup

### Backend

From the repository root:

```powershell
cd C:\Users\devra\Downloads\hackdevenger-proj
python -m venv backend\venv
backend\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### Frontend

Open a second terminal:

```powershell
cd C:\Users\devra\Downloads\hackdevenger-proj\frontend
npm install
```

## Environment Variables

Create a root `.env` file. Never commit it or place real keys in `.env.example`.

```env
# Optional SMTP configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=your-gmail@gmail.com


## Run Locally

Start the backend from the repository root in the first terminal:

```powershell
cd C:\Users\devra\Downloads\hackdevenger-proj
backend\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in the second terminal:

```powershell
cd C:\Users\devra\Downloads\hackdevenger-proj\frontend
npm run dev -- --host 127.0.0.1
```

Open the frontend at `http://127.0.0.1:5173/`.

Backend health check: `http://127.0.0.1:8000/`.

Interactive API documentation: `http://127.0.0.1:8000/docs`.

## Main API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | Sign in by role and name/email |
| POST | `/api/v1/auth/register` | Register an account |
| GET | `/api/v1/auth/me` | Refresh the current session |
| GET | `/api/v1/analytics/overview` | Dashboard summary metrics |
| GET | `/api/v1/projects` | List and filter projects |
| POST | `/api/v1/projects` | Create a project and calculate risk |
| GET | `/api/v1/projects/{project_id}` | Get project details |
| GET | `/api/v1/projects/{project_id}/history` | Get project audit history |
| POST | `/api/v1/projects/{project_id}/comments` | Add a project comment/image |
| GET | `/api/v1/predictions/alerts` | Get early-warning alerts |
| POST | `/api/v1/predictions/predict` | Run a project prediction |
| POST | `/api/v1/predictions/refresh` | Refresh all ML predictions |
| POST | `/api/v1/assistant/chat` | Ask LogicCore AI |
| GET | `/api/v1/users` | Admin user management |
| GET | `/api/v1/admin/project-backups` | List deleted project backups |

## Frontend Configuration

The frontend uses `http://127.0.0.1:8000` by default. To use another backend URL, create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Production Build

```powershell
cd frontend
npm run build
```

The generated files are placed in `frontend/dist/`.

## Logs and Troubleshooting

- Backend logs appear in the terminal running Uvicorn.
- Frontend logs appear in the browser developer tools under Console and Network.
- Chat requests can be inspected at `/api/v1/assistant/chat` in the browser Network tab.
- If port 8000 is busy, stop the existing Uvicorn process or use another backend port and update `VITE_API_BASE_URL`.
- If the chatbot shows a fallback answer, check the backend logs for Gemini/Groq failures and verify the provider model names.
- Do not print or share `.env` contents because it contains API keys.

## Data Persistence

The SQLite database persists at `backend/paimana.db`. Projects added through the API remain after a backend restart. The database is ignored by Git so each local installation keeps its own data.
