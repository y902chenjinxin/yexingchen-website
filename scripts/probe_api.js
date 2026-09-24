#!/usr/bin/env node
/** 关键接口实测：登录后逐个探测，打印状态与关键字段。 */
const https = require('https');

const SITE = 'https://yexingchen.cn';
const EMAIL = 'admin@yexingchen.cn';
const PASSWORD = 'Chen@12345678';

function req(method, url, body, token) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const headers = { 'Content-Type': 'application/json' };
    if (data) headers['Content-Length'] = Buffer.byteLength(data);
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const r = https.request(url, { method, headers }, (res) => {
      let b = '';
      res.on('data', (c) => b += c);
      res.on('end', () => resolve({ status: res.statusCode, body: b }));
    });
    r.on('error', reject);
    if (data) r.write(data);
    r.end();
  });
}

(async () => {
  const login = await req('POST', SITE + '/api/auth/login', { email: EMAIL, password: PASSWORD });
  const token = JSON.parse(login.body).data.token;
  console.log('login:', login.status);

  const probes = [
    '/api/workbench/summary',
    '/api/stocks/summary',
    '/api/stocks/watchlist',
    '/api/stocks/dashboard',
    '/api/stocks/snapshots?days=60',
    '/api/stocks/alerts',
    '/api/finance/summary',
    '/api/finance/transactions?limit=5',
    '/api/travels',
    '/api/countdown',
    '/api/datahub/overview',
    '/api/feed/dashboard',
    '/api/feed/sources',
  ];

  for (const p of probes) {
    const r = await req('GET', SITE + p, null, token);
    let brief = r.body.slice(0, 180).replace(/\s+/g, ' ');
    console.log(`${r.status === 200 ? 'OK ' : 'ERR'} ${r.status}  ${p}  ${brief}`);
  }
  process.exit(0);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });