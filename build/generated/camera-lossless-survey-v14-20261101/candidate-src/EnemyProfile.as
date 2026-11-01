package {
 /** 文化派系决定偏好；当前 fraction 只决定敌我，不参与派系命名。 */
 public class EnemyProfile {
  public static function make(s:Object):Object {
   var id:String=s.id || "";
   var family:String=s.family || "";
   var cls:String=s.cls || "";
   if(!family) {
    var names:Object={UnitRaider:"raider",UnitRanger:"ranger",UnitMerc:"merc",UnitSlaver:"slaver",UnitZebra:"zebra",UnitEncl:"encl"};
    family=names[cls] || "";
   }
   var styles:Object={raider:"掠夺者·猛攻",ranger:"铁骑卫·火力阵位",merc:"雇佣兵·稳健掩体",slaver:"奴隶贩子·机会进攻",zebra:"斑马军团·协同推进",encl:"英克雷·机动射击"};
   var supported:Boolean=styles[family]!=null && !s.boss;
   var training:int=(family=="ranger" || family=="encl" || family=="merc" || family=="zebra") ? 1 : 0;
   var eliteIds:Object={merc5:true,slaver5:true,slaver6:true,zebra5:true,ranger3:true,encl4:true};
   var elite:Boolean=Boolean(eliteIds[id]) || int(s.hero)>0;
   var base:int=1+int(Math.max(0,Number(s.level))/12);
   var tier:int=Math.max(1,Math.min(4,base+training+(elite ? 1 : 0)));
   var reasons:String="原版等级 "+int(s.level)+" → 基础 "+Math.min(4,base);
   if(training) reasons+="；训练 +1";
   if(eliteIds[id]) reasons+="；精英兵种 +1";
   else if(int(s.hero)>0) reasons+="；强化单位 +1（类型 "+int(s.hero)+"）";
   var aggressive:Number=family=="raider" ? 1 : family=="slaver" ? 0.8 : family=="zebra" ? 0.65 : 0.45;
   return {family:family,style:styles[family] || "原版行为",supported:supported,
    excluded:s.boss ? "特殊头目交还原版" : "未识别的兵种，交还原版",
    tier:tier,tierName:["","粗放","熟练","战术","精锐"][tier],source:reasons,
    confirm:Math.max(8,24-tier*4),memory:90+tier*45,reaction:Math.max(6,18-tier*3),
    aggression:aggressive,coverOptions:[0,1,2,4,8][tier],reportDelay:[0,36,24,12,6][tier],
    suppressDuration:family=="ranger" ? 120 : family=="raider" ? 60 : 90,
    retreatRatio:family=="raider" ? 0.18 : 0.3,elite:elite};
  }
 }
}
