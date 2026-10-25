"""One-shot owned game-window input; imports only reviewed v4 source, never its SWF."""
from pathlib import Path
import ast
import ctypes as C
import hashlib
import importlib.util
import inspect
import json
import math
import time

HERE=Path(__file__).resolve().parent
CAPABILITY=HERE.parent/'owned-mouse-capability-v4-20261025/run.py'
CAPABILITY_SHA='2C16D90AC24834BE291FDBF60D867933A64CCDA072383B2CBF93D8DDBE8E67F4'
POLICY_REASON='One native center mouse message before warmup, world mouse-tree ABBA; diagnostic, not gameplay acceptance'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()

assert sha(CAPABILITY)==CAPABILITY_SHA, 'Reviewed owned-window source changed'
spec=importlib.util.spec_from_file_location('world_mouse_owned_v4_source',CAPABILITY)
cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)


class DynamicOwnedWindow(cap.OwnedWindow):
    def select_ready(self,ready,app_id):
        self.client=[0,0,ready['stageWidth'],ready['stageHeight']]
        rows=self.windows()
        candidates=[row for row in rows if row['client']==self.client]
        if len(candidates)!=1 or candidates[0]['title']!=app_id:
            raise RuntimeError('No unique actual ready Stage client/title window: '+json.dumps(rows))
        self.hwnd_row=candidates[0]
        return rows

    def post_once(self,x,y):
        rows=self.windows()
        if [row for row in rows if row['client']==self.client]!=[self.hwnd_row] or not self.u.IsWindow(self.hwnd_row['hwnd']):
            raise RuntimeError('Original unique content window changed before message')
        self.verify();C.set_last_error(0);before=cap.stamp()
        ok=self.u.PostMessageW(self.hwnd_row['hwnd'],cap.WM_MOUSEMOVE,0,(y<<16)|x)
        code=0 if ok else C.get_last_error()
        return dict(before=before,after=cap.stamp(),accepted=bool(ok),winerror=code,
            hwnd=self.hwnd_row['hwnd'],message=cap.WM_MOUSEMOVE,wParam=0,lParam=(y<<16)|x,clientX=x,clientY=y)


class OwnedMouseHandshake:
    def __init__(self,hidden_class):
        self.hidden_class=hidden_class
        self.window=None;self.process=None;self.store=None;self.app_id=None
        self.started=None;self.posted_at=None;self.completed=False
        self.report=dict(version='mouse-world-owned-input-4',attempts=0,complete=False,errors=[],
            capabilitySource=str(CAPABILITY),capabilitySourceSHA256=CAPABILITY_SHA)

    def bind(self,process,descriptor,store,app_id):
        if self.process is not None:raise RuntimeError('Cannot bind a second process')
        if not app_id.startswith('pfe-modsettings-continuous-motion-'):
            raise RuntimeError('Independent motion AIR id required')
        self.process=process;self.app_id=app_id;self.store=store;self.started=time.perf_counter()
        self.window=DynamicOwnedWindow(process,descriptor,sha(descriptor),self.hidden_class)
        self.report.update(ownership=self.window.identity,storage=str(store),appId=app_id,boundAt=cap.stamp())

    def read(self,name):
        file=self.store/name
        if not file.is_file():return None
        value=json.loads(file.read_text('utf-8'))
        if value.get('appId')!=self.app_id:raise RuntimeError('Mouse file AIR identity mismatch')
        return value

    def poll(self,process,elapsed):
        if self.completed:return
        try:self._poll(process,elapsed)
        except BaseException as error:
            self.report['errors'].append(repr(error))
            raise RuntimeError('Owned mouse handshake failed; no fallback: '+repr(error)) from error

    def _poll(self,process,elapsed):
        if process is not self.process:raise RuntimeError('Original owned process changed')
        self.window.verify()
        if time.perf_counter()-self.started>180:raise RuntimeError('Scene mouse-ready timeout')
        if self.report['attempts']==0:
            ready=self.read('world-mouse-ready.json')
            if ready is None:return
            if (ready.get('version')!='mouse-world-native-4' or ready.get('scaleMode')!='noScale'
                    or ready.get('align')!='TL' or ready.get('windowTitle')!=self.app_id
                    or Path(ready['storageNativePath']).resolve()!=self.store.resolve()
                    or ready.get('mouseChildren') is not True or ready.get('mouseEnabled') is not True):
                raise RuntimeError('Actual game mouse readiness did not meet bounded geometry policy')
            width,height=ready['stageWidth'],ready['stageHeight']
            if any(type(v) is not int or not 1<=v<=32767 for v in (width,height)):
                raise RuntimeError('Actual client dimensions outside signed mouse message range')
            x,y=width//2,height//2
            if (ready.get('targetX'),ready.get('targetY'))!=(x,y):raise RuntimeError('Ready center mismatch')
            self.report['ready']=ready;self.report['ownedWindows']=self.window.select_ready(ready,self.app_id)
            self.report['attempts']=1
            self.report['post']=self.window.post_once(x,y)
            self.posted_at=time.perf_counter()
            if not self.report['post']['accepted']:raise RuntimeError('Native mouse queue rejected')
            return
        proof=self.read('world-mouse-proof.json')
        if proof is None:
            # AS3's 15-second failure path must finish and retain its actual
            # events/context before Python's owned-process cleanup deadline.
            if time.perf_counter()-self.posted_at>20:raise RuntimeError('Real runtime event/Timer proof timeout')
            return
        ready=self.report['ready'];event,timer=proof['event'],proof['laterTimer'];x,y=ready['targetX'],ready['targetY']
        if proof.get('version')!='mouse-world-native-4' or proof.get('ready')!=ready or event.get('seq',0)<=ready['eventSeq'] or event.get('type')!='mouseMove':
            raise RuntimeError('Runtime event does not follow actual readiness')
        if (event.get('buttonDown') is not False or not event.get('targetInWorld') or not event.get('pathReachedStage')
                or event.get('worldAncestorCount')!=1 or event.get('currentTargetIsStage') is not True):
            raise RuntimeError('Runtime mouse event did not hit actual world display tree')
        path=event.get('path',[])
        if not path or len(path)>64 or sum(node.get('isWorld') is True for node in path)!=1 or path[-1].get('isStage') is not True:
            raise RuntimeError('Actual world event ancestor path invalid')
        for row in (event,timer,event['directStageBefore'],event['directStageAfter']):
            if row.get('appId')!=self.app_id or (row.get('stageWidth'),row.get('stageHeight'))!=(ready['stageWidth'],ready['stageHeight']):
                raise RuntimeError('Runtime mouse readback identity/dimensions changed')
            if not cap.near(row.get('stageMouseX'),x) or not cap.near(row.get('stageMouseY'),y):
                raise RuntimeError('Actual Stage mouse coordinates differ from posted client center')
        # Event stageX/Y are retained, not corrected or used as direct Stage getters.
        # This trial proves fixed direct Stage position and actual world ancestry.
        for key,limit in (('eventStageX',ready['stageWidth']),('eventStageY',ready['stageHeight'])):
            value=event.get(key)
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<limit:
                raise RuntimeError('Derived MouseEvent Stage coordinates outside actual viewport')
        if timer.get('timerSeq',0)<=ready['timerSeq'] or timer.get('eventSeq',0)<event['seq'] or timer['atMs']<event['directStageAfter']['atMs']:
            raise RuntimeError('Independent later Timer readback missing')
        self.window.verify()
        accepted=dict(appId=self.app_id,eventSeq=event['seq'],targetX=x,targetY=y,nativePostAccepted=True)
        destination=self.store/'world-mouse-accepted.json'
        if destination.exists():raise RuntimeError('Do not overwrite mouse acceptance')
        temporary=destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(accepted),encoding='utf-8');temporary.replace(destination)
        self.report.update(proof=proof,accepted=accepted,complete=True,completedAt=cap.stamp())
        self.completed=True


