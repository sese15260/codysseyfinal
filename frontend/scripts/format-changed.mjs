import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, resolve, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import prettier from 'prettier'

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const root = resolve(frontend, '..')
const mode = process.argv[2]

if (mode !== 'write' && mode !== 'check') {
  console.error('Usage: node scripts/format-changed.mjs write|check')
  process.exit(2)
}

function git(...args) {
  return execFileSync('git', args, { cwd: root, encoding: 'utf8' })
}

function nulPaths(output) {
  return output.split('\0').filter(Boolean)
}

function changedPaths() {
  if (process.env.CI === 'true') {
    let baseSha = process.env.BASE_SHA?.trim()
    if (!baseSha || /^0+$/.test(baseSha)) {
      try {
        baseSha = git('rev-parse', 'HEAD^').trim()
      } catch {
        baseSha = git('rev-parse', 'HEAD').trim()
      }
    }
    const base = git('merge-base', baseSha, 'HEAD').trim()
    return nulPaths(
      git('diff', '--name-only', '--diff-filter=ACMRT', '-z', base, 'HEAD', '--', 'frontend/'),
    )
  }

  return [
    ...nulPaths(git('diff', '--name-only', '--diff-filter=ACMRT', '-z', 'HEAD', '--', 'frontend/')),
    ...nulPaths(git('ls-files', '--others', '--exclude-standard', '-z', '--', 'frontend/')),
  ]
}

const candidates = [...new Set(changedPaths())]
const targets = []
for (const repoPath of candidates) {
  const absolute = resolve(root, repoPath)
  const frontendPath = relative(frontend, absolute)
  if (frontendPath.startsWith(`..${sep}`) || frontendPath === '..' || !existsSync(absolute)) {
    continue
  }
  const info = await prettier.getFileInfo(absolute, {
    ignorePath: resolve(frontend, '.prettierignore'),
    resolveConfig: true,
  })
  if (!info.ignored && info.inferredParser) {
    targets.push(frontendPath)
  }
}

if (targets.length === 0) {
  console.log('No changed frontend files supported by Prettier.')
  process.exit(0)
}

console.log(`Checking ${targets.length} changed frontend file(s).`)
const prettierBin = resolve(frontend, 'node_modules/prettier/bin/prettier.cjs')
const result = spawnSync(
  process.execPath,
  [prettierBin, mode === 'write' ? '--write' : '--check', ...targets],
  {
    cwd: frontend,
    stdio: 'inherit',
  },
)
process.exit(result.status ?? 1)
