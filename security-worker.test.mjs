import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './security-worker.mjs';

const hosts = ['pesquisacomia.com.br', 'www.pesquisacomia.com.br'];
const failAssets = { ASSETS: { fetch() { assert.fail('An HTTP redirect must not fetch assets'); } } };

test('HTTP upgrades all published hosts without dropping paths or query parameters', async () => {
  for (const host of hosts) for (const method of ['GET', 'HEAD', 'POST']) {
    const path = '/pesquisa-01.html?busca=clima%20e%20dengue&origem=a%2Fb&v=1&v=2';
    const response = await worker.fetch(new Request(`http://${host}${path}`, { method }), failAssets);
    assert.equal(response.status, 308);
    assert.equal(response.headers.get('Location'), `https://${host}${path}`);
    assert.equal(await response.text(), '');
  }
});

test('forwarded headers cannot change the redirect destination or downgrade HTTPS', async () => {
  const headers = { 'X-Forwarded-Host': 'attacker.example', 'X-Forwarded-Proto': 'http', Forwarded: 'host=attacker.example;proto=http' };
  const insecure = await worker.fetch(new Request('http://pesquisacomia.com.br/artigo-01.pdf', { headers }), failAssets);
  assert.equal(insecure.headers.get('Location'), 'https://pesquisacomia.com.br/artigo-01.pdf');
  const secure = await worker.fetch(new Request('https://pesquisacomia.com.br/', { headers }), {
    ASSETS: { fetch: () => new Response('ok', { headers: { 'Content-Type': 'text/html' } }) },
  });
  assert.equal(secure.status, 200);
  assert.equal(secure.headers.has('Location'), false);
});

test('unconfigured hosts are rejected instead of producing an open redirect', async () => {
  for (const scheme of ['http', 'https']) {
    const response = await worker.fetch(new Request(`${scheme}://attacker.example/`), failAssets);
    assert.equal(response.status, 400);
    assert.equal(response.headers.has('Location'), false);
  }
});

test('domain robots delivery preserves its existing policy', async () => {
  const domainPolicy = JSON.parse(readFileSync('robots-domain.json', 'utf8'));
  for (const host of hosts.slice(0, 2)) for (const method of ['GET', 'HEAD']) {
    const response = await worker.fetch(new Request(`https://${host}/robots.txt`, { method }), failAssets);
    assert.equal(response.status, 200);
    assert.equal(await response.text(), method === 'HEAD' ? '' : domainPolicy);
    assert.equal(response.headers.get('Content-Length'), String(Buffer.byteLength(domainPolicy)));
    assert.equal(response.headers.get('X-Content-Type-Options'), 'nosniff');
    const redirect = await worker.fetch(new Request(`http://${host}/robots.txt`), failAssets);
    assert.equal(redirect.status, 308);
  }

});

test('HTML and custom 404 documents receive restrictive policies without body changes', async () => {
  for (const status of [200, 404]) {
    const body = readFileSync(status === 200 ? 'index.html' : '404.html');
    const response = await worker.fetch(new Request('https://pesquisacomia.com.br/'), {
      ASSETS: { fetch: () => new Response(body, { status, headers: { 'Content-Type': 'text/html; charset=utf-8', ETag: '"original"' } }) },
    });
    assert.equal(response.status, status);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), body);
    assert.equal(response.headers.get('ETag'), '"original"');
    const policy = response.headers.get('Content-Security-Policy');
    for (const directive of ["default-src 'none'", "script-src 'self'", "style-src 'self'", "frame-ancestors 'none'", "form-action 'none'"]) assert.ok(policy.includes(directive));
    assert.ok(!policy.includes('unsafe-inline') && !policy.includes('unsafe-eval'));
    assert.equal(response.headers.get('Strict-Transport-Security'), 'max-age=31536000');
    assert.equal(response.headers.get('X-Content-Type-Options'), 'nosniff');
    assert.equal(response.headers.get('X-Frame-Options'), 'DENY');
  }
});

