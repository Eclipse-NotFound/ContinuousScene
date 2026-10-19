"""Player step attribution in a diagnostic host, never a release input."""
from pathlib import Path
import importlib.util,re
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('parser',ROOT/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
source=(ROOT/'generated/v08-objects/source/fe/unit/Unit.as').read_text(encoding='utf-8-sig')
source=source.replace('   import fe.*;','   import flash.utils.getTimer;\n   import fe.*;',1)
pos=source.index('{',source.index('public class Unit'))+1
source=source[:pos]+'''
      public static var csPlayerProfile:Object={};
      public static function csPlayerRecord(name:String,ms:int):void {
         var row:Object=csPlayerProfile[name];if(!row)csPlayerProfile[name]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }
'''+source[pos:]
start,end=parser._body(source,'step');body=source[start+1:end]
def instrument(m):
    name=m.group(1)
    return 'if(this.player)csPlayerStart=getTimer();\n'+m.group(0)+'\nif(this.player)csPlayerRecord("'+name+'",getTimer()-csPlayerStart);'
body=re.sub(r'this\.(forces|control|run|checkWater|actions|setVisPos|setHpbarPos|animate)\([^;\n]*\);',instrument,body)
source=source[:start+1]+'\nvar csPlayerStart:int;\n'+body+source[end:]
out=ROOT/'generated/issues-player-profile/fe/unit/Unit.as';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(source,encoding='utf-8')
player=(ROOT/'cache/v08-player/scripts/fe/unit/UnitPlayer.as').read_text(encoding='utf-8-sig')
player=player.replace('   import fe.*;','   import flash.utils.getTimer;\n   import fe.*;',1)
start,end=parser._body(player,'animate');body=player[start+1:end]
sequence=0
def call_timer(m):
    global sequence
    sequence+=1
    return 'csAnimStart=getTimer();'+m.group(0)+'Unit.csPlayerRecord("animate.'+str(sequence)+'",getTimer()-csAnimStart);'
body=re.sub(r'(?:vis\.[\w.]+\.gotoAnd(?:Stop|Play)\([^;\n]*\)|this\.(?:setFilters|otherVisual)\(\));',call_timer,body)
player=player[:start+1]+'\nvar csAnimStart:int;\n'+body+player[end:]
out=ROOT/'generated/issues-player-profile/fe/unit/UnitPlayer.as'
out.write_text(player,encoding='utf-8')
