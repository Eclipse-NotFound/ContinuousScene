"""Flatten native factory/R&D artwork into one editable grid; no room loading at seams."""
from pathlib import Path
import copy,json,hashlib,xml.etree.ElementTree as E
MOD=Path(__file__).resolve().parents[1];ROOT=MOD.parents[1]
def build():
    nio=E.parse(ROOT/'Rooms/rooms_nio.xml').getroot().findall('room')
    plant=E.parse(ROOT/'Rooms/rooms_plant.xml').getroot().findall('room')
    layout=[[(nio,7),(nio,6),(nio,4),(nio,3)],[(plant,49),(nio,15),(nio,13),(nio,5)]]
    w,h=192,50;grid=[['A']*w for _ in range(h)]
    all=E.Element('all',sceneFormat='1');E.SubElement(all,'land',serial='1')
    room=E.SubElement(all,'room',name='工厂研发部·连续试验场',x='0',y='0',sceneWidth=str(w),sceneHeight=str(h),sceneRevision='factory-rd-1')
    E.SubElement(room,'options',backwall='tBackWall',music='music_plant_2')
    regions=E.SubElement(room,'sceneRegions');objects=[];sources=[];skipped=[]
    # This is a mechanics sandbox. Campaign scripts/portals/bosses are omitted explicitly.
    excluded={'player','exit','doorout','doorin','door','mainframe','npc','comp','area','trigger'}
    for ry,row in enumerate(layout):
        for rx,(pool,index) in enumerate(row):
            src=pool[index];ox,oy=rx*48,ry*25;rows=[(a.text or '').split('.') for a in src.findall('a')]
            assert len(rows)==25 and all_len(rows,48)
            for y in range(25):grid[oy+y][ox:ox+48]=rows[y]
            opt=src.find('options');attrs=opt.attrib if opt is not None else {}
            E.SubElement(regions,'region',x=str(ox),y=str(oy),width='48',height='25',backwall=attrs.get('backwall','tBackWall'),color=attrs.get('color',''),dark=attrs.get('dark','0'),source=src.get('name'))
            sources.append({'source':'nio' if pool is nio else 'plant','index':index,'name':src.get('name'),'offset':[ox,oy]})
            for tag in ('obj','back'):
                for node in src.findall(tag):
                    if tag=='obj' and (node.get('id') in excluded or node.get('scr') or node.get('land') or node.get('id','').startswith('door')):
                        skipped.append({'id':node.get('id'),'reason':'campaign or portal'});continue
                    c=copy.deepcopy(node)
                    for attr in list(c.attrib):
                        if attr.startswith('scr') or attr in ('fun','code','ref','link','land','loc','room','prob'):del c.attrib[attr]
                    for ch in list(c):
                        if ch.tag=='scr':c.remove(ch)
                    c.set('x',str(int(c.get('x'))+ox));c.set('y',str(int(c.get('y'))+oy));objects.append(c)
    def clear(x,y):
        old=grid[y][x];grid[y][x]=old[old.index('_'):] if '_' in old else '_'
    # Wide shared passages cut only the former separator strips, not entire interiors.
    for ry in range(2):
        for sx in (48,96,144):
            for y in range(ry*25+20,ry*25+24):
                for x in range(sx-3,sx+3):clear(x,y)
    # A continuous maintenance shaft joins the floors. AllData mat Cyrillic А = right ladder.
    for y in range(20,48):
        for x in range(90,94):grid[y][x]='_А' if x==93 else '_'
    for y in range(h):grid[y][0]=grid[y][-1]='A'
    grid[0]=['A']*w;grid[-1]=['A']*w
    for row in grid:E.SubElement(room,'a').text='.'.join(row)
    for node in objects:room.append(node)
    # Clear a known safe spawn pocket with a solid floor, leaving the rest of the design intact.
    spawnx,spawny=7,22
    for y in range(spawny-2,spawny+1):
        cells=room.findall('a')[y].text.split('.')
        for x in range(spawnx-2,spawnx+3):cells[x]='_'
        room.findall('a')[y].text='.'.join(cells)
    cells=room.findall('a')[spawny+1].text.split('.')
    for x in range(spawnx-2,spawnx+3):cells[x]='A'
    room.findall('a')[spawny+1].text='.'.join(cells)
    E.SubElement(room,'obj',id='player',x=str(spawnx),y=str(spawny))
    E.SubElement(room,'obj',id='box',x='12',y='22')
    dest=MOD/'maps/factory-rd.xml';dest.parent.mkdir(exist_ok=True);E.indent(all)
    dest.write_bytes(E.tostring(all,encoding='utf-8',xml_declaration=True))
    (MOD/'build/large-map/sample-provenance.json').write_text(json.dumps({'sources':sources,'skipped':skipped,'objects':len(objects),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Sample: {w}x{h}, {len(objects)} original objects/backdrops')
def all_len(rows,n):return all(len(row)==n for row in rows)
if __name__=='__main__':build()
