import {writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';

try {
  const raw = process.env.API_BASE_URL?.trim();
  if (!raw) throw new Error('API_BASE_URL is required');
  const url = new URL(raw);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash
      || !['', '/'].includes(url.pathname) || ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
    throw new Error('API_BASE_URL must be a public HTTPS origin');
  }
  const target = process.argv[2] || fileURLToPath(new URL('../config.js',import.meta.url));
  writeFileSync(target, `window.APP_CONFIG = ${JSON.stringify({API_BASE_URL:url.origin})};\n`, 'utf8');
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
