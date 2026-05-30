const SUPABASE_URL   = process.env.SUPABASE_URL;
const STORAGE_BUCKET = "sites";

export async function GET(request, { params }) {
  const { slug } = params;

  if (!SUPABASE_URL) {
    return new Response("SUPABASE_URL not configured", { status: 500 });
  }

  const storageUrl = `${SUPABASE_URL}/storage/v1/object/public/${STORAGE_BUCKET}/${slug}.html`;

  try {
    const upstream = await fetch(storageUrl, { next: { revalidate: 3600 } });

    if (!upstream.ok) {
      if (upstream.status === 404) {
        return new Response(notFoundPage(slug), {
          status: 404,
          headers: { "Content-Type": "text/html; charset=utf-8" },
        });
      }
      return new Response(`Upstream error: ${upstream.status}`, { status: upstream.status });
    }

    const html = await upstream.text();

    return new Response(html, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
        "X-Powered-By": "ResumeAI",
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
</style>
</head>
<body>
<div class="box">
  <h1>404</h1>
  <p>No site found at <code>/${slug}</code></p>
</div>
</body>
</html>`;
}
