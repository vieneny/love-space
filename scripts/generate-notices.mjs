import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '..');
const inventory = JSON.parse(execSync('pnpm licenses list --prod --json', { cwd: root, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 }));
const notices = ['Third-party frontend dependency notices', 'Generated from the installed pnpm lockfile. Includes build-time transitive packages.', ''];
const missing = [];
for (const license of Object.keys(inventory).sort()) {
  for (const pkg of inventory[license].sort((a, b) => a.name.localeCompare(b.name))) {
    const sections = new Set();
    for (const directory of pkg.paths || []) {
      for (const filename of fs.readdirSync(directory).filter(n => /^(licen[cs]e|copying|notice)([._-]|$)/i.test(n))) {
        const file = path.join(directory, filename);
        if (fs.statSync(file).isFile()) sections.add(fs.readFileSync(file, 'utf8').trim());
      }
    }
    notices.push('='.repeat(72), `${pkg.name} ${pkg.versions.join(', ')}`, `License: ${license}`, `Source: ${pkg.homepage || pkg.repository || 'See package registry metadata'}`, `Author: ${typeof pkg.author === 'string' ? pkg.author : JSON.stringify(pkg.author || '')}`, '');
    if (!sections.size) missing.push(pkg.name);
    notices.push(...sections, '');
    delete pkg.paths;
  }
}
fs.writeFileSync(path.join(root, 'docs/frontend-licenses.json'), JSON.stringify(inventory, null, 2) + '\n');
fs.writeFileSync(path.join(root, 'docs/THIRD_PARTY_NOTICES.txt'), notices.join('\n').replace(/[ \t]+$/gm, ''));
const destination = path.join(root, 'apps/miniapp/src/static/third-party-notices.txt');
fs.mkdirSync(path.dirname(destination), { recursive: true });
fs.copyFileSync(path.join(root, 'docs/THIRD_PARTY_NOTICES.txt'), destination);
console.log(`Notices generated. Packages without a root license text: ${missing.join(', ') || 'none'}`);
