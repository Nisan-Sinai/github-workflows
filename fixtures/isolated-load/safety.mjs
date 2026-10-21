import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { localOrigin, main } from './client.mjs';

test('rejects remote, DNS, HTTPS, credentials, privileged ports and path injection before traffic', async () => {
  for (const value of ['https://example.com', 'http://example.com:3000', 'http://localhost:3000',
    'https://127.0.0.1:3000', 'http://127.0.0.1:80', 'http://user:pass@127.0.0.1:3000',
    'http://127.0.0.1:3000/route', 'http://127.0.0.1:3000/?url=https://example.com']) {
    assert.throws(() => localOrigin(value));
  }
  for (const env of [{ VERCEL: '1' }, { VERCEL_ENV: 'preview' }, { NODE_ENV: 'production' },
    { LOAD_USERS: '201' }, { LOAD_USERS: '100,100' }, { LOAD_ROUNDS: '6' }]) {
    await assert.rejects(main(env));
  }
});

test('real localhost traffic writes a report, preserves measured failure, and closes its server', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'hub-isolated-load-'));
  let requests = 0;
  let failMeasured = false;
  const server = createServer((request, response) => {
    requests++;
    assert.equal(request.method, 'GET');
    assert.ok(['/', '/pricing', '/api/health'].includes(request.url));
    response.writeHead(failMeasured && request.headers['x-isolated-load-phase'] ? 503 : 200);
    response.end('fixture');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const file = join(directory, 'report.json');
  try {
    const env = { LOAD_BASE_URL: origin, LOAD_USERS: '3,4', LOAD_ROUNDS: '2', LOAD_REPORT_PATH: file };
    const report = await main(env);
    assert.equal(requests, 3 + (3 + 4) * 2);
    assert.ok(report.results.every(x => x.passed && x.failed === 0));
    assert.deepEqual(JSON.parse(await readFile(file, 'utf8')), report);
    failMeasured = true;
    await assert.rejects(main(env), /budget failure/);
    const failed = JSON.parse(await readFile(file, 'utf8'));
    assert.ok(failed.results.every(x => x.passed === false && x.failed === x.requests));
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
    await rm(directory, { recursive: true, force: true });
  }
  await assert.rejects(fetch(origin, { signal: AbortSignal.timeout(1000) }));
});
