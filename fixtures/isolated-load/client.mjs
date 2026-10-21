import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { performance } from 'node:perf_hooks';

const paths = ['/', '/pricing', '/api/health'];
export function localOrigin(raw) {
  const url = new URL(raw);
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' ||
      Number(url.port) < 1024 || url.pathname !== '/' || url.search || url.hash || url.username || url.password) {
    throw new Error('Only a nonprivileged localhost HTTP origin is permitted');
  }
  return url.origin;
}
const percentile = (sorted, fraction) => sorted.length ? sorted[Math.ceil(sorted.length * fraction) - 1] : null;

export async function main(env = process.env) {
  if (env.VERCEL || env.VERCEL_ENV || env.NODE_ENV === 'production') throw new Error('Hosted execution forbidden');
  const origin = localOrigin(env.LOAD_BASE_URL || 'http://127.0.0.1:3000');
  const users = (env.LOAD_USERS || '100,200').split(',').map(Number);
  const rounds = Number(env.LOAD_ROUNDS || 3);
  if (!users.length || users.length > 2 || new Set(users).size !== users.length ||
      users.some(value => !Number.isSafeInteger(value) || value < 1 || value > 200) ||
      !Number.isSafeInteger(rounds) || rounds < 1 || rounds > 5) throw new Error('Unbounded load configuration');
  const timeout = Number(env.LOAD_TIMEOUT_MS || 30000);
  const maxErrorPercent = Number(env.LOAD_MAX_ERROR_PERCENT || 1);
  const maxP95Ms = Number(env.LOAD_MAX_P95_MS || 15000);
  if (!Number.isSafeInteger(timeout) || timeout < 1000 || timeout > 60000 ||
      maxErrorPercent !== 1 || maxP95Ms !== 15000) throw new Error('Unexpected fixture budgets');
  for (const path of paths) {
    const response = await fetch(origin + path, { method: 'GET', redirect: 'manual', signal: AbortSignal.timeout(timeout) });
    await response.arrayBuffer();
    if (response.status !== 200) throw new Error('Fixture warmup failed');
  }
  const results = [];
  for (const concurrency of users) {
    const started = performance.now();
    const samples = [];
    await Promise.all(Array.from({ length: concurrency }, async (_, user) => {
      for (let round = 0; round < rounds; round++) {
        const before = performance.now();
        try {
          const response = await fetch(origin + paths[(user + round) % paths.length], {
            method: 'GET', redirect: 'manual', signal: AbortSignal.timeout(timeout),
            headers: { 'x-isolated-load-phase': 'measure' },
          });
          await response.arrayBuffer();
          samples.push({ success: response.status === 200, ms: Math.round(performance.now() - before) });
        } catch {
          samples.push({ success: false, ms: Math.round(performance.now() - before) });
        }
      }
    }));
    const latencies = samples.filter(x => x.success).map(x => x.ms).sort((a, b) => a - b);
    const failed = samples.length - latencies.length;
    const errorPercent = 100 * failed / samples.length;
    const elapsedMs = performance.now() - started;
    const p95Ms = percentile(latencies, .95);
    results.push({ concurrency, rounds, requests: samples.length, successes: latencies.length, failed,
      errorPercent: Number(errorPercent.toFixed(2)), elapsedMs: Math.max(1, Math.round(elapsedMs)),
      requestsPerSecond: Number((samples.length * 1000 / elapsedMs).toFixed(2)),
      p50Ms: percentile(latencies, .5), p95Ms, p99Ms: percentile(latencies, .99),
      passed: samples.length === concurrency * rounds && errorPercent <= maxErrorPercent && p95Ms !== null && p95Ms <= maxP95Ms });
  }
  const report = { mode: 'local-read-only', target: origin, publicPaths: paths,
    thresholds: { maxErrorPercent, maxP95Ms }, results };
  const output = resolve(env.LOAD_REPORT_PATH || 'artifacts/load-test-report.json');
  await mkdir(dirname(output), { recursive: true });
  await writeFile(output, JSON.stringify(report, null, 2) + '\n');
  if (results.some(x => !x.passed)) throw new Error('Fixture measured budget failure; report preserved');
  console.log(`Measured ${results.reduce((sum, x) => sum + x.requests, 0)} localhost GET requests`);
  return report;
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
