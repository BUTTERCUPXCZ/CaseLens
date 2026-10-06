// Set the app's version everywhere it is written: node desktop/scripts/version.mjs 1.2.0
// Then commit, and tag the same version with a message (the release notes): git tag -a v1.2.0 -m "What's new"
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const version = process.argv[2]
if (!/^\d+\.\d+\.\d+$/.test(version ?? '')) {
  console.error('Usage: node desktop/scripts/version.mjs 1.2.0')
  process.exit(1)
}
const desktop = join(dirname(fileURLToPath(import.meta.url)), '..')
const edit = (file, change) => writeFileSync(join(desktop, file), change(readFileSync(join(desktop, file), 'utf8')))

edit('src-tauri/tauri.conf.json', (text) => text.replace(/"version": "[^"]+"/, `"version": "${version}"`))
edit('package.json', (text) => text.replace(/"version": "[^"]+"/, `"version": "${version}"`))
edit('src-tauri/Cargo.toml', (text) => text.replace(/^version = "[^"]+"/m, `version = "${version}"`))
edit('src-tauri/Cargo.lock', (text) => text.replace(/(name = "caselens"\nversion = )"[^"]+"/, `$1"${version}"`))
console.log(`CaseLens is now version ${version}. Commit, then: git tag -a v${version} -m "What's new" && git push origin v${version}`)
