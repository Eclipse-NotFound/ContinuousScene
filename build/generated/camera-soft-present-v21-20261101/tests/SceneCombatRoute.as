package tests {
    import flash.utils.getTimer;

    /** Selects existing terrain once, before actors are placed or timing starts.
     * Does not edit terrain, move actors, alter AI, or call simulation steps.
     * A rejected map throws with evidence and, if available, an UNSELECTED
     * shorter-route option. The requested 400 px path never silently shrinks.
     */
    public class SceneCombatRoute {
        private static const TILE:int=40;
        private static const PATH:int=400;
        private static const GAP:int=320;
        private static const MARGIN:int=40;

        public static function select(w:*,preferredX:Number,preferredY:Number,requestedPath:int=PATH):Object {
            if(!w || !w.loc || !w.gg || !isFinite(preferredX) || !isFinite(preferredY))
                throw new Error("Combat route requires an active location and finite preferred position");
            if([100,200,400].indexOf(requestedPath)<0)throw new Error("Unsupported explicit combat route length");
            var begin:int=getTimer(),loc:*=w.loc;
            var width:int=int(loc.spaceX),height:int=int(loc.spaceY);
            if(width<3 || height<5 || !loc.space)throw new Error("Combat route map is too small");
            var clearance:Number=Math.max(120,Number(w.gg.scY)+12);
            var obstacles:Array=obstacleBounds(loc);
            var spans:Array=[],runs:int=0,cells:int=0;
            for(var row:int=3;row<height;++row) {
                var start:int=-1,top:Number=NaN;
                for(var col:int=1;col<width;++col) {
                    // Last column is a sentinel: never place a body on the map edge.
                    var floor:*=col<width-1?loc.space[col][row]:null;
                    var valid:Boolean=floor && fullFloor(floor,col,row)
                        && clearColumn(loc,col,Number(floor.phY1),clearance,height);
                    ++cells;
                    if(start>=0 && (!valid || Math.abs(Number(floor.phY1)-top)>.001)) {
                        ++runs;splitObjects(spans,start*TILE,col*TILE,top,clearance,obstacles);
                        start=-1;
                    }
                    if(valid && start<0){start=col;top=Number(floor.phY1);}
                }
            }
            var longest:Number=0;
            for each(var span:Object in spans)longest=Math.max(longest,span.right-span.left);
            var best:Object=choose(loc,spans,preferredX,preferredY,requestedPath,clearance);
            var evidence:Object={version:"existing-flat-combat-route-1",diagnosticFixture:true,
                preferred:{x:preferredX,y:preferredY,roomX:int(preferredX/1920),roomY:int(preferredY/1000)},
                map:{widthTiles:width,heightTiles:height},clearance:clearance,
                playerPath:requestedPath,minimumPlayerToEnemyGap:GAP,allowedEnemySpacing:[120,100,80],
                bodyMargin:MARGIN,scannedCells:cells,terrainRuns:runs,objectFreeSpans:spans.length,
                longestObjectFreeSpan:longest,obstaclesChecked:obstacles.length,
                checks:["full-width rectangular solid floor at identical height",
                    "continuous body clearance without walls, steps, shelves, ladders, doors, water or traps",
                    "no existing physical box or door intersects the full corridor",
                    "native line-of-sight from five player poses to all six enemy poses"],
                scope:"Initial placement only; later destruction, AI motion, visibility and firing must be observed during the run"};
            if(!best) {
                var alternatives:Array=[];
                for each(var shortPath:int in [200,100]) {
                    if(shortPath>=requestedPath)continue;
                    var shorter:Object=choose(loc,spans,preferredX,preferredY,shortPath,clearance);
                    if(shorter){shorter.unselected=true;shorter.requiresExplicitSelection=true;alternatives.push(shorter);}
                }
                evidence.selected=false;evidence.shorterOptions=alternatives;evidence.searchMs=getTimer()-begin;
                throw new Error("No existing "+requestedPath+" px combat route satisfies the full terrain/visibility checks: "+JSON.stringify(evidence));
            }
            evidence.selected=true;evidence.searchMs=getTimer()-begin;
            best.evidence=evidence;
            return best;
        }

        private static function fullFloor(t:*,col:int,row:int):Boolean {
            return int(t.phis)==1 && !t.shelf && int(t.diagon)==0 && !t.door && !t.trap
                && int(t.stair)==0 && int(t.water)==0
                && isFinite(Number(t.phX1)) && isFinite(Number(t.phX2))
                && isFinite(Number(t.phY1)) && isFinite(Number(t.phY2))
                && Number(t.phX1)<=col*TILE && Number(t.phX2)>=(col+1)*TILE
                && Number(t.phY1)>=row*TILE && Number(t.phY1)<(row+1)*TILE
                && Number(t.phY2)>Number(t.phY1);
        }

        private static function clearColumn(loc:*,col:int,top:Number,clearance:Number,height:int):Boolean {
            var first:int=int(Math.floor((top-clearance)/TILE));
            var last:int=int(Math.floor((top-.001)/TILE));
            if(first<0 || last>=height)return false;
            for(var row:int=first;row<=last;++row) {
                var t:*=loc.space[col][row];
                if(!t || t.door || t.trap || int(t.stair)!=0 || int(t.water)!=0)return false;
                if((int(t.phis)!=0 || t.shelf || int(t.diagon)!=0)
                    && Number(t.phY1)<top && Number(t.phY2)>top-clearance)return false;
            }
            return true;
        }

        private static function obstacleBounds(loc:*):Array {
            var out:Array=[];
            for each(var obj:* in loc.objs) {
                if(!obj || ("dead" in obj && obj.dead))continue;
                if(!(("phis" in obj && Number(obj.phis)>0) || ("shelf" in obj && obj.shelf)
                    || ("wall" in obj && Number(obj.wall)>0) || ("door" in obj && Number(obj.door)>0)))continue;
                var x1:Number=Number(obj.X1),x2:Number=Number(obj.X2),y1:Number=Number(obj.Y1),y2:Number=Number(obj.Y2);
                if(!isFinite(x1) || !isFinite(x2) || !isFinite(y1) || !isFinite(y2) || x2<x1 || y2<y1)
                    throw new Error("Cannot verify combat route: physical object has invalid bounds");
                // Include invisible physical objects too: visibility alone is not collision evidence.
                out.push({left:x1,right:x2,top:y1,bottom:y2});
            }
            return out;
        }

        private static function splitObjects(out:Array,left:Number,right:Number,top:Number,clearance:Number,obstacles:Array):void {
            if(right-left<80)return;
            var blocked:Array=[];
            for each(var b:Object in obstacles) {
                if(b.top<top && b.bottom>top-clearance && b.left<right && b.right>left)
                    blocked.push({left:Math.max(left,b.left),right:Math.min(right,b.right)});
            }
            blocked.sortOn("left",Array.NUMERIC);
            var cursor:Number=left;
            for each(b in blocked) {
                if(b.left>cursor)out.push({left:cursor,right:b.left,top:top});
                cursor=Math.max(cursor,b.right);
            }
            if(cursor<right)out.push({left:cursor,right:right,top:top});
        }

        private static function choose(loc:*,spans:Array,px:Number,py:Number,path:int,clearance:Number):Object {
            var best:Object=null;
            for each(var span:Object in spans) {
                for each(var spacing:int in [120,100,80]) {
                    var spanNeeded:Number=2*MARGIN+path+GAP+5*spacing;
                    if(span.right-span.left<spanNeeded)continue;
                    var low:Number=span.left+MARGIN;
                    var high:Number=span.right-MARGIN-path-GAP-5*spacing;
                    var x:Number=Math.max(low,Math.min(high,px)),y:Number=span.top-1;
                    var roomDistance:int=Math.max(Math.abs(int(x/1920)-int(px/1920)),Math.abs(int(y/1000)-int(py/1000)));
                    var distance:Number=(x-px)*(x-px)+(y-py)*(y-py);
                    if(best && (roomDistance>best.roomDistance || roomDistance==best.roomDistance
                        && (distance>best.distanceSquared || distance==best.distanceSquared && spacing<=best.enemySpacing)))continue;
                    var enemies:Array=[];
                    for(var i:int=0;i<6;++i)enemies.push({x:x+path+GAP+i*spacing,y:y});
                    var checks:int=0,clear:Boolean=true;
                    for(var pose:int=0;pose<=4 && clear;++pose) {
                        var playerX:Number=x+path*pose/4;
                        for each(var enemy:Object in enemies) {
                            ++checks;
                            // Both bodies fit inside the verified 120+ px corridor.
                            if(!loc.isLine(playerX,y-60,enemy.x,enemy.y-60)){clear=false;break;}
                        }
                    }
                    if(!clear)continue;
                    var candidate:Object={x:x,y:y,path:path,enemies:enemies,enemySpacing:spacing,
                        gapFromPlayerPathEnd:GAP,bodyClearance:clearance,
                        corridor:{left:x-MARGIN,right:enemies[5].x+MARGIN,top:span.top-clearance,floor:span.top},
                        originalFreeSpan:{left:span.left,right:span.right,floor:span.top},
                        checkedNativeSightLines:checks,roomDistance:roomDistance,distanceSquared:distance,
                        selectedRoom:{x:int(x/1920),y:int(y/1000)},
                        reason:roomDistance==0?"Existing clear platform in the preferred original room":"Nearest qualifying existing platform by original-room distance, then position"};
                    if(!best || roomDistance<best.roomDistance || roomDistance==best.roomDistance
                        && (distance<best.distanceSquared || distance==best.distanceSquared && spacing>best.enemySpacing))best=candidate;
                }
            }
            return best;
        }
    }
}
