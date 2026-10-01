import { readFileSync } from 'node:fs';

export function parseEnv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) out[m[1]!] = m[2]!.replace(/^(['"])(.*)\1$/, '$2');
  }
  return out;
}

/** Later files win. Missing files are skipped. Values are never logged. */
export function loadEnv(...files: URL[]): Record<string, string> {
  let merged: Record<string, string> = {};
  for (const f of files) {
    try {
      merged = { ...merged, ...parseEnv(readFileSync(f, 'utf8')) };
    } catch {
      /* file absent */
    }
  }
  return merged;
}
