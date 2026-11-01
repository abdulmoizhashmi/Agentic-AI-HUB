# Agentic AI Hub

A local, full-stack learning application with two specialist agents:

- **Customer Support Agent**: searches a mock FAQ, looks up demo orders, and routes sensitive requests to human review.
- **AI Interview Agent**: runs role- and difficulty-based mock interviews and gives follow-up feedback.

The backend uses a real **LangGraph** state graph. Its router, planner, specialist, tool, reflection, and checkpoint nodes are connected by edges and conditional routing. A LangGraph in-memory checkpointer is paired with a local JSON session store so conversation turns remain available after the backend restarts.

## GitHub Pages demo

The project site is published from the `main` branch root. `publish-pages.ps1` builds the frontend with the `/Agentic-AI-HUB/` project-site path, then copies the static entry page and bundled assets to the repository root. The root `index.html` makes Pages show the application instead of rendering this README. After changing frontend code, run `.\publish-pages.ps1`, commit the generated root `index.html` and `agentic-ai-hub-assets/`, then push to `main`. GitHub Pages automatically publishes the branch update; check the repository's **Actions** tab for the Pages build status.

GitHub Pages hosts static files only; it does not run the Python/FastAPI server. On `github.io`, the UI therefore uses a clearly labeled browser-only demo with sample support and interview responses. To run the full LangGraph-powered backend, follow the local setup instructions below.

## Learning guide

This project is intended as a small, runnable example for learning how an agent application is assembled. Start with one user request and follow it from the React UI, through the HTTP API, into the LangGraph workflow, and back to the conversation.

### Technology stack

| Area | Technology | Purpose in this project |
|---|---|---|
| Browser UI | React 18 | Builds the interactive agent chat and controls. |
| Frontend language | JavaScript (ES modules, JSX) | Defines components and browser-side behavior. |
| Frontend tooling | Vite 6 | Runs the local development server and bundles production assets. |
| Icons | lucide-react | Supplies the interface icons. |
| API server | FastAPI | Exposes the chat, session, review, and health endpoints. |
| API validation | Pydantic 2 | Validates and bounds incoming chat requests. |
| Workflow orchestration | LangGraph | Defines specialist routing, tool usage, response, and checkpoint nodes as a graph. |
| Model integration | OpenAI Python SDK (optional) | Generates responses when a key is configured. |
| Configuration | python-dotenv | Loads local backend settings from `backend\.env`. |
| Local development | Python 3.10+ and Node.js 18+ | Run the backend and frontend. |

CrewAI, AutoGen, and OpenAI Agents SDK are not used by the running application. They are separate frameworks you can explore after understanding this example.

### Architecture at a glance

```text
Browser (React + Vite)
  ├─ Customer Support Agent ─┐
  └─ AI Interview Agent ─────┴─ POST /api/chat
                                 │
                         FastAPI + Pydantic
                                 │
                       LangGraph supervisor
                  ┌──────────────┴──────────────┐
             Support route                 Interview route
             ├─ escalation check           └─ interview agent
             ├─ FAQ / order tools                  │
             └──────────────┬──────────────────────┘
                      Response + reflection
                                 │
                   JSON session store + response
                                 │
                         Browser conversation
```

### What happens when you send a message

1. The React app keeps separate session IDs and messages for the two agents, then sends the selected agent, message, and interview settings as JSON.
2. FastAPI validates the body using the `ChatRequest` Pydantic model. Invalid or oversized input is rejected before the workflow runs.
3. The orchestrator loads that agent's saved conversation and invokes the compiled LangGraph with a thread ID derived from both the session ID and agent type.
4. The router and planner nodes record which specialist to run and the intended steps.
5. Conditional routing sends support requests to escalation detection and mock tools, while interview requests go directly to the interview specialist.
6. The specialist asks the optional OpenAI model for a response when configured. Without a usable model response, deterministic local examples handle common flows.
7. Reflection checks for an empty response and applies a safe fallback if needed.
8. The checkpoint node saves the turn and metadata to `backend\data\sessions.json`; the graph's `MemorySaver` also checkpoints graph state in memory while the backend process is running.
9. The API returns the response, escalation status, and workflow trace. The browser displays the agent's reply.

### Agent and LangGraph concepts demonstrated

- **Agent architecture:** each specialist has a defined role and its own response behavior.
- **Supervisor/router:** a shared orchestrator routes work based on the selected agent.
- **Planning:** a planner node records a short execution plan before specialist work.
- **State management:** the graph passes a typed `AgentState` between nodes.
- **Nodes and edges:** router, planner, tools, specialist, reflection, and checkpoint are nodes connected in execution order.
- **Conditional routing:** the planner selects the support or interview path.
- **Tool calling:** support looks up demo orders and searches a small FAQ. These are local Python tools, not external APIs.
- **Memory:** recent conversation messages are supplied to the interview response; agent sessions are kept separate.
- **Checkpointing:** LangGraph `MemorySaver` keeps graph checkpoints in process memory; the JSON store persists conversation turns to disk across restarts.
- **Human-in-the-loop:** sensitive support messages are added to the pending review queue. This demo flags work for a person; it does not provide a staffed review dashboard or execute account/order changes.
- **Reflection and safe fallback:** a response check prevents empty answers, while support instructions avoid unsupported order promises.
- **Multi-step reasoning:** a request proceeds through multiple explicit workflow stages. The UI does not expose private model chain-of-thought.
- **Multi-agent workflow:** two specialist agents share one router and API. This is a small supervisor pattern, not a team of autonomous agents debating with one another.

