"""Bullet collision candidates for ContinuousScene (2026-11-04).

Evidence behind this candidate set:
  * `Grafon.sceneTick` writes a viewport unit list into
    `World.w.visual.root["sceneCU"]`; `World.w.visual.root` is `fe.MainFE`, a
    *sealed* AS3 class, so the write throws `#1069` (swallowed) and every
    `Bullet.run` read throws `#1069` as well. With 30-60 rounds in flight that
    is tens of exception constructions per frame, and the collision loop always
    falls back to scanning all of `loc.units` (~130) per bullet:
    O(bullets x units) every frame.
  * Nothing else reads that channel (`sceneCU` appears only in test probes).

Candidates (method-only pcode replacement, class layout unchanged):
  scu-remove : drop both sides of the dead sceneCU channel. Semantics identical
               to the deployed host, strictly cheaper.
  grid       : above plus a real per-frame bucket table for the whole room,
               built in `sceneTick` and queried by the bullet's own position.
               Storage lives on `World.w.vgui` (a `MovieClip`, which is a
               `dynamic` class, unlike `Sprite` / `MainFE` / `Grafon`).
               Verified offline: `Sprite` rejects the write with `#1056`,
               `MovieClip` accepts it (see src/SpriteDynamicProbe.as).

Only `fe.graph.Grafon::sceneTick` and `fe.weapon.Bullet::run` change.
"""
from pathlib import Path
import hashlib, json, re, subprocess, sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
ROOT = MOD.parents[1]
SDK = ROOT / 'mods/Sandevistan/build/tools'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
GRAFON = MOD / 'build/generated/envkey-cache-20261102/host-export/scripts/fe/graph/Grafon.as'
BULLET = MOD / 'build/generated/camera-spatial-20261101/bullet-src/fe/weapon/Bullet.as'
BASE_HOST = MOD / 'build/backups/pfe_before_decal_nocancel_20261104-133604.swf'
BASE_SHA = 'A9B39CC742078D7A7D9F289EE408EDAE11C3AAC376A43246B306B91AC7AD2D94'
DEPLOYED_SHA = '1D2004AB4C972F199FDD6BCA708C8F483C8314FED77AEA477FB9544F33AB02F3'
GRAFON_CLASS = 'fe.graph.Grafon'
BULLET_CLASS = 'fe.weapon.Bullet'
CFG = {'cell': 512, 'margin': 96}
sys.path.insert(0, str(MOD / 'tools'))
sys.path.insert(0, str(MOD / 'build'))
sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
import stutter_host as sh
import stutter_opt as opt
from pcode_plan import abc_methods
from test_registry import Registration

EARLY_OLD = '''         if(!this.sceneLarge || this.loc == null)
         {
            return;
         }'''
EARLY_NEW = '''         if(!this.sceneLarge || this.loc == null)
         {
            if(World.w != null && World.w.vgui != null)
            {
               World.w.vgui["__csBulletGridV1"] = null;
            }
            return;
         }'''

LIST_OLD = '''            vl = (-camera.vx - camera.quakeX) / scale - 500;
            vt = (-camera.vy - camera.quakeY) / scale - 500;
            vr = vl + camera.screenX / scale + 1000;
            vb = vt + camera.screenY / scale + 1000;
            cu = [];
            for each(cu2 in this.loc.units)
            {
               if(cu2.X >= vl && cu2.X <= vr && cu2.Y >= vt && cu2.Y <= vb)
               {
                  cu.push(cu2);
               }
            }
            cu.push(World.w.gg);
            try
            {
               World.w.visual.root["sceneCU"] = cu;
            }
            catch(cuErr:Error)
            {
            }'''

