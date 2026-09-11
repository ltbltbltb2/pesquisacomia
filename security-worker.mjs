import domainRobots from './robots-domain.json' with { type: 'json' };

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

function protect(response, secure, pathname = '') {
  const headers = new Headers(response.headers);
  const type = (headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
  // A 304 or HEAD can omit Content-Type. Never replace a cached HTML policy
  // with a weaker policy merely because the validation response has no body.
  const pdf = type === 'application/pdf' || (!type && pathname.toLowerCase().endsWith('.pdf'));
  headers.set('Content-Security-Policy', pdf ? FILE_POLICY : HTML_POLICY);
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
      }), secure, url.pathname);
    }
    if (!secure) {
      url.protocol = 'https:';
      url.port = '';
      return protect(new Response(null, {
        status: 308,
        headers: { Location: url.href },
      }), false, url.pathname);
    }
    // Preserve the domain's existing robots policy without the provider rewriting
    // HTTP redirect responses to 200. Preserve the custom-domain policy.
    if (url.pathname === '/robots.txt'
      && (request.method === 'GET' || request.method === 'HEAD')) {
      return protect(new Response(request.method === 'HEAD' ? null : domainRobots, {
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          'Content-Length': String(new TextEncoder().encode(domainRobots).length),
          'Cache-Control': 'public, max-age=0, must-revalidate',
        },
      }), true, url.pathname);
    }
    try {
      // Pass the original request through: preserve HEAD, Range, ETag and query semantics.
      return protect(await env.ASSETS.fetch(request), true, url.pathname);
    } catch {
      return protect(new Response('Temporariamente indisponível.', {
        status: 503,
        headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
      }), true, url.pathname);
    }
  },
};