### Useful source files

| File | What to study |
|---|---|
| `frontend\src\App.jsx` | Agent selection, form state, API calls, loading/error handling, and rendering chat messages. |
| `frontend\src\styles.css` | Responsive black-and-beige design, mobile breakpoints, and control sizing. |
| `frontend\src\main.jsx` | React application entry point. |
| `frontend\vite.config.js` | Vite development server configuration. |
| `backend\app\main.py` | FastAPI setup, request schema, CORS, and HTTP endpoints. |
| `backend\app\workflow.py` | LangGraph state, nodes, conditional routing, support/interview logic, and checkpointing. |
| `backend\app\tools.py` | Mock knowledge-base search, order lookup, and escalation detection. |
| `backend\app\llm.py` | Optional OpenAI integration and logged local fallback. |
| `backend\app\storage.py` | JSON persistence for conversations, memory summaries, and human-review items. |
| `backend\tests\test_workflow.py` | Tests for order lookup, escalation, and role/difficulty-aware interviews. |
| `.vscode\tasks.json` | Starts the backend and frontend together from VS Code. |

### API endpoints

| Method and path | Purpose |
|---|---|
| `GET /` | API identity and docs location. |
| `GET /api/health` | Backend health and whether an OpenAI key is configured. |
| `POST /api/chat` | Run an agent turn. Body fields: `session_id`, `agent` (`support` or `interview`), `message`, optional `role`, optional `difficulty`. |
| `GET /api/sessions/{session_id}` | Read saved session messages and memory. |
| `DELETE /api/sessions/{session_id}` | Clear a saved session. |
| `GET /api/human-review` | List conversations currently flagged for human review. |

FastAPI's interactive endpoint documentation is available at <http://127.0.0.1:8000/docs> when the backend is running.

### Frontend responsiveness

The interface uses a desktop sidebar and centered conversation at larger widths, then switches to a compact stacked navigation on screens at or below 620px. Interview controls wrap into a vertical layout on phones, chat messages and prompts wrap to the available width, and text-entry/send controls are sized for touch. The design is tested at narrow phone, phone, tablet, and desktop viewport widths.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer (npm is included)
- VS Code (optional; the application can also be started from two terminals)
- OpenAI API key (optional; both agents work with deterministic local responses without one)

## Quick setup on Windows

1. Extract the project ZIP and open the extracted `Agentic_AI_Hub_Project` folder in VS Code.
2. In the VS Code terminal, run:

   ```powershell
   .\setup.ps1
   ```

   This creates `backend\.venv`, installs Python and frontend dependencies, and creates `backend\.env` from the example if needed. If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then retry.
3. In VS Code, select **Terminal > Run Task > Start Agentic AI Hub**. The backend and frontend start in separate terminals.
4. Open <http://localhost:5173>. The API and interactive documentation are at <http://127.0.0.1:8000> and <http://127.0.0.1:8000/docs>.

### Start manually

Backend terminal:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend terminal:

```powershell
cd frontend
npm run dev
```

For manual setup without `setup.ps1`, create the environment and install dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
cd ..\frontend
npm install
```

## Optional OpenAI responses

Add your key to `backend\.env`:

```dotenv
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
```

Restart the backend after changing the environment file. Do not commit or share the `.env` file. If no key is configured—or the model request fails—the agents log the issue and use their local demo responses.

## Try the agents

- Support: “Where is order DEMO-1001?”, “What is your refund policy?”, or “I need a human agent”.
- Interview: select a role and difficulty, click **Start interview**, then answer the question.

Each agent has a separate session, so their conversation histories do not mix. Session data is stored in `backend\data\sessions.json`; the file is created automatically and is excluded from the project archive.

## Verify

From the project root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
cd ..\frontend
npm run build
```

## Project layout

```text
backend/
  app/                 FastAPI API, LangGraph workflow, tools, LLM adapter, and session store
  data/                Local session data directory
  tests/               Backend workflow tests
  requirements.txt
frontend/
  src/                 React application and styles
  package.json
.vscode/tasks.json     VS Code tasks for starting both servers
setup.ps1              Windows dependency setup
```

This is an educational starter, not production software. The order and FAQ tools are mock data, and the local JSON store is not a substitute for an authenticated, durable production database. CrewAI, AutoGen, and the OpenAI Agents SDK are learning topics, not dependencies used by this application.
