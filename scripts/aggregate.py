"""Turn a '[rating] <platform>' issue into one vote and rebuild ratings.json.

One vote per GitHub account and provider: a new vote replaces the old one.
Run by .github/workflows/aggregate.yml. `python scripts/aggregate.py --rebuild`
only recomputes ratings.json from votes/.
"""
import json, os, re, statistics, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOTES = ROOT / 'votes'
PLATFORM = re.compile(r'^[a-z0-9][a-z0-9_-]{1,31}$')
LOGIN = re.compile(r'^[A-Za-z0-9-]{1,39}$')
CAP = 5000
PRIOR_STARS, PRIOR_WEIGHT = 3.0, 5


def score(stars_sum, votes, ok, fail, p50_ms):
    stars = (stars_sum + PRIOR_STARS * PRIOR_WEIGHT) / (votes + PRIOR_WEIGHT)
    success = (ok + 1) / (ok + fail + 2)
    speed = 1 / (1 + p50_ms / 4000) if p50_ms else 0.5
    return round(100 * (0.6 * (stars - 1) / 4 + 0.3 * success + 0.1 * speed))


def clamp(x, hi):
    return max(0, min(hi, int(x or 0)))


def parse(body):
    m = re.search(r'```json\s*(\{.*?\})\s*```', body or '', re.S)
    if not m: raise ValueError('no rating data found')
    v = json.loads(m.group(1))
    p = str(v.get('platform', ''))
    if not PLATFORM.match(p): raise ValueError('unknown provider id')
    stars = int(v.get('stars', 0))
    if not 1 <= stars <= 5: raise ValueError('stars must be between 1 and 5')
    return {'platform': p, 'stars': stars, 'ok': clamp(v.get('ok'), CAP), 'fail': clamp(v.get('fail'), CAP), 'p50_ms': clamp(v.get('p50_ms'), 600000)}


def rebuild():
    out = {}
    for f in sorted(VOTES.glob('*/*.json')):
        try: v = json.loads(f.read_text('utf-8'))
        except ValueError: continue
        p = out.setdefault(f.parent.name, {'votes': 0, 'stars_sum': 0, 'ok': 0, 'fail': 0, 'lat': []})
        p['votes'] += 1; p['stars_sum'] += int(v['stars']); p['ok'] += int(v['ok']); p['fail'] += int(v['fail'])
        if v.get('p50_ms'): p['lat'].append(int(v['p50_ms']))
    for p in out.values():
        lat = p.pop('lat'); p['p50_ms'] = int(statistics.median(lat)) if lat else 0
        p['score'] = score(p['stars_sum'], p['votes'], p['ok'], p['fail'], p['p50_ms'])
    data = {'format': 'secretscript-provider-ratings', 'version': 1,
            'updated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'providers': dict(sorted(out.items()))}
    (ROOT / 'ratings.json').write_text(json.dumps(data, indent=1) + '\n', 'utf-8')


def main():
    if '--rebuild' in sys.argv:
        rebuild(); return
    ev = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text('utf-8'))
    issue = ev['issue']; user = issue.get('user') or {}; login = str(user.get('login', ''))
    try:
        if not LOGIN.match(login): raise ValueError('invalid account')
        if user.get('type') != 'User': raise ValueError('only personal accounts can vote')
        v = parse(issue.get('body'))
        d = VOTES / v['platform']; d.mkdir(parents=True, exist_ok=True)
        v['at'] = int(time.time())
        (d / (login.lower() + '.json')).write_text(json.dumps(v) + '\n', 'utf-8')
        msg = 'Thanks, your %d/5 rating for %s is counted. SecretScript shows it within a few hours.' % (v['stars'], v['platform'])
    except (ValueError, TypeError, KeyError) as e:
        msg = 'Rating not recorded: %s.' % e
    rebuild()
    (ROOT / 'result.txt').write_text(msg, 'utf-8')


if __name__ == '__main__':
    main()
