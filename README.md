# 🌾 BRRI Winnower 2024 — Multimodal Troubleshooting Assistant

A full-stack prototype that helps field operators diagnose and fix problems with
the **BRRI Winnower Model 2024** agricultural machine. Users upload a **photo**
of a suspected faulty part or **record their voice** describing the issue; the
app grounds the request in a local knowledge base (machine specs + reference
images of intact parts) and asks **Google Gemini 2.5 Pro** for a step-by-step
repair guide, returned **exclusively in fluent Bengali (Bangla)**.

---

## ✨ Features

- **Vision troubleshooting** — upload a part photo (+ optional text). The backend
  attaches local "healthy part" reference images so Gemini can compare the broken
  part against a known-good reference.
- **Voice troubleshooting** — record audio in the browser (`MediaRecorder` API).
  The backend transcribes it and produces a fix.
- **Grounded answers** — every request is combined with `prompts.txt` and
  `machine_data.json` from a local knowledge base directory.
- **Bengali output** — all solutions are returned in Bangla, rendered with a
  Bengali-capable web font.
- **Full audit log** — every query (image/audio path, text, transcription,
  response, timestamp) is stored in SQLite via SQLAlchemy.
- **Graceful demo mode** — runs without a Gemini key (returns a helpful Bengali
  message) so the UI is demoable out of the box.

---

## 🏗️ Tech Stack

| Layer     | Technology                                              |
| --------- | ------------------------------------------------------- |
| Backend   | FastAPI (Python 3.10+), SQLAlchemy ORM, pydantic-settings |
| AI        | Google Gemini 2.5 Pro via the `google-genai` SDK        |
| Database  | SQLite (swap to PostgreSQL/MySQL by changing one URL)   |
| Frontend  | React 18 + Vite + Tailwind CSS + react-markdown         |

---

## 📁 Project Structure

```
brri-prototype/
├── README.md
├── .gitignore
│
├── backend/
│   ├── main.py                     # FastAPI entrypoint (app, CORS, lifespan)
│   ├── requirements.txt
│   ├── .env.example                # Copy to .env and fill in secrets
│   │
│   ├── app/
│   │   ├── config.py               # Typed settings from environment (.env)
│   │   ├── database.py             # SQLAlchemy engine, session, Base, init_db
│   │   │
│   │   ├── models/                 # ORM models
│   │   │   └── query_log.py        # QueryLog audit table
│   │   │
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   └── troubleshoot.py
│   │   │
│   │   ├── routes/                 # API route handlers
│   │   │   └── troubleshoot.py     # /vision, /voice, /history
│   │   │
│   │   ├── services/               # Business logic
│   │   │   ├── knowledge_base.py   # Loads prompts.txt + machine_data.json
│   │   │   └── gemini_service.py   # Gemini 2.5 Pro multimodal integration
│   │   │
│   │   └── utils/
│   │       └── files.py            # Upload saving + reference image reading
│   │
│   └── knowledge_base/             # 📚 Local grounding data (see below)
│       ├── prompts.txt             # Base system instruction for the LLM
│       ├── machine_data.json       # BRRI Winnower 2024 technical specs
│       └── reference_images/       # Photos of INTACT parts (compared vs. user)
│           └── README.md
│
└── frontend/
    ├── package.json
    ├── vite.config.js              # Dev proxy: /api -> http://localhost:8000
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html                  # Loads Bengali web fonts
    ├── .env.example
    └── src/
        ├── main.jsx
        ├── App.jsx                 # Tabs, state, orchestration
        ├── index.css               # Tailwind directives
        ├── services/
        │   └── api.js              # fetch wrappers for the backend
        └── components/
            ├── Header.jsx
            ├── ImageUpload.jsx     # Drag & drop + preview + text
            ├── AudioRecorder.jsx   # MediaRecorder capture + playback
            ├── ResponseDisplay.jsx # Renders Bengali markdown
            └── Loader.jsx          # Spinner + skeleton
```

---

## 📚 The Local Knowledge Base

The backend reads a local `knowledge_base/` directory to **ground** every LLM
request in the real machine's data:

1. **`prompts.txt`** — the base system instruction. The core directive is:

   > *"Analyze the user's uploaded image or audio transcription regarding the BRRI
   > Winnower 2024. Use the provided JSON data and reference images to
   > cross-reference the issue with the machine's mechanical specs. Output a
   > step-by-step troubleshooting solution EXCLUSIVELY in fluent Bengali (Bangla)."*

2. **`machine_data.json`** — technical specifications (dimensions, motor, belt,
   bearings, blower, sieve mechanism, materials, common issues). This JSON is
   serialised and appended to the system instruction at request time.

3. **`reference_images/`** — drop photos of **intact** parts here. The backend
   automatically attaches up to 4 of them (alphabetical order) to each Gemini
   Vision request, labelled as reference images, so the model can compare the
   user's (possibly broken) part against a known-good one.

> The knowledge base is loaded once at startup and cached in-process. Edit the
> files and restart the backend (or call `reload_knowledge_base()`) to refresh.

### Seeded machine data (BRRI Win2024)

