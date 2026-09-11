// Request URL comes from Cloudflare; forwarded headers are never used for redirects.
const SITE_HOSTS = new Set([
  'pesquisacomia.com.br',
  'www.pesquisacomia.com.br',
]);

const HTML_POLICY = [
  "default-src 'none'",
  "base-uri 'none'",
  "script-src 'self'",
  "script-src-attr 'none'",
  "style-src 'self'",
  "style-src-attr 'none'",
  "img-src 'self'",
  "font-src 'self'",
  "connect-src 'none'",
  "object-src 'none'",
  "frame-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'none'",
  'upgrade-insecure-requests',
].join('; ');

// Do not impose HTML resource restrictions on native PDF viewers.
const FILE_POLICY = "frame-ancestors 'none'; base-uri 'none'; form-action 'none'";

function protect(response, secure) {
  const headers = new Headers(response.headers);
  const type = (headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
  headers.set('Content-Security-Policy',
    type === 'text/html' || type === 'application/xhtml+xml' ? HTML_POLICY : FILE_POLICY);
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('X-Frame-Options', 'DENY');
  headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=()');
  // Exact hosts only: no preload or policy for unconfigured subdomains.
  if (secure) headers.set('Strict-Transport-Security', 'max-age=31536000');
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const secure = url.protocol === 'https:';
    if (!SITE_HOSTS.has(url.hostname)) {
      return protect(new Response('Host não reconhecido.', {
        status: 400,
        headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
      }), secure);
    }
    if (!secure) {
      url.protocol = 'https:';
      url.port = '';
      return protect(new Response(null, {
        status: 308,
        headers: { Location: url.href },
      }), false);
    }
    try {
      // Pass the original request through: preserve HEAD, Range, ETag and query semantics.
      return protect(await env.ASSETS.fetch(request), true);
    } catch {
      return protect(new Response('Temporariamente indisponível.', {
        status: 503,
        headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
      }), true);
    }
  },
};