test('PDF range requests, content type, validators and bytes survive the security layer', async () => {
  const pdf = readFileSync('artigo-01.pdf');
  const bytes = pdf.subarray(0, 64);
  const contentRange = `bytes 0-63/${pdf.length}`;
  const request = new Request('https://pesquisacomia.com.br/artigo-01.pdf', { headers: { Range: 'bytes=0-63', 'If-Range': '"pdf-v1"' } });
  const response = await worker.fetch(request, { ASSETS: { fetch(received) {
    assert.equal(received, request);
    return new Response(bytes, { status: 206, headers: {
      'Content-Type': 'application/pdf', 'Content-Range': contentRange, 'Accept-Ranges': 'bytes',
      'Content-Length': '64', ETag: '"pdf-v1"', 'Cache-Control': 'public, max-age=0, must-revalidate',
    } });
  } } });
  assert.equal(response.status, 206);
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), bytes);
  assert.equal(response.headers.get('Content-Range'), contentRange);
  assert.equal(response.headers.get('Content-Length'), '64');
  assert.equal(response.headers.get('Content-Type'), 'application/pdf');
  assert.equal(response.headers.get('ETag'), '"pdf-v1"');
  assert.equal(response.headers.get('Cache-Control'), 'public, max-age=0, must-revalidate');
  assert.ok(!response.headers.get('Content-Security-Policy').includes('default-src'));
});

test('HEAD, conditional requests and existing asset redirects keep their HTTP semantics', async () => {
  for (const status of [200, 304, 307]) {
    const request = new Request('https://pesquisacomia.com.br/pesquisa-01.html', { method: 'HEAD', headers: { 'If-None-Match': '"v1"' } });
    const response = await worker.fetch(request, { ASSETS: { fetch(received) {
      assert.equal(received.method, 'HEAD');
      assert.equal(received.headers.get('If-None-Match'), '"v1"');
      return new Response(null, { status, headers: { ETag: '"v1"', ...(status === 307 ? { Location: '/pesquisa-01' } : {}) } });
    } } });
    assert.equal(response.status, status);
    assert.equal(await response.text(), '');
    assert.equal(response.headers.get('ETag'), '"v1"');
    assert.ok(response.headers.get('Content-Security-Policy').includes("script-src 'self'"));
    if (status === 307) assert.equal(response.headers.get('Location'), '/pesquisa-01');
  }
});

test('a PDF 304 without Content-Type keeps its PDF policy instead of acquiring HTML restrictions', async () => {
  const response = await worker.fetch(new Request('https://pesquisacomia.com.br/artigo-01.pdf'), {
    ASSETS: { fetch: () => new Response(null, { status: 304, headers: { ETag: '"pdf-v1"' } }) },
  });
  assert.equal(response.status, 304);
  assert.equal(response.headers.get('Content-Security-Policy'), "frame-ancestors 'none'; base-uri 'none'; form-action 'none'");
});

test('asset failure produces a protected, non-cacheable response without exposing error details', async () => {
  const response = await worker.fetch(new Request('https://pesquisacomia.com.br/'), {
    ASSETS: { fetch() { throw new Error('private backend detail'); } },
  });
  assert.equal(response.status, 503);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.equal(response.headers.get('X-Content-Type-Options'), 'nosniff');
  assert.ok(!(await response.text()).includes('private'));
});

test('published HTML needs no inline scripts, inline styles, frames or external executable resources', () => {
  for (const name of readdirSync('.').filter(name => name.endsWith('.html'))) {
    const html = readFileSync(name, 'utf8');
    assert.doesNotMatch(html, /\s(?:style|on\w+)\s*=/i, name);
    assert.doesNotMatch(html, /<(?:iframe|object|embed|form)\b/i, name);
    for (const tag of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
      assert.match(tag[1], /src="app\.js"/);
      assert.equal(tag[2].trim(), '');
    }
  }
});
