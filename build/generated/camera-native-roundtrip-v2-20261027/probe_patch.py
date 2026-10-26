"""Round-trip fixture with explicit null 2D matrices and 3D transform records."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-native-roundtrip-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('roundtrip_3d_metadata',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    source=source.replace('camera-native-roundtrip-1','camera-native-roundtrip-2')
    edits=[
        ('matrix:fields(m,["a","b","c","d","tx","ty"]),','matrix:m==null?null:fields(m,["a","b","c","d","tx","ty"]),'),
        ('concatMatrix:fields(cm,["a","b","c","d","tx","ty"]),','concatMatrix:cm==null?null:fields(cm,["a","b","c","d","tx","ty"]),'),
        ('                var bitmap:Bitmap=node as Bitmap;','''                record.matrix3D=null;
                if(node.transform.matrix3D!=null){
                    record.matrix3D=[];
                    for each(var component:Number in node.transform.matrix3D.rawData)record.matrix3D.push(component);
                }
                var projection:*=node.transform.perspectiveProjection;
                record.perspective=projection==null?null:{fieldOfView:projection.fieldOfView,focalLength:projection.focalLength,
                    center:{x:projection.projectionCenter.x,y:projection.projectionCenter.y}};
                var bitmap:Bitmap=node as Bitmap;'''),
        ('            report.nodeSnapshots.push(result);','''            report.nodeSnapshots.push(result);
            result.ancestors=[];
            for each(var ancestor:DisplayObject in [world.visual,world.visual.parent,grafon.visFon,grafon.visLight,grafon.visSats]){
                var filters:Array=[];
                for each(var af:* in ancestor.filters)filters.push(getQualifiedClassName(af));
                var am:Matrix=ancestor.transform.matrix;
                result.ancestors.push({className:getQualifiedClassName(ancestor),name:ancestor.name,visible:ancestor.visible,
                    alpha:ancestor.alpha,cache:ancestor.cacheAsBitmap,blend:ancestor.blendMode,mask:nodeId(ancestor.mask),
                    filters:filters,matrix:am==null?null:fields(am,["a","b","c","d","tx","ty"]),
                    color:fields(ancestor.transform.colorTransform,["redMultiplier","greenMultiplier","blueMultiplier","alphaMultiplier","redOffset","greenOffset","blueOffset","alphaOffset"])});
            }'''),
    ]
    for old,new in edits:
        assert source.count(old)==1,old;source=source.replace(old,new,1)
    return source

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
