"""
ResumeAI Backend — FastAPI + OpenAI + Supabase Storage
python -m uvicorn main:app --reload
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
import os, re, hashlib, time
from dotenv import load_dotenv
from chatbox_snippet import inject_chatbox

load_dotenv()

app = FastAPI(title="ResumeAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET       = "sites"
# Vercel proxy base URL: https://v0-resumeai-apps.vercel.app
VERCEL_BASE_URL      = os.getenv("VERCEL_BASE_URL", "https://v0-resumeai-apps.vercel.app")


# ── Supabase Storage helper ────────────────────────────────────────────────

def get_supabase():
    """Return a Supabase client, or raise a clear error if not configured."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env"
        )
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def upload_html_to_supabase(slug: str, html: str) -> str:
    """
    Upload HTML to Supabase Storage bucket 'sites'.
    Sets content-type to text/html so the browser renders it inline (not download).
    Returns the public URL.
    """
    sb = get_supabase()
    file_path = f"{slug}.html"
    html_bytes = html.encode("utf-8")

    sb.storage.from_(STORAGE_BUCKET).upload(
        path=file_path,
        file=html_bytes,
        file_options={
            "content-type": "text/html; charset=utf-8",
            "cache-control": "public, max-age=3600",
            "upsert": "true",
        },
    )

    # Public URL — Supabase renders text/html inline in the browser
    public_url = sb.storage.from_(STORAGE_BUCKET).get_public_url(file_path)
    return public_url


# ── Models ─────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    resume_text: str
    style: str = "minimal"   # minimal | creative | tech
    custom_prompt: str = ""
    # Optional extras — included in the page when provided
    linkedin_url:  str = ""
    scholar_url:   str = ""
    website_url:   str = ""
    # photo_url is injected post-generation in the frontend (base64 too large for prompt)


class GenerateResponse(BaseModel):
    html: str
    name: str
    slug: str


class PublishResponse(BaseModel):
    url: str
    slug: str


# ── Routes ─────────────────────────────────────────────────────────────────

@app.post("/generate", response_model=GenerateResponse)
async def generate_site(req: GenerateRequest):
    """Resume text → GPT-4o → full HTML personal website."""

    style_instructions = {
        "minimal": "极简黑白风格，衬线字体，大量留白，专业商务感",
        "creative": "创意风格，渐变色 Hero 背景（紫→蓝），彩色技能标签，现代感强",
        "tech": "极客暗黑风，终端/代码美学，monospace 字体，深色背景 #0d1117",
    }

    # Build the extras block — only include fields the user actually provided
    extras_lines = []
    if req.linkedin_url:
        extras_lines.append(f'- LinkedIn: <a href="{req.linkedin_url}" target="_blank">{req.linkedin_url}</a>')
    if req.scholar_url:
        extras_lines.append(f'- Google Scholar: <a href="{req.scholar_url}" target="_blank">{req.scholar_url}</a>')
    if req.website_url:
        extras_lines.append(f'- Website: <a href="{req.website_url}" target="_blank">{req.website_url}</a>')

    extras_instruction = ""
    if extras_lines:
        extras_instruction = (
            "\n\n【重要】用户提供了以下额外信息，必须全部显示在网站中（放在联系方式或页脚区域）：\n"
            + "\n".join(extras_lines)
        )

    # Profile photo placeholder — frontend will inject the real base64 image after generation
    photo_instruction = (
        "\n\n用户有头像图片，请在网站合适位置（如 Hero 区域）放置一个圆形头像占位符，"
        "使用 id=\"profile-photo\" 的 <img> 标签，src 暂时留空（src=\"\"）。"
        if req.custom_prompt and "photo" in req.custom_prompt.lower() else ""
    )

    system_prompt = (
        "你是一个专业的个人网站生成器。\n"
        "根据用户提供的简历内容，生成一个完整的、美观的单页个人网站 HTML。\n\n"
        "硬性要求（不可省略）：\n"
        "1. 返回完整 HTML 文件（内联 CSS + JS），不要 markdown 代码块\n"
        "2. 响应式设计，移动端友好\n"
        "3. 必须使用简历中真实的姓名、职位、邮箱、工作经历、技能\n"
        "4. 在 HTML 注释中提供解析出的姓名：<!-- NAME: xxx -->\n"
        + (extras_instruction if extras_lines else "")
        + photo_instruction
    )

    user_prompt = (
        f"简历内容：\n{req.resume_text}\n\n"
        f"风格：{style_instructions.get(req.style, style_instructions['minimal'])}\n"
        + (f"\n额外要求：{req.custom_prompt}\n" if req.custom_prompt else "")
        + "\n请生成个人网站 HTML。"
    )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in server environment.")

    try:
        ai = AsyncOpenAI(api_key=api_key)
        response = await ai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=4000,
            temperature=0.7,
        )
        html = response.choices[0].message.content.strip()
        # Strip accidental markdown code fences
        html = re.sub(r'^```html\s*', '', html, flags=re.IGNORECASE)
        html = re.sub(r'^```\s*',     '', html)
        html = re.sub(r'\s*```$',     '', html)

        name_match = re.search(r'<!-- NAME: (.+?) -->', html)
        name = name_match.group(1).strip() if name_match else "portfolio"
        slug = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:8]

        # Inject AI chatbox — backend_url for the /chat endpoint
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        html = inject_chatbox(html, backend_url)

        return GenerateResponse(html=html, name=name, slug=slug)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    html: str           # current full page HTML
    message: str        # user's customization request
    history: list = []  # [{role, content}, ...] for multi-turn context


