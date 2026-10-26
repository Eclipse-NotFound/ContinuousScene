"""Keep optional metadata failures separate from the actual pixel invariant."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-native-roundtrip-v2-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('roundtrip_field_diagnostics',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py')

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    source=source.replace('camera-native-roundtrip-2','camera-native-roundtrip-3')
    edits=[
        ('            require(result.errors.length==0,"Display metadata incomplete");',
         '            result.complete=result.errors.length==0; // Optional metadata is not a pixel-identity claim.'),
        ('            if(depth>70 || result.nodes.length>=12000)',
         '            var readPhase:String="begin";\n            if(depth>70 || result.nodes.length>=12000)'),
        ('                var m:Matrix=node.transform.matrix,cm:Matrix=node.transform.concatenatedMatrix;',
         '                readPhase="matrix-and-color";\n                var m:Matrix=node.transform.matrix,cm:Matrix=node.transform.concatenatedMatrix;'),
        ('                var record:Object={id:nodeId(node)',
         '                readPhase="record-header";\n                var record:Object={id:nodeId(node)'),
        ('                for each(var filter:* in node.filters) {',
         '                record.complete=false;result.nodes.push(record);readPhase="filters";\n                for each(var filter:* in node.filters) {'),
        ('                    var f:Object={className:getQualifiedClassName(filter)};',
         '                    var f:Object={className:getQualifiedClassName(filter)};record.filters.push(f);'),
        ('                    record.filters.push(f);',''),
        ('                record.matrix3D=null;','                readPhase="matrix3D-and-projection";record.matrix3D=null;'),
        ('                var bitmap:Bitmap=node as Bitmap;','                readPhase="bitmap";var bitmap:Bitmap=node as Bitmap;'),
        ('                var clip:MovieClip=node as MovieClip;','                readPhase="movieclip";var clip:MovieClip=node as MovieClip;'),
        ('                var textField:TextField=node as TextField;','                readPhase="text";var textField:TextField=node as TextField;'),
        ('                result.nodes.push(record);','                record.complete=true;readPhase="children";'),
        ('            } catch(error:Error){result.errors.push(path+": "+error.message);}',
         '            } catch(error:Error){result.errors.push({path:path,phase:readPhase,message:error.message,matrixPresent:m!=null,concatMatrixPresent:cm!=null,colorPresent:ct!=null,concatColorPresent:cct!=null});}'),
    ]
    for old,new in edits:
        assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new,1)
    return source

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