LIST_NEW = '''            var grid:* = World.w.vgui["__csBulletGridV1"];
            if(grid == null || grid.loc !== this.loc)
            {
               grid = {"loc":this.loc,"cell":512,"buckets":[],"gx":0,"gy":0,"empty":[],"stamp":0,
                  "units":-1,"ggX":0,"ggY":0};
               World.w.vgui["__csBulletGridV1"] = grid;
            }
            var gridCell:Number = grid.cell;
            var gridCountX:int = int(Math.ceil(this.loc.spaceX * Tile.tileX / gridCell));
            var gridCountY:int = int(Math.ceil(this.loc.spaceY * Tile.tileY / gridCell));
            if(gridCountX < 1)
            {
               gridCountX = 1;
            }
            if(gridCountY < 1)
            {
               gridCountY = 1;
            }
            if(grid.gx != gridCountX || grid.gy != gridCountY)
            {
               grid.gx = gridCountX;
               grid.gy = gridCountY;
               grid.buckets = [];
            }
            var gridBuckets:Array = grid.buckets;
            var gridSlot:int = 0;
            while(gridSlot < gridBuckets.length)
            {
               if(gridBuckets[gridSlot] != null)
               {
                  gridBuckets[gridSlot].length = 0;
               }
               ++gridSlot;
            }
            for each(var gridUnit:* in this.loc.units)
            {
               if(gridUnit == null || gridUnit.loc !== this.loc)
               {
                  continue;
               }
               var gridX0:int = int((gridUnit.X1 - 96) / gridCell);
               if(gridX0 < 0)
               {
                  gridX0 = 0;
               }
               var gridX1:int = int((gridUnit.X2 + 96) / gridCell);
               if(gridX1 >= gridCountX)
               {
                  gridX1 = gridCountX - 1;
               }
               var gridY0:int = int((gridUnit.Y1 - 96) / gridCell);
               if(gridY0 < 0)
               {
                  gridY0 = 0;
               }
               var gridY1:int = int((gridUnit.Y2 + 96) / gridCell);
               if(gridY1 >= gridCountY)
               {
                  gridY1 = gridCountY - 1;
               }
               var gridY:int = gridY0;
               while(gridY <= gridY1)
               {
                  var gridRow:int = gridY * gridCountX;
                  var gridX:int = gridX0;
                  while(gridX <= gridX1)
                  {
                     var gridIndex:int = gridRow + gridX;
                     var gridBucket:Array = gridBuckets[gridIndex];
                     if(gridBucket == null)
                     {
                        gridBucket = [];
                        gridBuckets[gridIndex] = gridBucket;
                     }
                     gridBucket.push(gridUnit);
                     ++gridX;
                  }
                  ++gridY;
               }
            }
            ++grid.stamp;
            grid.units = this.loc.units.length;
            if(World.w.gg != null)
            {
               grid.ggX = World.w.gg.X;
               grid.ggY = World.w.gg.Y;
            }'''

SCU_BLOCK = '''         var _collisionUnits:Array = loc.units;
         try {
            if(World.w != null && World.w.visual != null && World.w.visual.root != null) {
               var _cuList:* = World.w.visual.root["sceneCU"];
               if(_cuList is Array && _cuList.length > 0) _collisionUnits = _cuList;
            }
         } catch(_cuError:Error) {}
         for each(_loc2_ in _collisionUnits)'''

