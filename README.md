# ResumeAI

Upload a resume, get a personal website in seconds.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENT                           │
│   React SPA (Vite + TS)          Site Preview (iframe)  │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────────┐
│                    API GATEWAY                          │
│         FastAPI · Auth · Rate Limit · CORS              │
└──────┬─────────────────┬────────────────────┬───────────┘
       │                 │                    │
┌──────▼──────┐  ┌───────▼───────┐  ┌────────▼────────┐
│   Resume    │  │     Site      │  │    Publish      │
│   Parser    │─▶│   Generator   │  │    Service      │
│ pypdf/docx  │  │ LLM prompt +  │  │ slug · routing  │
│extract text │  │ HTML renderer │  │                 │
└──────┬──────┘  └───────┬───────┘  └────────┬────────┘
       │                 │                    │
┌──────▼──────┐  ┌───────▼───────┐  ┌────────▼────────┐
│  OpenAI     │  │  File Storage │  │   PostgreSQL    │
│  GPT-4o     │  │  S3/Supabase  │  │   Supabase      │
│resume→HTML  │  │ files · HTML  │  │users·sites·slug │
└─────────────┘  └───────────────┘  └─────────────────┘
```

---

## Product Flow

```
User uploads resume (PDF / DOCX / text)
    │
    ▼
Resume Parser extracts structured text
    │
    ▼
Site Generator calls GPT-4o with style prompt
    │
    ▼
HTML/CSS website generated in ~15s
    │
    ▼
User previews → selects style → publishes
    │
    ▼
Site live at resumeai.app/u/<slug>
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI (Python) |
| AI | OpenAI GPT-4o |
| Resume parsing | pypdf, python-docx |
| Database | PostgreSQL (Supabase) |
| File storage | AWS S3 / Supabase Storage |
| Deployment | Vercel (frontend) + Railway/Fly.io (API) |

---

## API Endpoints

```
POST /upload-resume   — Upload PDF/DOCX, returns extracted text
POST /generate        — Resume text + style → generated HTML site
POST /publish         — Save HTML, return public URL slug
GET  /u/<slug>        — Serve published personal site
```

### `POST /generate` payload

```json
{
  "resume_text": "...",
  "style": "minimal | creative | tech",
  "custom_prompt": "make it more colorful"
}
```

### `POST /generate` response

```json
{
  "html": "<!DOCTYPE html>...",
  "name": "Zhang Wei",
  "slug": "a3f8c2"
}
```

---

## Site Styles

| Style | Description | Best for |
|---|---|---|
| Minimal | Clean black & white, serif font, lots of whitespace | Business, consulting |
| Creative | Gradient hero, colorful skill tags | Design, marketing |
| Tech | Dark background, terminal aesthetic, monospace | Engineers, developers |

---

## Project Structure

```
.
├── README.md
├── resume-to-site-demo.html    # Frontend prototype (standalone)
└── backend/
    ├── main.py                 # FastAPI app
    └── requirements.txt        # Python dependencies
```

---

## Getting Started

**Backend**

```bash
cd backend
pip install -r requirements.txt
OPENAI_API_KEY=sk-xxx uvicorn main:app --reload
```

API available at `http://localhost:8000`
Docs at `http://localhost:8000/docs`

**Frontend prototype**

Open `resume-to-site-demo.html` directly in a browser — no build step needed.

---

## Roadmap

- [ ] Connect frontend to real FastAPI backend
- [ ] PDF/DOCX parsing in upload endpoint
- [ ] Supabase auth (sign up / login)
- [ ] Site storage and slug routing
- [ ] Custom domain support
- [ ] More style templates
- [ ] Mobile app (React Native)
