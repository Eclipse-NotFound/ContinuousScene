from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-visible-room-reference-20261027'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
assert not (HERE/'prepare.py').exists()
s=(BASE/'prepare.py').read_text('utf-8-sig').replace('camera-visible-room-reference-1','camera-visible-room-scout-1')
s=one(s,"'            var x:int=Math.round(player.X),y:int=Math.round(player.Y);'", "'            var x:int=Math.round(player.X),y:int=offsetY+Math.max(520,Math.min(700,Math.round(player.Y)-offsetY));'")
s=one(s,"'var offsetX:int=grafon.sceneLarge?3840:0,offsetY:int=grafon.sceneLarge?3000:0;'", "'var offsetX:int=grafon.sceneLarge?report.referenceSite.roomX*1920:0,offsetY:int=grafon.sceneLarge?report.referenceSite.roomY*1000:0;'")
s=one(s,'localCenterX:x-offsetX,localCenterY:y-offsetY,roomGridX:2,roomGridY:3,roomWidth:1920,roomHeight:1000','localCenterX:x-offsetX,localCenterY:y-offsetY,roomGridX:report.referenceSite.roomX,roomGridY:report.referenceSite.roomY,roomWidth:1920,roomHeight:1000')
s=one(s,"    return s\ndef runner_source():", "    s=s.replace('y:y+48','y:y+24').replace('y:y-48','y:y-24')\n    return s\ndef runner_source():")
s=one(s,'    return s\nif __name__', '''    s=one(s,'def options(name,mode):','def options(name,mode,room_x,room_y):')
    s=one(s,"'--native-room-x','2','--native-room-y','3'","'--native-room-x',str(room_x),'--native-room-y',str(room_y)")
    s=one(s,"    group=parser.add_mutually_exclusive_group(required=True)","    parser.add_argument('--room-x',type=int,default=2);parser.add_argument('--room-y',type=int,default=3)\\n    group=parser.add_mutually_exclusive_group(required=True)")
    s=one(s,'options(args.name,args.mode)','options(args.name,args.mode,args.room_x,args.room_y)')
    return s
if __name__''')
ast.parse(s);(HERE/'prepare.py').write_text(s,'utf-8')
s=(BASE/'site-methods.as.inc').read_text('utf-8-sig')
s=one(s,'            var ox:int=grafon.sceneLarge?96:0,oy:int=grafon.sceneLarge?75:0;', '            var ox:int=0,oy:int=0;')
s=one(s,'            for(var cy:int=13;cy<=17;++cy)for(var cx:int=20;cx<=28;++cx) {','''            for(var ry:int=0;ry<(grafon.sceneLarge?5:1);++ry)for(var rx:int=0;rx<(grafon.sceneLarge?5:1);++rx) {
            ox=rx*48;oy=ry*25;
            for(var cy:int=8;cy<=22;++cy)for(var cx:int=20;cx<=28;++cx) {''')
s=one(s,'var score:Number=Math.abs(cx*40+20-960)+Math.abs(cy*40-600);','''var roomX:int=grafon.sceneLarge?rx:int(world.land.locX),roomY:int=grafon.sceneLarge?ry:int(world.land.locY);
                var score:Number=(Math.abs(roomX-2)+Math.abs(roomY-3))*10000+Math.abs(cx*40+20-960)+Math.abs(cy*40-600);''')
s=one(s,'localY:cy*40,score:score','localY:cy*40,roomX:roomX,roomY:roomY,score:score')
s=one(s,'            report.referenceSite={roomX:2,roomY:3,','''            }
            report.referenceSite={roomX:best?best.roomX:-1,roomY:best?best.roomY:-1,''')
s=one(s,'No verified visible reference platform in room 2,3','No verified visible reference platform in scanned rooms')
s=one(s,'            var tileHash:uint=0;', '''            ox=grafon.sceneLarge?best.roomX*48:0;oy=grafon.sceneLarge?best.roomY*25:0;
            var tileHash:uint=0;''')
(HERE/'site-methods.as.inc').write_text(s,'utf-8')
for name in ['probe_patch.py','summary.py','axis_summary.py']:
    s=(BASE/name).read_text('utf-8-sig').replace('camera-visible-room-reference-1','camera-visible-room-scout-1')
    ast.parse(s);(HERE/name).write_text(s,'utf-8')
(HERE/'README.md').write_text('''# 可见房间参考：实际地形选点

上一配方指定2,3房间的中层平台不存在，失败保留，未产生计时。本配方只扩大离线选点：场景扫描25个原生房间的现有平台，优先2,3房间及中心；普通模式只在命令行指定且已由场景选出的同一房间选择。120px身体空间、物件碰撞与实体地面检查不变。允许低层地面，镜头中心在520–700，纵向路线±24，仍遵守原版边界。角色不离屏，原生地形不编辑。

其余继承上一配方：960完整间隔、原始模拟运行、私有桌面、一次放置、计时前五幅完整PNG、覆盖率至少30%、计时前稳定60帧、相机坐标和地形哈希另行配对。此为诊断，非战斗/跳跃或实际显示器FPS验收。
''','utf-8')
print('Derived new immutable recipe; previous failed reference retained')