- **Dimensions:** 1350 × 835 × 1310 mm
- **Motor:** 0.5 HP, single phase, 220 V, 1450 rpm
- **Power transmission:** B-belt, 1650 mm (marked **B65**)
- **Bearings:** 6306 ball bearings, P-206 pillow block bearings
- **Core mechanism:** motor → V-belt → main shaft → 270 mm blower + sieve cam/linkage
- **Materials:** Plain Carbon Steel angle bars (38×38×3 mm), some ASTM A36,
  stainless steel fasteners

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- A **Google Gemini API key** — get one at
  [Google AI Studio](https://aistudio.google.com/app/apikey)
  *(optional: the app runs in demo mode without it)*

### 1. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# → open .env and paste your GEMINI_API_KEY

# Run the API (http://localhost:8000, docs at /docs)
uvicorn main:app --reload --port 8000
```

### 2. (Optional) Add reference images

Drop JP/PNG photos of **intact** machine parts into
`backend/knowledge_base/reference_images/`, e.g. `blower_unit_intact.jpg`,
`v_belt_b65.jpg`. See that folder's `README.md` for naming tips.

### 3. Frontend setup

```bash
cd frontend

npm install

# (optional) cp .env.example .env  — only needed for a non-proxied backend
npm run dev                        # http://localhost:5173
```

Open **http://localhost:5173**. The Vite dev server proxies `/api/*` to the
FastAPI backend on port 8000, so no CORS config is needed locally.

---

## 🔌 API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint                     | Description                                             |
| ------ | ---------------------------- | ------------------------------------------------------- |
| `GET`  | `/`                          | Liveness + config probe (model, whether Gemini is set). |
| `GET`  | `/api/health`               | Simple health check.                                    |
| `POST` | `/api/troubleshoot/vision`  | `multipart/form-data`: `image` (file), `text` (opt.).   |
| `POST` | `/api/troubleshoot/voice`   | `multipart/form-data`: `audio` (file).                  |
| `GET`  | `/api/troubleshoot/history` | Recent query logs (`?limit=20`).                        |

Interactive Swagger docs: **http://localhost:8000/docs**

### Example: vision request

```bash
curl -X POST http://localhost:8000/api/troubleshoot/vision \
  -F "image=@/path/to/broken_belt.jpg;type=image/jpeg" \
  -F "text=belt keeps slipping"
```

### Example response

```json
{
  "id": 1,
  "modality": "vision",
  "response": "ধাপ ১: ... (Bengali step-by-step solution)",
  "transcription": null,
  "reference_images_used": ["v_belt_b65.jpg"],
  "created_at": "2026-07-23T17:49:47.059000"
}
```

---

## 🗄️ Database

- Uses **SQLite** by default at `backend/brri_winnower.db` (auto-created on
  startup). Every request is written to the `query_logs` table.
- **Migrating to PostgreSQL / MySQL** requires only changing `DATABASE_URL` in
  `.env` and installing the appropriate driver (e.g. `psycopg`), because the app
  uses the SQLAlchemy ORM throughout — no raw SQLite calls.

```env
# Example PostgreSQL URL
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/brri
```

---

## 🔐 Security & Configuration

- All secrets live in **`.env`** (never committed — see `.gitignore`).
  Reference values are documented in **`.env.example`**.
- `GEMINI_API_KEY` and `DATABASE_URL` are the key sensitive variables.
- Uploads are validated against content-type allow-lists and stored under
  `backend/uploads/` with collision-resistant, timestamped filenames.
- CORS origins are configurable via the `CORS_ORIGINS` env variable.

---

## 🧩 How a Request Flows

1. **Frontend** captures an image or audio blob and POSTs it to the backend.
2. **Route handler** validates the content type and saves the upload.
3. **Knowledge base service** builds a grounded system instruction
   (`prompts.txt` + `machine_data.json`).
4. **Gemini service** attaches local reference images + the user's input and
   calls Gemini 2.5 Pro (voice is transcribed first, then diagnosed).
5. **Response** (Bengali) is logged to SQLite and returned to the UI, which
   renders it as formatted markdown.

---

## 🛠️ Troubleshooting the App Itself

| Symptom                                   | Fix                                                        |
| ----------------------------------------- | ---------------------------------------------------------- |
| Response says "GEMINI_API_KEY missing"    | Add a valid key to `backend/.env` and restart uvicorn.     |
| `429 RESOURCE_EXHAUSTED` / quota exceeded | `gemini-2.5-pro` has **no free-tier quota**. Set `GEMINI_MODEL=gemini-2.5-flash` in `.env`, or enable billing. The app auto-falls back to `GEMINI_FALLBACK_MODEL` and returns a Bengali 429 message. |
| Microphone doesn't work in browser        | Allow mic permission; use `http://localhost` (secure ctx). |
| CORS errors in production                 | Set `CORS_ORIGINS` and `VITE_API_BASE_URL` correctly.      |
| Frontend can't reach backend in dev       | Ensure backend runs on port 8000 (Vite proxies `/api`).    |
| `sqlite3.OperationalError: attempt to write a readonly database` | The SQLite file/dir isn't writable by the server process. Relative DB paths are auto-anchored to `backend/`; ensure that directory is writable by the user running uvicorn (`chown`/`chmod` if it's owned by another user), or point `DATABASE_URL` to a writable absolute path. |

---

## 📈 Extending the Prototype

- Add more reference images to improve visual comparisons.
- Enrich `machine_data.json` with part-level fault trees.
- Add authentication and rate limiting for production.
- Swap SQLite for PostgreSQL and add Alembic migrations.
- Add a history/gallery view in the frontend using `/api/troubleshoot/history`.

---

*Built as a maintainable, scalable prototype. Answers are AI-generated — always
verify critical repairs with a qualified technician.*