class ChatResponse(BaseModel):
    html: str    # updated full page HTML
    reply: str   # friendly confirmation message shown in chatbox


@app.post("/chat", response_model=ChatResponse)
async def chat_customize(req: ChatRequest):
    """
    Live page customization via chat.
    Takes the current HTML + user message, returns updated HTML + reply.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured.")

    system_prompt = (
        "你是一个网页定制助手，帮助用户修改他们的个人网站。\n"
        "用户会告诉你想改什么，你需要：\n"
        "1. 返回修改后的完整 HTML（保留所有原有内容，只修改用户要求的部分）\n"
        "2. 在 HTML 末尾的注释中写一句确认：<!-- REPLY: 已完成xxx修改 -->\n"
        "3. 不要删除页面中已有的 id=\"resumeai-chat\" chatbox 代码\n"
        "4. 只返回 HTML，不要任何解释或 markdown 代码块"
    )

    messages = [{"role": "system", "content": system_prompt}]
    # Include recent history for multi-turn context (last 6 messages)
    for h in req.history[-6:]:
        messages.append(h)
    messages.append({
        "role": "user",
        "content": f"当前页面 HTML：\n{req.html}\n\n用户请求：{req.message}"
    })

    try:
        ai = AsyncOpenAI(api_key=api_key)
        response = await ai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=4000,
            temperature=0.5,
        )
        new_html = response.choices[0].message.content.strip()
        new_html = re.sub(r'^```html\s*', '', new_html, flags=re.IGNORECASE)
        new_html = re.sub(r'^```\s*', '', new_html)
        new_html = re.sub(r'\s*```$', '', new_html)

        reply_match = re.search(r'<!-- REPLY: (.+?) -->', new_html)
        reply = reply_match.group(1).strip() if reply_match else "已更新页面 ✓"

        return ChatResponse(html=new_html, reply=reply)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/publish", response_model=PublishResponse)
async def publish_site(body: dict):
    """
    Upload generated HTML to Supabase Storage → return public URL.
    Body: { slug: str, html: str }
    """
    slug = body.get("slug", "").strip()
    html = body.get("html", "").strip()

    if not slug or not html:
        raise HTTPException(status_code=400, detail="Missing slug or html")

    await upload_html_to_supabase(slug, html)

    # Return Vercel clean URL if configured, otherwise fall back to Supabase URL
    if VERCEL_BASE_URL:
        url = f"{VERCEL_BASE_URL.rstrip('/')}/u/{slug}"
    else:
        url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{slug}.html"

    return PublishResponse(url=url, slug=slug)


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload PDF/DOCX/TXT → return extracted text."""
    content  = await file.read()
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        text = _extract_pdf(content)
    elif filename.endswith((".doc", ".docx")):
        text = _extract_docx(content)
    elif filename.endswith(".txt"):
        text = content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use PDF, DOCX, or TXT.")

    return {"text": text, "filename": file.filename}


@app.get("/u/{slug}", response_class=HTMLResponse)
async def serve_site(slug: str):
    """
    Serve a published site directly (fallback if using Supabase public URL is inconvenient).
    Returns the HTML stored in Supabase Storage.
    """
    try:
        sb = get_supabase()
        data = sb.storage.from_(STORAGE_BUCKET).download(f"{slug}.html")
        return HTMLResponse(content=data.decode("utf-8"), status_code=200)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found: {e}")


@app.get("/health")
async def health():
    supabase_ok = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)
    return {
        "status": "ok",
        "supabase": "configured" if supabase_ok else "not configured",
        "openai_env": bool(os.getenv("OPENAI_API_KEY")),
    }


# ── Internal helpers ────────────────────────────────────────────────────────

def _extract_pdf(content: bytes) -> str:
    try:
        import pypdf
        from io import BytesIO
        reader = pypdf.PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        raise HTTPException(status_code=500, detail="pypdf not installed. Run: pip install pypdf")


def _extract_docx(content: bytes) -> str:
    try:
        import docx
        from io import BytesIO
        doc = docx.Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx not installed. Run: pip install python-docx")
