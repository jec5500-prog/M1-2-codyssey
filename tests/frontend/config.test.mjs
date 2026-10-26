import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync, readFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';

const script = resolve('frontend/scripts/build-config.mjs');
function build(value) {
  const dir = mkdtempSync(join(tmpdir(), 'codyssey-config-'));
  const result = spawnSync(process.execPath, [script, join(dir, 'config.js')], {
    env: {...process.env, API_BASE_URL: value ?? ''}, encoding:'utf8',
  });
  const text = result.status === 0 ? readFileSync(join(dir, 'config.js'),'utf8') : '';
  rmSync(dir, {recursive:true,force:true});
  return {result, text};
}
test('valid HTTPS API config is safely serialized',()=> {
  const {result,text} = build('https://m1-2-codyssey.onrender.com/');
  assert.equal(result.status,0, result.stderr);
  assert.match(text, /"API_BASE_URL":"https:\/\/m1-2-codyssey.onrender.com"/);
});
for (const url of ['', 'http://localhost:8000', 'javascript:alert(1)', "https://example.com/'unsafe"]) {
  test(`invalid deployment URL rejected: ${url}`,()=>assert.notEqual(build(url).result.status,0));
}
