package {
    import flash.utils.getDefinitionByName;

    /** Remove only native room-edge damage protection at joined interior seams.
     * Keep the generated wall image, geometry, objects and outer world shell. */
    public class NativeSceneWalls {
        public static function restore(land:*,regions:Array):int {
            var cells:Object={},entry:Object,restored:int=0;
            for each(entry in regions)cells[entry.lx+":"+entry.ly]=true;
            var Tile:Class=getDefinitionByName("fe.loc.Tile") as Class;
            var Form:Class=getDefinitionByName("fe.loc.Form") as Class;
            var decoded:Object={};
            for each(entry in regions) {
                var source:*=entry.source;
                if(!source.room || !source.room.xml)continue;
                for(var y:int=0;y<25;++y) {
                    var row:Array=String(source.room.xml.a[y]).split(".");
                    for(var x:int=0;x<48;++x) {
                        if(x!=0 && x!=47 && y!=0 && y!=24)continue;
                        // A corner touching any exterior or missing cell stays protected.
                        if((x==0 && !cells[(entry.lx-1)+":"+entry.ly]) ||
                           (x==47 && !cells[(entry.lx+1)+":"+entry.ly]) ||
                           (y==0 && !cells[entry.lx+":"+(entry.ly-1)]) ||
                           (y==24 && !cells[entry.lx+":"+(entry.ly+1)]))continue;
                        var tile:*=entry.space[x][y];
                        if(!tile.indestruct || tile.phis!=1 || tile.door || tile.trap)continue;
                        var form:*=Form.fForms[tile.front];
                        // Steel and intrinsically unbreakable materials remain unbreakable.
                        if(!form || form.indestruct || form.hp<=0)continue;
                        var code:String=row[source.mirror?47-x:x];if(code==null)continue;
                        var key:String=(source.mirror?"1:":"0:")+code;
                        var original:*=decoded[key];
                        if(!original) {
                            original=new Tile(0,0);original.dec(code,source.mirror);decoded[key]=original;
                        }
                        // Do not reinterpret empty cells filled by the room frame, or
                        // template-specific protection that mainFrame visually replaced.
                        if(original.phis<1 || original.indestruct)continue;
                        if(land.rnd) {
                            // Native mainFrame changes both material and health. Restore
                            // the current material's profile, not the underlying old image.
                            // Unknown later modifications are deliberately left intact.
                            if(tile.front!=land.act.border || tile.hp!=10000)continue;
                            tile.hp=form.hp;tile.thre=form.thre;
                        }else {
                            // Fixed maps only gain the edge flag in buildLoc. Retain
                            // health (including prior damage) and composite tile stats.
                            if(tile.front!=original.front || tile.hp>original.hp || tile.thre!=original.thre)continue;
                        }
                        tile.indestruct=false;++restored;
                    }
                }
            }
            return restored;
        }
    }
}
