"""Offline, original-size motion atlas with exact Stage-geometry fallback.

Input is frozen C0E4; this module and transform() perform no file I/O. No
compilation, runtime verification, deployment, or combat benefit is implied.

Only an attached world with a finite 2D unit concatenated matrix, integral
Stage translation, scaleV == 1 and finite integral raw quake qualifies.
forcePresentation never bypasses this gate. Rejection restores native tiles,
clears pose eligibility and keeps existing atlas data/revisions without pumping
them. On re-entry, original revision copies precede any atlas presentation.
The first unforced eligible update still displays native, as in motion-only.

Eligible static updates retain the original cache allocation/sync work. This
adds one concatenatedMatrix getter (possibly allocating a Matrix) and constant
number checks per eligible update path, with no extra surface scan. Memory,
first construction, cache-boundary copies and native beginFrame churn remain.
This does not qualify RV/WB/SATS, dynamic impacts or actual battle performance.
The accepted RGB <= 2 / identical alpha boundary still needs runtime checks.
"""

from hashlib import sha256

VERSION = "camera-atlas-guarded-transform-1"
SOURCE_SHA256 = "C0E40368FD8BF6FE1413EC4C8D533C7034B18297AEB35119FBFEC4ADD5D93175"


EDITS = (
    (
        '            if(w.sats.active || g.visSats.visible){beginFrame();return;}',
        '            if(w.sats.active || g.visSats.visible){beginFrame();return;}\n            var presentationMatrix:*=w.visual.transform.concatenatedMatrix;\n            var geometryScale:Number=Number(w.cam.scaleV);\n            var geometryX:Number=Number(w.cam.vx),geometryY:Number=Number(w.cam.vy);\n            var geometryQuakeX:Number=Number(w.cam.quakeX),geometryQuakeY:Number=Number(w.cam.quakeY);\n            var geometryValid:Boolean=w.visual.stage!=null && presentationMatrix!=null &&\n                isFinite(geometryScale) && geometryScale==1 && isFinite(geometryX) && isFinite(geometryY) &&\n                isFinite(geometryQuakeX) && isFinite(geometryQuakeY) &&\n                geometryQuakeX==Math.floor(geometryQuakeX) && geometryQuakeY==Math.floor(geometryQuakeY) &&\n                isFinite(presentationMatrix.a) && isFinite(presentationMatrix.b) &&\n                isFinite(presentationMatrix.c) && isFinite(presentationMatrix.d) &&\n                isFinite(presentationMatrix.tx) && isFinite(presentationMatrix.ty) &&\n                presentationMatrix.a==1 && presentationMatrix.b==0 && presentationMatrix.c==0 && presentationMatrix.d==1 &&\n                presentationMatrix.tx==Math.floor(presentationMatrix.tx) && presentationMatrix.ty==Math.floor(presentationMatrix.ty);\n            if(!geometryValid){beginFrame();presentationPoseValid=false;return;}',
    ),
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
    (
        "        public function clear():void {",
        "        public function snapshot():Object {\n"
        "            var live:int=0;var attached:int=0;var bytes:Number=0;\n"
        "            for each(var bitmap:Bitmap in layers) {\n"
        "                if(bitmap.parent)++attached;\n"
        "                if(bitmap.bitmapData){++live;bytes+=Number(bitmap.bitmapData.width)*bitmap.bitmapData.height*4;}\n"
        "            }\n"
        "            return {version:\"atlas-motion-snapshot-1\",presented:presented,copies:copies,rebuilds:rebuilds,\n"
        "                layers:layers.length,attached:attached,liveBitmaps:live,pixelStorageBytes:bytes,\n"
        "                pendingHidden:hidden.length,hasBounds:bounds!=null,hasLocation:location!=null,poseValid:presentationPoseValid};\n"
        "        }\n"
        "        public function clear():void {",
    ),

)


def transform(source: str) -> str:
    """Return experimental AS3 from exact original text; perform no file writes."""
    if not isinstance(source, str):
        raise TypeError("source must be the frozen UTF-8 source decoded as str")
    if sha256(source.encode("utf-8")).hexdigest().upper() != SOURCE_SHA256:
        raise ValueError("Unexpected SceneRasterPresentation source")
    result = source
    for before, after in EDITS:
        if result.count(before) != 1:
            raise ValueError("Guarded atlas transform anchor is not unique: " + before)
        result = result.replace(before, after, 1)
    restored = result
    for before, after in reversed(EDITS):
        if restored.count(after) != 1:
            raise AssertionError("Guarded atlas inverse anchor is not unique")
        restored = restored.replace(after, before, 1)
    if restored != source:
        raise AssertionError("Guarded atlas transform changed unrelated original source")
    return result
