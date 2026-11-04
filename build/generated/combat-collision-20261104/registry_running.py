import sqlite3, json
c = sqlite3.connect(r'shared-knowledge/knowledge-validation/coordination/test-runs.sqlite3')
rows = [json.loads(r[0]) for r in c.execute('select payload from runs order by rowid desc limit 60')]
for r in rows:
    if r.get('resource') == 'game' and r.get('state') == 'running':
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print('---')
