"""One-method Camera.calc candidate; the carrier owns the sole context record.

No Camera members, closures, timers, RNG calls, actor writes or CS source edits.
Compilation must freshly export Camera from the pinned current 80CF host and
prove its original calc body matches this already-inspected source reference.
"""
from pathlib import Path
import hashlib

VERSION = 'vertical-camera-band-1'
TARGET = 'fe.inter.Camera::0:1:calc'
HOST_SHA = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
XML_SHA = 'B92260A7A0DFA80EB129C60AEF273645C32BBBA9B3588770BD7083D6984E7E04'
REFERENCE_SHA = '4EB7D9B9E96B1CFF61A92A8297DC537CE1D488E051EF1236672F926CEA9A22A2'
STATE_KEY = 'verticalCameraState'

DECLARATIONS = '''
         var csVCZoom:Boolean = this.w.ctr.keyZoom;
         var csVCCarrier:* = null;
         var csVCAPI:* = null;
         var csVCState:* = null;
         var csVCUse:Boolean = false;
         var csVCReset:Boolean = false;
         var csVCLook:Boolean = false;
         var csVCScale:Number = Number(this.scaleV);
         var csVCFoot:Number = 0;
         var csVCHeight:Number = 0;
         var csVCBand:Number = 0;
         var csVCMargin:Number = 0;
'''

# This runs after the unmodified keyZoom handler, before native look blending.
CONTEXT = '''         // The state is on the existing dynamic API, never on Camera's class layout.
         csVCCarrier = this.w.main.getChildByName("ContinuousSceneCarrier");
         if(csVCCarrier != null && "nativeAPI" in csVCCarrier)
         {
            csVCAPI = csVCCarrier["nativeAPI"];
         }
         if(csVCAPI != null && csVCAPI.constructor === Object)
         {
            csVCState = csVCAPI["verticalCameraState"];
            csVCScale = Number(this.scaleV);
            csVCFoot = this.screenY / 2 + 100;
            csVCHeight = Number(param1.scY) * csVCScale;
            csVCMargin = 2 + Math.abs(this.quakeY);
            csVCBand = Math.max(0,Math.min(160,this.screenY * 0.18,
               csVCFoot - csVCHeight - csVCMargin,this.screenY - csVCMargin - csVCFoot));
            if(this.w.grafon.sceneLarge && param1 === this.w.gg && this.w.loc != null
               && !this.w.loc.sky && this.moved && this.maxvy > 0
               && isFinite(csVCScale) && csVCScale > 0
               && isFinite(csVCHeight) && csVCHeight > 0 && isFinite(csVCBand) && csVCBand > 0
               && isFinite(param1.X) && isFinite(param1.Y))
            {
               csVCLook = this.w.ctr.keyLook || this.showOn || this.otryv > 0 || this.camRun;
               csVCReset = csVCState == null || csVCState.constructor !== Object
                  || csVCState.version !== "vertical-camera-band-1"
                  || csVCState.camera !== this || csVCState.loc !== this.w.loc
                  || csVCState.scale !== csVCScale || csVCState.screenX !== this.screenX
                  || csVCState.screenY !== this.screenY;
               if(csVCReset)
               {
                  csVCState = {version:"vertical-camera-band-1",camera:this,loc:this.w.loc};
                  csVCAPI["verticalCameraState"] = csVCState;
               }
               else
               {
                  csVCReset = csVCZoom || Boolean(csVCState.lookActive)
                     || !isFinite(csVCState.lastPlayerX) || !isFinite(csVCState.lastPlayerY)
                     || Math.abs((param1.X - csVCState.lastPlayerX) * csVCScale) > this.screenX / 2
                     || Math.abs((param1.Y - csVCState.lastPlayerY) * csVCScale) > this.screenY / 2;
               }
               csVCUse = !csVCLook && !csVCReset;
               csVCReset = !csVCLook && csVCReset;
               csVCState.scale = csVCScale;
               csVCState.screenX = this.screenX;
               csVCState.screenY = this.screenY;
               csVCState.lastPlayerX = param1.X;
               csVCState.lastPlayerY = param1.Y;
               csVCState.lookActive = csVCLook;
            }
            else if(csVCState != null && csVCState.constructor === Object
               && csVCState.version === "vertical-camera-band-1")
            {
               // Discard our context on ordinary rooms/disabled or unsuitable cameras.
               csVCAPI["verticalCameraState"] = null;
            }
         }
'''

NATIVE_Y = '''                  if(this.ovy - param1.Y * this.scaleV > 5 && this.ovy - param1.Y * this.scaleV < 50)
                  {
                     this.Y = this.ovy - (this.ovy - param1.Y * this.scaleV) / 4;
                  }
                  else
                  {
                     this.Y = param1.Y * this.scaleV;
                  }
'''
Y_PREFIX = '''                  if(csVCReset)
                  {
                     this.Y = param1.Y * this.scaleV;
                  }
                  else if(csVCUse)
                  {
                     this.Y = Math.max(param1.Y * this.scaleV - csVCBand,
                        Math.min(this.ovy,param1.Y * this.scaleV + csVCBand));
                  }
                  else
                  {
'''
Y_SUFFIX = '''                  }
'''


def once(text, old, new):
    assert text.count(old) == 1, ('Nonunique exact anchor', old[:100])
    return text.replace(old, new, 1)


def read_reference(path):
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == REFERENCE_SHA
    return raw.decode('utf-8-sig').replace('\r\n', '\n')


def transform(source, parser, reference):
    assert 'csVC' not in source
    start, end = parser._body(source, 'calc')
    ra, rz = parser._body(reference, 'calc')
    old = source[start + 1:end]
    # The fresh current-host export is authoritative; reject changed native code.
    assert old == reference[ra + 1:rz], '80CF Camera.calc differs from inspected reference'
    body = DECLARATIONS + old
    body = once(body, '         if(this.moved)\n', CONTEXT + '         if(this.moved)\n')
    body = once(body, NATIVE_Y, Y_PREFIX + NATIVE_Y + Y_SUFFIX)
    restored = once(body, Y_PREFIX + NATIVE_Y + Y_SUFFIX, NATIVE_Y)
    restored = once(restored, CONTEXT, '')
    assert restored.startswith(DECLARATIONS)
    restored = restored[len(DECLARATIONS):]
    assert restored == old, 'Inverse must restore every native statement and branch'
    result = source[:start + 1] + body + source[end:]
    a, z = parser._body(result, 'calc')
    assert result[:a + 1] == source[:start + 1] and result[z:] == source[end:]
    assert result.count('Math.random(') == source.count('Math.random(')
    assert result.count('sceneTick(') == source.count('sceneTick(')
    assert 'getTimer' not in result and 'try\n' not in body and 'finally' not in body
    return result
