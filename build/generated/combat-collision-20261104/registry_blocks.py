import json, sqlite3

c = sqlite3.connect(r'shared-knowledge/knowledge-validation/coordination/test-runs.sqlite3')
rows = [json.loads(r[0]) for r in c.execute('select payload from runs order by rowid desc limit 60')]
for r in rows:
    if r.get('resource') != 'game':
        continue
    state = r.get('state')
    if state in ('running', 'needs-check', 'waiting'):
        print(json.dumps({k: r.get(k) for k in ('id', 'owner', 'purpose', 'state', 'created', 'updated', 'runner', 'note')},
                         ensure_ascii=False))
        print('---')