GRID_READ = '''         var _collisionUnits:Array = loc.units;
         if(!this.targetObj && loc.units != null && World.w != null && World.w.vgui != null)
         {
            var _gridData:* = World.w.vgui["__csBulletGridV1"];
            if(_gridData != null && _gridData.loc === loc && _gridData.units == loc.units.length)
            {
               var _gridGgX:Number = _gridData.ggX;
               var _gridGgY:Number = _gridData.ggY;
               if(loc.gg == null || Math.abs(loc.gg.X - _gridGgX) < 256 && Math.abs(loc.gg.Y - _gridGgY) < 256)
               {
                  var _gridCellSize:Number = _gridData.cell;
                  var _gridCellX:int = int(X / _gridCellSize);
                  var _gridCellY:int = int(Y / _gridCellSize);
                  if(_gridCellX >= 0 && _gridCellX < _gridData.gx && _gridCellY >= 0 && _gridCellY < _gridData.gy)
                  {
                     var _gridList:Array = _gridData.buckets[_gridCellY * _gridData.gx + _gridCellX];
                     _collisionUnits = _gridList == null ? _gridData.empty : _gridList;
                  }
               }
            }
         }
         for each(_loc2_ in _collisionUnits)'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()


def decal(text):
    old = sh.method(text, 'sceneApply')
    new = sh.once(old, '         this.sceneCancelWarm(affected);',
                  '         if(kind != "decal")\n         {\n            this.sceneCancelWarm(affected);\n         }')
    return text.replace(old, new)


def grafon_source(diagnostic):
    text = GRAFON.read_text(encoding='utf-8-sig')
    names = []
    if diagnostic:
        text, names = sh.phase(text)
    text = decal(text)
    tick = sh.method(text, 'sceneTick')
    tick = sh.once(tick, EARLY_OLD, EARLY_NEW)
    tick = sh.once(tick, 'if(this.loc.units != null && World.w.gg != null)',
                   'if(this.loc.units != null && World.w.gg != null && World.w.vgui != null)')
    tick = sh.once(tick, LIST_OLD, LIST_NEW)
    text = text.replace(sh.method(text, 'sceneTick'), tick)
    return text, list(dict.fromkeys(names + ['sceneTick']))


def bullet_source(grid):
    text = BULLET.read_text(encoding='utf-8-sig')
    if grid:
        text = sh.once(text, SCU_BLOCK, GRID_READ)
    else:
        text = sh.once(text, SCU_BLOCK, '         for each(_loc2_ in loc.units)')
    return text, ['run']


def build(tag, kind):
    """kind: scu-remove | grid | scu-remove-diag | grid-diag"""
    out = HERE / tag
    out.mkdir(exist_ok=False)
    assert sha(BASE_HOST) == BASE_SHA, 'formal host changed'
    diagnostic = kind.endswith('-diag')
    grid = kind.startswith('grid')
    files, names = {}, {}
    files[GRAFON_CLASS], names[GRAFON_CLASS] = grafon_source(diagnostic)
    files[BULLET_CLASS], names[BULLET_CLASS] = bullet_source(grid)
    for cls, text in files.items():
        target = out / 'source' / Path(*cls.split('.')).with_suffix('.as')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    receipt = {'kind': kind, 'host': sha(BASE_HOST),
               'baseTag': 'decal-nocancel' if diagnostic else 'decal-nocancel-clean',
               **CFG, 'methods': names, 'compiled': False, 'deployed': False}

    def ff(*args):
        command = [str(JAVA), '-Xmx1400m', '-jar', str(SDK / 'ffdec/ffdec-cli.jar'), *map(str, args)]
        with (out / 'ffdec.log').open('ab') as log:
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            lease.child(proc.pid)
            proc.wait(900)
        if proc.returncode:
            raise RuntimeError('FFDec failed; see ffdec.log')
        lease.child_stopped()

    with Registration(owner='ContinuousScene / bullet spatial candidates', purpose=tag,
                      resource='offline', run_dir=out, evidence=out, wait=120) as lease:
        try:
            ff('-swf2xml', BASE_HOST, out / 'base.xml')
            ff('-importScript', BASE_HOST, out / 'donor.swf', out / 'source')
            for cls in files:
                slug = cls.replace('.', '_')
                for label, swf in [('original', BASE_HOST), ('donor', out / 'donor.swf')]:
                    ff('-format', 'script:pcode', '-selectclass', cls, '-export', 'script',
                       out / (label + '-pcode-' + slug), swf)
            methods = abc_methods(out / 'base.xml')
            specs, keys = [], []
            for cls in files:
                slug = cls.replace('.', '_')
                relative = Path(*cls.split('.')).with_suffix('.pcode')
                original = (out / ('original-pcode-' + slug) / 'scripts' / relative).read_text(encoding='utf-8-sig')
                donor = (out / ('donor-pcode-' + slug) / 'scripts' / relative).read_text(encoding='utf-8-sig')
                for name in names[cls]:
                    start = re.search(r'\bfunction ' + name + r'\(', donor).end()
                    first = re.search(r'\bmethod\s*\n', donor[start:]).start() + start
                    last = donor.index('end ; method', first) + len('end ; method')
                    code = donor[first:last]
                    old_start = re.search(r'\bfunction ' + name + r'\(', original).end()
                    old_end = original.index('end ; method', old_start)
                    old_ns = list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)', original[old_start:old_end])))
                    new_ns = list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)', code)))
                    if new_ns:
                        assert len(old_ns) == len(new_ns), (name, old_ns, new_ns)
                        for a, b in zip(new_ns, old_ns):
                            code = code.replace(a, b)
                    prior = set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)', original))
                    used = set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)', code))
                    assert used <= prior, (name, used - prior)
                    key = next(n for n in methods if n.endswith(':' + name) and cls + '::' in n)
                    path = out / (slug + '__' + name + '.pcode')
                    path.write_text(code + '\n', encoding='utf-8')
                    keys.append(key)
                    specs.extend([cls, str(path), str(methods[key][0])])
            (out / 'replace.txt').write_text('\n'.join(specs) + '\n', encoding='utf-8')
            ff('-replace', BASE_HOST, out / 'candidate.swf', out / 'replace.txt')
            ff('-swf2xml', out / 'candidate.swf', out / 'candidate.xml')
            audit = opt.load('stutter_audit', MOD / 'build/renderer-audit.py')
            assert audit.classes(out / 'base.xml') == audit.classes(out / 'candidate.xml'), 'Class layout changed'
            after = abc_methods(out / 'candidate.xml')
            changed = [n for n, pair in methods.items()
                       if (None if pair is None else pair[1].attrib['codeBytes'])
                       != (None if after[n] is None else after[n][1].attrib['codeBytes'])]
            assert set(changed) == set(keys), (sorted(changed), sorted(keys))
            assert sha(BASE_HOST) == receipt['host'], 'formal host changed during build'
            output = sha(out / 'candidate.swf')
            if not diagnostic:
                assert output != DEPLOYED_SHA
            receipt.update(compiled=True, output=output, changedMethods=changed, classesUnchanged=True)
            lease.outcome = 'passed'
            lease.note = 'Method-only candidate built; runtime evidence pending'
        finally:
            (out / 'build.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({'tag': tag, 'output': receipt.get('output'), 'changed': receipt.get('changedMethods')}))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])


