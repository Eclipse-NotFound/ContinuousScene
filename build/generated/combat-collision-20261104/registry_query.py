import sqlite3, json
c = sqlite3.connect(r'shared-knowledge/knowledge-validation/coordination/test-runs.sqlite3')
c.row_factory = sqlite3.Row
tables = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
print('tables:', tables)
for t in tables:
    cols = [r[1] for r in c.execute('PRAGMA table_info(' + t + ')')]
    print('==', t, cols)
    for r in c.execute('select * from ' + t + ' order by rowid desc limit 6'):
        row = dict(r)
        if 'payload' in row and isinstance(row['payload'], str) and len(row['payload']) > 200:
            row['payload'] = row['payload'][:200] + '...'
        print('   ', row)
