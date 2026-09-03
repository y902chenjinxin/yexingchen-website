const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, 'dist');
const types = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.css': 'text/css', '.webm': 'video/webm', '.png': 'image/png', '.svg': 'image/svg+xml',
  '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.map': 'application/json'
};
const PROXY = ['/api', '/uploads', '/music'];
function proxyApi(p, req, res) {
  const opt = { hostname: '127.0.0.1', port: 8000, path: p, method: req.method, headers: Object.assign({}, req.headers) };
  delete opt.headers.host;
  const pr = http.request(opt, (prs) => { res.writeHead(prs.statusCode, prs.headers); prs.pipe(res); });
  pr.on('error', () => { res.writeHead(502); res.end(); });
  req.pipe(pr);
}
http.createServer((req, res) => {
  const p = decodeURIComponent((req.url || '/').split('?')[0]);
  if (PROXY.some(k => p === k || p.startsWith(k + '/'))) return proxyApi(p, req, res);
  if (p === '/') return res.end(fs.readFileSync(path.join(ROOT, 'index.html')));
  let fp = path.join(ROOT, p);
  if (!fs.existsSync(fp) || fs.statSync(fp).isDirectory()) {
    if (p.startsWith('/whale-pet/')) { res.writeHead(404); return res.end(); }
    return res.end(fs.readFileSync(path.join(ROOT, 'index.html')));
  }
  res.setHeader('Content-Type', types[path.extname(fp)] || 'application/octet-stream');
  fs.createReadStream(fp).pipe(res);
}).listen(8900, () => console.log('serve on 8900'));