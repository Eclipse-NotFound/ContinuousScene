"""Frozen pow2 atlas plus motion-only presentation; no build or runtime actions."""

from hashlib import sha256
import importlib.util
from pathlib import Path


VERSION = "camera-atlas-motion-only-transform-1"
SOURCE_SHA256 = "C0E40368FD8BF6FE1413EC4C8D533C7034B18297AEB35119FBFEC4ADD5D93175"
POW2_TRANSFORM_SHA256 = "C9C071AB87588DD4CB0CECA161A4CBD89F4C2E04F1C7DC832DB6AEE892B984CD"
POW2_TRANSFORM_PATH = Path(__file__).resolve().parent.parent / "camera-atlas-pow2-20261025" / "atlas_transform.py"
if sha256(POW2_TRANSFORM_PATH.read_bytes()).hexdigest().upper() != POW2_TRANSFORM_SHA256:
    raise ValueError("Frozen pow2 transform changed")
_spec = importlib.util.spec_from_file_location("camera_atlas_motion_only_pow2", POW2_TRANSFORM_PATH)
_pow2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pow2)


EDITS = (
    (
        "        public var rebuilds:int=0;",
        "        public var rebuilds:int=0;\n"
        "        public var presented:Boolean=false;\n"
        "        private var presentationPoseValid:Boolean=false;\n"
        "        private var presentationPoseX:Number=NaN;\n"
        "        private var presentationPoseY:Number=NaN;\n"
        "        private var presentationPoseScale:Number=NaN;",
    ),
    (
        "        public function update(w:*,enabled:Boolean):void {",
        "        public function update(w:*,enabled:Boolean,forcePresentation:Boolean=false):void {",
    ),
    (
        "            var needed:Rectangle=new Rectangle(Math.floor(view.x/side)*side,Math.floor(view.y/side)*side,",
        "            var nextPoseX:Number=Number(w.cam.vx);\n"
        "            var nextPoseY:Number=Number(w.cam.vy);\n"
        "            var nextPoseScale:Number=Number(w.cam.scaleV);\n"
        "            var nextPoseValid:Boolean=isFinite(nextPoseX) && isFinite(nextPoseY) && isFinite(nextPoseScale) && nextPoseScale>0;\n"
        "            var useAtlas:Boolean=forcePresentation || (nextPoseValid && presentationPoseValid &&\n"
        "                (nextPoseX!=presentationPoseX || nextPoseY!=presentationPoseY || nextPoseScale!=presentationPoseScale));\n"
        "            var needed:Rectangle=new Rectangle(Math.floor(view.x/side)*side,Math.floor(view.y/side)*side,",
    ),
    (
        "                for each(bitmap in s.bitmaps)if(bitmap.visible){hidden.push(bitmap);bitmap.visible=false;}",
        "                if(useAtlas)for each(bitmap in s.bitmaps)if(bitmap.visible){hidden.push(bitmap);bitmap.visible=false;}",
    ),
    (
        "            for each(bitmap in layers)bitmap.visible=true;",
        "            for each(bitmap in layers)bitmap.visible=useAtlas;\n"
        "            presented=useAtlas;\n"
        "            presentationPoseValid=nextPoseValid;\n"
        "            presentationPoseX=nextPoseX;presentationPoseY=nextPoseY;presentationPoseScale=nextPoseScale;",
    ),
    (
        "        public function beginFrame():void {",
        "        public function beginFrame():void {\n"
        "            presented=false;",
    ),
    (
        "            layers=[];bounds=null;revisions=new Dictionary(true);location=null;side=0;",
        "            layers=[];bounds=null;revisions=new Dictionary(true);location=null;side=0;\n"
        "            presentationPoseValid=false;\n"
        "            presentationPoseX=NaN;presentationPoseY=NaN;presentationPoseScale=NaN;\n"
        "            presented=false;",
    ),
)


def transform(source: str) -> str:
    """Return experimental AS3 from exact original text; perform no file writes."""
    if not isinstance(source, str):
        raise TypeError("source must be the frozen UTF-8 source decoded as str")
    if sha256(source.encode("utf-8")).hexdigest().upper() != SOURCE_SHA256:
        raise ValueError("Unexpected SceneRasterPresentation source")
    sized = _pow2.transform(source)
    result = sized
    for before, after in EDITS:
        if result.count(before) != 1:
            raise ValueError("Motion-only transform anchor is not unique: " + before)
        result = result.replace(before, after, 1)
    restored = result
    for before, after in reversed(EDITS):
        if restored.count(after) != 1:
            raise AssertionError("Motion-only inverse anchor is not unique")
        restored = restored.replace(after, before, 1)
    if restored != sized:
        raise AssertionError("Motion-only transform changed unrelated pow2 source")
    return result
