import { createServer } from 'node:http';
import { accessSync, constants, readFileSync } from 'node:fs';

const PORT = Number(process.env.PORT ?? 3000);
const DATA_DIR = process.env.DATA_DIR ?? './data';
const { version } = JSON.parse(
  readFileSync(new URL('../package.json', import.meta.url), 'utf8'),
);

function dataDirIsWritable() {
  try {
    accessSync(DATA_DIR, constants.R_OK | constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

const server = createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    const dataOk = dataDirIsWritable();
    res.writeHead(dataOk ? 200 : 503, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: dataOk ? 'ok' : 'error', version, data: dataOk }));
    return;
  }
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not found' }));
});

server.listen(PORT, () => {
  console.log(`Personal OS v${version} listening on port ${PORT}`);
});

for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
