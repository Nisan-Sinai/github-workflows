import { createServer } from 'node:http';

const server = createServer((request, response) => {
  const allowed = request.method === 'GET' && ['/', '/pricing', '/api/health'].includes(request.url);
  response.writeHead(allowed ? 200 : 405, { 'content-type': 'application/json' });
  response.end(JSON.stringify({ status: allowed ? 'ok' : 'forbidden', fixture: 'localhost-only' }));
});
server.listen(3000, '127.0.0.1', () => console.log('Isolated fixture listening on 127.0.0.1:3000'));
process.on('SIGTERM', () => server.close(() => process.exit(0)));
