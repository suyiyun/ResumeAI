/**
 * Vercel Serverless Function — /api/u/[slug]
 * Fetches generated HTML from Supabase Storage and serves it inline.
 */

const SUPABASE_URL   = process.env.SUPABASE_URL;
const STORAGE_BUCKET = "sites";

module.exports = async function handler(req, res) {
  const { slug } = req.query;

  if (!slug) {
    return res.status(404).send("Not found");
  }

  if (!SUPABASE_URL) {
    return res.status(500).send("SUPABASE_URL not configured");
  }

  const storageUrl = `${SUPABASE_URL}/storage/v1/object/public/${STORAGE_BUCKET}/${slug}.html`;

  try {
    const upstream = await fetch(storageUrl);

    if (!upstream.ok) {
      if (upstream.status === 404) {
        return res.status(404).setHeader("Content-Type", "text/html; charset=utf-8").send(notFoundPage(slug));
      }
      return res.status(upstream.status).send(`Upstream error: ${upstream.status}`);
    }

    const html = await upstream.text();

    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.setHeader("Cache-Control", "public, s-maxage=3600, stale-while-revalidate=86400");
    res.setHeader("X-Powered-By", "ResumeAI");
    return res.status(200).send(html);

  } catch (err) {
    return res.status(500).send(`Error: ${err.message}`);
  }
};

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
