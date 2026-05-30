"""
ResumeAI Backend Test Suite
Run: python test_api.py

Tests:
  1. OpenAI API key is valid
  2. /generate endpoint returns HTML from resume text
  3. /upload-resume endpoint parses a .docx file
  4. Full end-to-end: docx → text → HTML site
"""

import os, sys, json, requests, pathlib

BASE_URL = "http://localhost:8000"
DOCX_PATH = pathlib.Path(__file__).parent.parent / "Chenying Wang_resume_industrial copy.docx"

# ── colour helpers ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✓{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}"); sys.exit(1)
def info(msg): print(f"  {YELLOW}→{RESET}  {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")

# ── sample resume text ──────────────────────────────────────────────────────
SAMPLE_RESUME = """
CHENYING WANG, Ph.D.
Email: wangchenying7@gmail.com | Washington DC

PROFESSIONAL SUMMARY
Electrochemical Engineer with 7+ years of experience in aqueous CO2 electroreduction
and thin film electrode development.

EDUCATION
Ph.D., Chemical Engineering | Rensselaer Polytechnic Institute | 2020-2023
B.E., Chemical Engineering | Tianjin University | 2015-2019

PROFESSIONAL EXPERIENCE
Postdoctoral R&D Scientist | Carnegie Institution of Washington | Jan 2024 – Present
- Developed CO2 electroreduction thin film electrodes achieving high current density
- Conducted long-term electrolysis and durability tests (NASA project)

TECHNICAL SKILLS
Electrochemical: CV, LSV, EIS, Mott-Schottky
Analysis: GC-MS, NMR, TEM, SEM, XRD, XPS
Programming: Matlab, Python, Origin

PUBLICATIONS
12 papers total, 8 as first/co-first author.
NASA Astrobiology ICAR Program Grant, 2024–Present
"""

# ═══════════════════════════════════════════════════════════════════════════
# TEST 1 — Server is running
# ═══════════════════════════════════════════════════════════════════════════
header("Test 1 — Server health check")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    r.raise_for_status()
    ok(f"Server is running at {BASE_URL}")
except requests.exceptions.ConnectionError:
    fail(f"Cannot connect to {BASE_URL}. Run: uvicorn main:app --reload")
except Exception as e:
    fail(f"Health check failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 2 — /generate with sample resume text
# ═══════════════════════════════════════════════════════════════════════════
header("Test 2 — /generate (text → HTML site)")

for style in ["minimal", "creative", "tech"]:
    info(f"Testing style: {style}")
    payload = {
        "resume_text": SAMPLE_RESUME,
        "style": style,
        "custom_prompt": ""
    }
    try:
        r = requests.post(f"{BASE_URL}/generate", json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()

        assert "html" in data, "Response missing 'html' field"
        assert "slug" in data, "Response missing 'slug' field"
        assert len(data["html"]) > 500, "Generated HTML too short"
        assert "<!DOCTYPE" in data["html"] or "<html" in data["html"], "HTML looks invalid"
        assert "Chenying" in data["html"] or "CHENYING" in data["html"] or "Wang" in data["html"], \
            "Name not found in generated HTML — AI may have ignored resume content"

        ok(f"Style '{style}' — HTML {len(data['html'])} chars, slug: {data['slug']}, name detected ✓")

    except requests.exceptions.Timeout:
        fail(f"Style '{style}' timed out (>60s). Check OpenAI API key.")
    except AssertionError as e:
        fail(f"Style '{style}' assertion failed: {e}")
    except Exception as e:
        fail(f"Style '{style}' error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 3 — /upload-resume with real .docx
# ═══════════════════════════════════════════════════════════════════════════
header("Test 3 — /upload-resume (.docx parsing)")

if not DOCX_PATH.exists():
    print(f"  {YELLOW}⚠{RESET}  DOCX not found at {DOCX_PATH}, skipping.")
else:
    try:
        with open(DOCX_PATH, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/upload-resume",
                files={"file": (DOCX_PATH.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                timeout=15
            )
        r.raise_for_status()
        data = r.json()

        assert "text" in data, "Response missing 'text' field"
        assert len(data["text"]) > 200, "Extracted text too short"
        assert "CHENYING" in data["text"].upper(), "Name not found in extracted text"

        ok(f"DOCX parsed — {len(data['text'])} chars extracted")
        info(f"Preview: {data['text'][:120].strip()}...")

    except AssertionError as e:
        fail(f"DOCX parse assertion: {e}")
    except Exception as e:
        fail(f"DOCX upload error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 4 — End-to-end: upload docx → generate site
# ═══════════════════════════════════════════════════════════════════════════
header("Test 4 — End-to-end: DOCX → upload → generate → HTML")

if not DOCX_PATH.exists():
    print(f"  {YELLOW}⚠{RESET}  DOCX not found, skipping end-to-end test.")
else:
    try:
        # Step 1: upload
        with open(DOCX_PATH, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/upload-resume",
                files={"file": (DOCX_PATH.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                timeout=15
            )
        r.raise_for_status()
        resume_text = r.json()["text"]
        ok(f"Step 1 upload — {len(resume_text)} chars")

        # Step 2: generate
        r = requests.post(f"{BASE_URL}/generate", json={
            "resume_text": resume_text,
            "style": "minimal"
        }, timeout=60)
        r.raise_for_status()
        result = r.json()

        assert len(result["html"]) > 500
        ok(f"Step 2 generate — {len(result['html'])} chars HTML, slug: {result['slug']}")

        # Step 3: save preview HTML locally for manual inspection
        out_path = pathlib.Path(__file__).parent / "test_output.html"
        out_path.write_text(result["html"], encoding="utf-8")
        ok(f"Step 3 saved → {out_path}  (open in browser to inspect)")

    except AssertionError as e:
        fail(f"End-to-end assertion: {e}")
    except Exception as e:
        fail(f"End-to-end error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 5 — /publish → Supabase Storage
# ═══════════════════════════════════════════════════════════════════════════
header("Test 5 — /publish (Supabase Storage)")

# Check if Supabase is configured via health endpoint
health = requests.get(f"{BASE_URL}/health").json()
if health.get("supabase") != "configured":
    print(f"  {YELLOW}⚠{RESET}  Supabase not configured — skipping publish test.")
    print(f"       Set SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env")
else:
    try:
        import uuid
        test_slug = f"test-{uuid.uuid4().hex[:6]}"
        test_html = f"<html><body><h1>Test site {test_slug}</h1></body></html>"

        r = requests.post(f"{BASE_URL}/publish", json={"slug": test_slug, "html": test_html}, timeout=15)
        r.raise_for_status()
        data = r.json()

        assert "url" in data, "Response missing 'url'"
        assert test_slug in data["url"], "Slug not in returned URL"
        ok(f"Published → {data['url']}")

        # Verify the file is accessible
        r2 = requests.get(data["url"], timeout=10)
        assert r2.status_code == 200, f"Public URL returned {r2.status_code}"
        assert test_slug in r2.text, "Content mismatch at public URL"
        ok(f"Public URL accessible and content verified ✓")

    except AssertionError as e:
        fail(f"Publish assertion: {e}")
    except Exception as e:
        fail(f"Publish error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{GREEN}{BOLD}All tests passed!{RESET}\n")
