from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-object-clip-v7-20261101'
helper=(OLD/'ObjectViewportProbe.as').read_text('utf-8')
helper=helper.replace('entries.push({layer:layer,mask:shape});','entries.push({layer:layer,mask:shape,cache:layer.cacheAsBitmap,index:entries.length});')
helper=helper.replace('if(mode=="objectClip") {','if(mode=="objectClip" || mode=="clipCache01" || mode=="clipCache0" || mode=="clipCache1") {')
helper=helper.replace('layer.x=left;layer.y=top;', '''layer.x=left;layer.y=top;
                    if(mode=="clipCache01" && item.index<2 || mode=="clipCache0" && item.index==0 || mode=="clipCache1" && item.index==1)
                        layer.cacheAsBitmap=true;''')
helper=helper.replace('item.layer.scrollRect=null;', 'item.layer.cacheAsBitmap=item.cache;item.layer.scrollRect=null;')
(HERE/'ObjectViewportProbe.as').write_text(helper,'utf-8')
source=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8')
source=source.replace('    import flash.display.DisplayObject;', '    import flash.geom.Rectangle;\n    import flash.display.DisplayObject;')
source=source.replace('camera-object-clip-7','camera-object-cache-8')
source=source.replace('["objectClip","objectMask","objectMask","objectClip"]','["clipCache01","clipCache0","clipCache1","clipCache1","clipCache0","clipCache01"]')
source=source.replace('frames:180','frames:90')
source=source.replace('            viewport=new ObjectViewportProbe(g);','''            report.objectCensus=[];
            var view:Rectangle=new Rectangle(-cam.vx/cam.scaleV,-cam.vy/cam.scaleV,cam.screenX/cam.scaleV,cam.screenY/cam.scaleV);
            for each(var objectLayer:* in g.visObjs) {
                var census:Object={total:objectLayer.numChildren,visibleInView:0,classes:{},cachedInView:0};
                for(var ci:int=0;ci<objectLayer.numChildren;++ci) {
                    var child:DisplayObject=objectLayer.getChildAt(ci);
                    if(!child.visible || !view.intersects(child.getBounds(g.visual)))continue;
                    ++census.visibleInView;
                    if(child.cacheAsBitmap)++census.cachedInView;
                    var cn:String=getQualifiedClassName(child);
                    census.classes[cn]=int(census.classes[cn])+1;
                }
                report.objectCensus.push(census);
            }
            report.unitCensus={};
            for each(var unit:* in loc.units){cn=getQualifiedClassName(unit);report.unitCensus[cn]=int(report.unitCensus[cn])+1;}
            viewport=new ObjectViewportProbe(g);''')
(HERE/'ContinuousSceneMotionMod.as').write_text(source,'utf-8')
work=(OLD/'work.py').read_text('utf-8')
work=work.replace("resource='offline'", "resource='game'").replace('wait=60)', 'wait=900)')
work=work.replace("candidate=ROOT/'pfe_before_unitvis_20261101-004531.swf'\n        assert sha(candidate)=='9D8662F6CF80E0AD20741EC2A4E7BEAD68446269EBB0ADB641C876DB68698B1D'", "candidate=ROOT/'pfe_before_unitvis_20261101-004531.swf'\n        expected='9D8662F6CF80E0AD20741EC2A4E7BEAD68446269EBB0ADB641C876DB68698B1D'\n        if args.host=='guard':\n            candidate=HERE.parent/'camera-turret-guard-r2-20261101/candidate.swf'\n            expected=json.loads((candidate.parent/'build.json').read_text('utf-8'))['candidateSHA256']\n        assert sha(candidate)==expected")
work=work.replace("choices=['current','a80']", "choices=['current','guard']")
(HERE/'work.py').write_text(work,'utf-8')
print('Prepared v8 bounded object-layer cache experiment.')
