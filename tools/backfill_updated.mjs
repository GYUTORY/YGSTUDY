#!/usr/bin/env node
import { execSync } from 'child_process';
import { readFileSync, writeFileSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';

const REPO_ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const DOCS_DIR = join(REPO_ROOT, 'Develop');
const FRONT_RE = /^---\s*\n([\s\S]*?)\n---/;

function findMd(dir) {
  const result = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) result.push(...findMd(full));
    else if (entry.isFile() && entry.name.endsWith('.md')) result.push(full);
  }
  return result;
}

let fixed = 0;
for (const md of findMd(DOCS_DIR).sort()) {
  const content = readFileSync(md, 'utf8');
  const m = content.match(FRONT_RE);
  if (!m) continue;
  if (/^updated\s*:/m.test(m[1])) continue;

  const gitDate = execSync(
    `git log -1 --format=%ad --date=format:%Y-%m-%d -- "${relative(REPO_ROOT, md)}"`,
    { cwd: REPO_ROOT, encoding: 'utf8' }
  ).trim() || '2026-08-07';

  // 두 번째 --- 직전에 삽입
  const closeIdx = content.indexOf('\n---', m.index + 4);
  const newContent = content.slice(0, closeIdx + 1) + `updated: ${gitDate}\n` + content.slice(closeIdx + 1);
  writeFileSync(md, newContent, 'utf8');
  fixed++;
}

console.log(`완료: ${fixed}개 파일 updated 백필`);
