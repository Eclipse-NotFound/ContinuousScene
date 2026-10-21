"""Prepare uncompiled SATS/impact candidates from the verified BEFC renderer.

This command only writes generated source and its provenance. It cannot launch
AIR/Java, compile, test or deploy. The current user request pauses all testing.
Do not feed the old whole-game prepare/upgrade recipe into a later deployment.
"""
from pathlib import Path
import argparse
import hashlib
import json

B = Path(__file__).resolve().parent
ROOT = B.parents[2]
SOURCE = B / 'generated/motion-direction-rays/source/fe/graph/Grafon.as'
HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
SOURCE_SHA = '75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError('Source anchor changed: ' + old[:100])
    return source.replace(old, new, 1)


def sats(source):
    start = source.index('      private function sceneSats() : void')
    end = source.index('      // Per-native-Game state;', start)
    helper = (B.parent / 'src/patches/SceneSatsViewport.as.inc').read_text('utf-8')
    source = source[:start] + helper.rstrip() + '\n\n' + source[end:]
    source = once(source,
        '         this.sceneCullSurfaces();\n      }',
        '         this.sceneCullSurfaces();\n'
        '         if(this.visSats.visible) this.sceneCaptureSatsView();\n      }')
    source = once(source,
        '      private function sceneClear() : void\n      {',
        '      private function sceneClear() : void\n      {\n'
        '         this.sceneClearSats();')
    source = once(source,
        '      public function onSats(param1:Boolean) : *\n      {\n'
        '         this.visSats.visible = param1;',
        '      public function onSats(param1:Boolean) : *\n      {\n'
        '         if(!param1 && this.sceneLarge) this.sceneClearSats();\n'
        '         this.visSats.visible = param1;')
    return source


def impacts(source):
    # Preserve traversal, intersection semantics and random choices exactly.
    # Reuse one Rectangle instead of allocating one per resident cell per hit.
    start = source.index('      private function sceneApply(kind:String, args:Array) : void')
    end = source.index('      private function sceneRestoreMarks()', start)
    body = source[start:end]
    body = once(body, '         var affected:Rectangle;',
        '         var affected:Rectangle;\n'
        '         var surfaceBounds:Rectangle = new Rectangle();')
    body = once(body,
        '               if(affected && !affected.intersects(new Rectangle(entry.x,entry.y,this.rectX,this.rectY))) continue;',
        '               if(affected)\n'
        '               {\n'
        '                  surfaceBounds.x = entry.x; surfaceBounds.y = entry.y;\n'
        '                  surfaceBounds.width = this.rectX; surfaceBounds.height = this.rectY;\n'
        '                  if(!affected.intersects(surfaceBounds)) continue;\n'
        '               }')
    return source[:start] + body + source[end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['sats', 'impacts', 'combined'], default='sats')
    args = parser.parse_args()
    if sha(ROOT / 'pfe.swf') != HOST or sha(B / 'generated/fog-typed/pfe.swf') != HOST:
        raise RuntimeError('Installed host changed; reconcile the new source baseline first')
    if sha(SOURCE) != SOURCE_SHA:
        raise RuntimeError('Verified Grafon source changed')
    audit = json.loads((B / 'generated/fog-typed/strict-audit.json').read_text('utf-8'))
    if not audit.get('passed') or audit.get('changedMethods') != ['fe.loc.Location::0:1:lighting']:
        raise RuntimeError('Missing evidence that BEFC retains the original Grafon')
    source = SOURCE.read_text('utf-8-sig')
    changed = []
    added = []
    if args.mode in ('sats', 'combined'):
        source = sats(source)
        changed += ['sceneSats', 'sceneTick', 'sceneClear', 'onSats']
        added += ['sceneSatsViewKey', 'sceneClearSats', 'sceneCaptureSatsView', 'sceneCaptureSatsBatch']
    if args.mode in ('impacts', 'combined'):
        source = impacts(source)
        changed += ['sceneApply']
    out = B / ('generated/sats-viewport-20261021-' + args.mode)
    dest = out / 'source/fe/graph/Grafon.as'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(source, encoding='utf-8', newline='\n')
    manifest = {'status': 'source-only-uncompiled-untested', 'mode': args.mode,
        'baseHostSHA256': HOST, 'baseGrafonSourceSHA256': SOURCE_SHA,
        'candidateSourceSHA256': sha(dest), 'changedMethods': changed, 'addedMembers': added,
        'compiled': False, 'tested': False, 'deployed': False,
        'userConstraint': '2026-10-21: 先不做测试'}
    (out / 'provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps({'source': str(dest), **manifest}, ensure_ascii=False))


if __name__ == '__main__':
    main()
