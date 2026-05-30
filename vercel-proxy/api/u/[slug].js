/**
 * Vercel Edge Function — /u/[slug]
 *
 * Fetches the generated HTML from Supabase Storage and serves it
 * as a proper webpage. Supports custom domain (resumeai.app/u/chenying-wang).
 */

export const config = { runtime: "edge" };

const SUPABASE_URL    = process.env.SUPABASE_URL;
const STORAGE_BUCKET  = "sites";

export default async function handler(req) {
  const url  = new URL(req.url);
  const slug = url.pathname.split("/u/")[1]?.replace(/\.html$/, "").trim();

  if (!slug) {
    return new Response("Not found", { status: 404 });
  }

  if (!SUPABASE_URL) {
    return new Response("SUPABASE_URL not configured", { status: 500 });
  }

  const storageUrl = `${SUPABASE_URL}/storage/v1/object/public/${STORAGE_BUCKET}/${slug}.html`;

  try {
    const res = await fetch(storageUrl);

    if (!res.ok) {
      if (res.status === 404) {
        return new Response(notFoundPage(slug), {
          status: 404,
          headers: { "content-type": "text/html; charset=utf-8" },
        });
      }
      return new Response(`Upstream error: ${res.status}`, { status: res.status });
    }

    const html = await res.text();

    return new Response(html, {
      status: 200,
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "public, s-maxage=3600, stale-while-revalidate=86400",
        "x-powered-by": "ResumeAI",
      },
    });
  } catch (err) {
    return new Response(`Error: ${err.message}`, { status: 500 });
  }
}

function notFoundPage(slug) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Page not found — ResumeAI</title>
<style>
  body { font-family: -apple-system, sans-serif; background: #0a0a0f; color: #e8e8f0;
         display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
  .box { text-align: center; }
  h1 { font-size: 48px; font-weight: 800; color: #7c6aff; margin-bottom: 12px; }
  p  { color: #6b7280; font-size: 16px; }
  a  { color: #a78bfa; }
</style>
</head>
<body>
<div class="box">
  <h1>404</h1>
  <p>No site found at <code>/${slug}</code></p>
  <p><a href="/">Create your own →</a></p>
</div>
</body>
</html>`;
}
