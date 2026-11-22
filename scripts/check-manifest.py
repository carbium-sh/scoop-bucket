#!/usr/bin/env python3
"""Checks this bucket's Scoop manifests the way Scoop and its Excavator read them.

  check-manifest.py [--sums SHA256SUMS] [--live] [--dist-tags FILE] MANIFEST...

Always: Scoop's schema (from a pinned Scoop commit, refused unless its SHA-256 matches), the file style Scoop's bucket
tests ask for, no duplicate keys, autoupdate urls that give back url for the manifest's version, a #/ rename equal to
bin, and a checkver that reads npm's latest dist-tag of carbium (it moves only after a cli release passes carbium-js's
release checks, which GitHub's own latest release does not wait for).
--sums FILE: each hash must be the one Scoop's autoupdate reads for its file from FILE (a release's SHA256SUMS).
--live: the manifest must be npm's latest carbium (from checkver's url, or from --dist-tags FILE) and, without --sums,
its hashes must match that release's SHA256SUMS.
Needs python3-jsonschema. Exit 1 on any problem.
"""
import argparse, hashlib, json, re, sys, urllib.request
import jsonschema

SCHEMA = 'https://raw.githubusercontent.com/ScoopInstaller/Scoop/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/schema.json'
PIN = '64ec829c70758d3fba2c8c168a5901a64408a6493efda25f172b0fe4505caac0'
problems = []

def bad(where, msg): problems.append(f'{where}: {msg}')

def read(src):  # a local file or an https URL
    if not src.startswith('https://'):
        with open(src, 'rb') as f: return f.read()
    return urllib.request.urlopen(src, timeout=60).read()

def nodup(pairs):
    keys = [k for k, _ in pairs]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup: raise ValueError(f'duplicate key {dup}')
    return dict(pairs)

def latest(p, doc, dist_tags):
    """What Excavator should have found: npm's latest carbium."""
    v = json.loads(read(dist_tags or doc['checkver']['url'])).get('latest')
    if not isinstance(v, str) or not v: return bad(p, 'npm has no latest dist-tag for carbium')
    if v != doc.get('version'): bad(p, f"version {doc.get('version')} but npm's latest is {v!r}: Excavator has not updated it")
    return v

def check(p, schema, sumtext, live, dist_tags):
    raw = open(p, 'rb').read()
    if raw.startswith(b'\xef\xbb\xbf'): bad(p, 'UTF-8 BOM')
    if not raw.endswith(b'\n'): bad(p, 'no final newline')
    for n, line in enumerate(raw.decode('utf-8').splitlines(), 1):
        if line != line.rstrip(): bad(p, f'line {n}: trailing whitespace')
        if re.match(r' *\t', line): bad(p, f'line {n}: tab in indentation')
    try: doc = json.loads(raw, object_pairs_hook=nodup)
    except ValueError as e: return bad(p, f'JSON: {e}')
    for e in sorted(schema.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path))):
        bad(p, f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}")
    ver, cv = doc.get('version', ''), doc.get('checkver')
    if cv != {'url': 'https://registry.npmjs.org/-/package/carbium/dist-tags', 'jsonpath': '$.latest'}:
        return bad(p, "checkver must read npm's latest dist-tag of carbium: GitHub's newest release has not passed the release checks")
    if live and latest(p, doc, dist_tags) and sumtext is None:
        url = next(iter(doc['architecture'].values()))['url'].split('#')[0]
        src = doc['autoupdate']['hash']['url'].replace('$baseurl', url.rsplit('/', 1)[0])
        try: sumtext = read(src).decode('utf-8')
        except OSError as e: bad(p, f'{src}: {e}')
    auto = doc.get('autoupdate', {}).get('architecture', {})
    for arch, entry in doc.get('architecture', {}).items():
        url, sha = entry.get('url', ''), str(entry.get('hash', '')).lower()
        tmpl = auto.get(arch, {}).get('url')
        if tmpl is None: bad(p, f'{arch}: no autoupdate url')
        elif tmpl.replace('$version', ver) != url: bad(p, f'{arch}: autoupdate url with $version={ver} differs from url')
        if url.split('#/')[-1] != doc.get('bin'): bad(p, f"{arch}: url saves as {url.split('#/')[-1]} but bin is {doc.get('bin')}")
        if sumtext is None: continue
        base = url.split('#')[0].rsplit('/', 1)[-1]  # Scoop's lookup in SHA256SUMS: hash, blanks, anything, name, blank or end
        m = re.search(rf'([a-fA-F0-9]{{32,128}})[\x20\t]+.*{re.escape(base)}(?:\s|$)', sumtext, re.I)
        if not m: bad(p, f'{arch}: Scoop would not find {base} in SHA256SUMS')
        elif m[1].lower() != sha: bad(p, f'{arch}: hash differs from the SHA256SUMS line for {base}')

if __name__ == '__main__':
    a = argparse.ArgumentParser(usage=__doc__.split('\n\n')[1].strip())
    a.add_argument('manifest', nargs='+')
    a.add_argument('--sums')
    a.add_argument('--live', action='store_true')
    a.add_argument('--dist-tags')
    a = a.parse_args()
    body = read(SCHEMA)
    if hashlib.sha256(body).hexdigest() != PIN: sys.exit('Scoop schema: SHA-256 differs from the pin')
    schema = jsonschema.Draft7Validator(json.loads(body), format_checker=jsonschema.FormatChecker())
    sumtext = read(a.sums).decode('utf-8') if a.sums else None
    for p in a.manifest: check(p, schema, sumtext, a.live or bool(a.dist_tags), a.dist_tags)
    for line in problems: print(line)
    print(f'{len(problems)} problem(s)')
    sys.exit(1 if problems else 0)
