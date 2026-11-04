package {
    import flash.utils.getDefinitionByName;
    import flash.utils.Dictionary;
    public class ActivityEvidence {
        public static const DIAGNOSTIC:Boolean=false;
        public static const ARM:String="?";
        private static var updates:int=0,totalMs:int=0,totalQ:int=0,totalBuilds:int=0;
        private static var lastMs:int=0,lastQ:int=0,lastBuilds:int=0;
        private static var boundaries:int=0,changed:int=0,compared:int=0,mismatches:int=0;
        private static var early:Array,checked:Boolean=false,input:Object,expected:Object;
        private static var examples:Array=[];
        private static var priorBullets:Dictionary=new Dictionary(true);
        private static var bulletBorn:int=0,bulletMoved:int=0,bulletGone:int=0,sleepTransitions:int=0,wakeTransitions:int=0,clipsObserved:int=0,clipsStopped:int=0;
        public static function reset():void {updates=totalMs=totalQ=totalBuilds=0;}
        private static function chain(loc:*):Array {
            var a:Array=[],cls:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
            for(var p:*=loc.firstObj;p;p=p.nobj) {
                var bullet:Boolean=p is cls;
                a.push(bullet?[p,true,p.off,p.X,p.Y,p.dx,p.dy,p.explRadius]:[p,false]);
                if(a.length>100000)throw new Error("Unbounded object chain");
            }
            return a;
        }
        private static function equal(a:*,b:*):Boolean {return a===b || (a is Number && b is Number && isNaN(a)&&isNaN(b));}
        public static function begin(loc:*,w:*,s:Object):void {
            early=chain(loc);checked=false;
            var seen:Dictionary=new Dictionary(true);
            for each(var row:Array in early)if(row[1]) {
                seen[row[0]]=row;
                var previous:Array=priorBullets[row[0]];
                if(!previous)++bulletBorn;
                else if(row[3]!==previous[3]||row[4]!==previous[4])++bulletMoved;
            }
            for(var previousBullet:* in priorBullets)if(!seen[previousBullet])++bulletGone;
            priorBullets=seen;
            input=ActivityFixture.capture(loc,w,s);
            expected=ActivityFixture.compare(input);
            ++compared;
            if(!expected.equal){++mismatches;if(examples.length<4)examples.push({kind:"AB",details:expected});}
        }
        public static function boundary(loc:*):void {
            if(checked)return;checked=true;++boundaries;
            var now:Array=chain(loc),same:Boolean=now.length==early.length;
            for(var i:int=0;same&&i<now.length;++i) {
                same=now[i].length==early[i].length;
                for(var j:int=0;same&&j<now[i].length;++j)same=equal(now[i][j],early[i][j]);
            }
            if(!same){++changed;if(examples.length<4)examples.push({kind:"read-timing",beforeLength:early.length,afterLength:now.length});}
        }
        public static function record(ms:int,q:int,builds:int,s:Object,loc:*):void {
            lastMs=ms;lastQ=q;lastBuilds=builds;
            ++updates;totalMs+=ms;totalQ+=q;totalBuilds+=builds;
            if(DIAGNOSTIC) {
                var actual:Object=ActivityFixture.project(loc,s);
                for(var i:int=0;i<actual.units.length;++i)if(actual.units[i]) {
                    if(!input.sleeping[i]&&actual.units[i].sleeping)++sleepTransitions;
                    if(input.sleeping[i]&&!actual.units[i].sleeping)++wakeTransitions;
                    var record:Object=s.records[loc.units[i]];
                    if(record)for each(var item:Object in record.clips) {
                        ++clipsObserved;if(!item.clip.isPlaying)++clipsStopped;
                    }
                }
                if(JSON.stringify(actual)!=JSON.stringify(expected.a.state)) {
                    ++mismatches;if(examples.length<4)examples.push({kind:"live-state",expected:expected.a.state,actual:actual});
                }
            }
        }
        public static function snapshot():Object {return {arm:ARM,diagnostic:DIAGNOSTIC,updates:updates,totalMs:totalMs,totalQ:totalQ,totalBuilds:totalBuilds,
            ms:lastMs,q:lastQ,builds:lastBuilds,boundaries:boundaries,changed:changed,compared:compared,mismatches:mismatches,examples:examples,
            bulletBorn:bulletBorn,bulletMoved:bulletMoved,bulletGone:bulletGone,sleepTransitions:sleepTransitions,wakeTransitions:wakeTransitions,clipsObserved:clipsObserved,clipsStopped:clipsStopped,
            cases:DIAGNOSTIC?ActivityFixture.cases():null};}
    }
}