def policy_adapter(module):
    """Return an isolated function clone; the shared module/file is never patched."""
    original=inspect.getsource(module.run_owned)
    edits=[
        ("    descriptor.write_text(descriptor_text,encoding='utf-8')",
         "    assert descriptor_text.count('<visible>false</visible>')==1\n"
         "    descriptor_text=descriptor_text.replace('<visible>false</visible>','<visible>true</visible>',1)\n"
         "    descriptor.write_text(descriptor_text,encoding='utf-8')"),
        ("policy['diagnosticOnly']='World display mouse hit testing disabled for attribution; input compatibility not accepted'",
         "policy['diagnosticOnly']="+repr(POLICY_REASON)),
        ("            record.child(process.pid)",
         "            record.child(process.pid)\n            policy['worldMouseInput']=_mouse_handshake.report\n"
         "            _mouse_handshake.bind(process,descriptor,store,app)"),
        ("                time.sleep(1)\n                try:policy['ownedProcessCpuSamples']",
         "                time.sleep(1)\n                if process.poll() is None:_mouse_handshake.poll(process,time.monotonic()-start)\n"
         "                try:policy['ownedProcessCpuSamples']"),
    ]
    changed=original
    for old,new in edits:
        assert changed.count(old)==1,old
        changed=changed.replace(old,new,1)
    restored=changed
    for old,new in reversed(edits):
        assert restored.count(new)==1
        restored=restored.replace(new,old,1)
    assert restored==original
    tree=ast.parse(changed)
    assert len(tree.body)==1 and isinstance(tree.body[0],ast.FunctionDef)
    scope=dict(module.__dict__);handshake=OwnedMouseHandshake(module.HiddenProcess)
    scope['_mouse_handshake']=handshake
    exec(compile(tree,'<owned-world-mouse-policy>','exec'),scope)
    digest=lambda text:hashlib.sha256(text.encode()).hexdigest().upper()
    return scope['run_owned'],dict(originalSHA256=digest(original),transformedSHA256=digest(changed),
        reverseExact=True,sharedModuleModified=False,ownedInputMessagesMaximum=1,
        privateDesktopVisibleThroughout=True,noGlobalCursorOrActivation=True,
        capabilitySourceSHA256=CAPABILITY_SHA),handshake
