import sqlite3, json, time
c = sqlite3.connect(r'shared-knowledge/knowledge-validation/coordination/test-runs.sqlite3')
rows = [json.loads(r[0]) for r in c.execute('select payload from runs order by rowid desc limit 40')]
now = int(time.time() * 1000)
for r in rows:
    if r.get('resource') != 'game':
        continue
    keys = {k: r.get(k) for k in ('owner', 'purpose', 'status', 'state', 'releasedAt', 'heartbeatAt', 'expiresAt', 'startedAt')}
    print(json.dumps(keys, ensure_ascii=False))
