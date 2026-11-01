package {
    import flash.utils.getTimer;

    /** Read-only, one-time camera-test fixture selection.
     * Follows tests.SceneCombatRoute's existing full-floor/clear-column and
     * physical-object rules, without its combat corridor, enemies or sight lines.
     * Never moves a unit, changes terrain/AI, or advances the simulation.
     */
    public class CameraProbePlatform {
        private static const TILE:int=40;
        private static const EDGE:Number=480;
        private static const SIDE:Number=40;

        public static function select(w:*,preferredX:Number,preferredY:Number):Object {
            if(!w || !w.loc || !w.gg || !isFinite(preferredX) || !isFinite(preferredY))
                throw new Error("Platform selection requires a location, player and finite preferred position");
            var started:int=getTimer(),loc:*=w.loc,player:*=w.gg;
            var columns:Number=Number(loc.spaceX),rows:Number=Number(loc.spaceY);
            if(!isFinite(columns) || !isFinite(rows) || columns!=Math.floor(columns) || rows!=Math.floor(rows)
                || columns<3 || rows<5 || !loc.space || !loc.objs)
                throw new Error("Cannot verify platform: invalid native terrain/object grid");
            var width:int=int(columns),height:int=int(rows);
            var limitX:Number=Number(loc.limX),limitY:Number=Number(loc.limY);
            if(!isFinite(limitX) || !isFinite(limitY) || limitX<=2*EDGE || limitY<=2*EDGE)
                throw new Error("Cannot verify platform: map lacks the required 480 px interior margin");
            var mapWidth:Number=Math.min(limitX,width*TILE),mapHeight:Number=Math.min(limitY,height*TILE);
            if(mapWidth<=2*EDGE || mapHeight<=2*EDGE)
                throw new Error("Cannot verify platform: terrain grid lacks the required interior margin");
            var px:Number=Number(player.X),x1:Number=Number(player.X1),x2:Number=Number(player.X2);
            var bodyHeight:Number=Number(player.scY);
            if(!isFinite(px) || !isFinite(x1) || !isFinite(x2) || x2<=x1 || x1>px || x2<px
                || !isFinite(bodyHeight) || bodyHeight<=0)
                throw new Error("Cannot verify platform: invalid native player body bounds");
            var leftExtent:Number=px-x1,rightExtent:Number=x2-px;
            var clearance:Number=Math.max(120,bodyHeight+12);
            var requiredWidth:Number=leftExtent+rightExtent+2*SIDE;
            var obstacles:Array=obstacleBounds(loc),spans:Array=[];
            var cells:int=0,runs:int=0;
            for(var row:int=3;row<height;++row) {
                var start:int=-1,top:Number=NaN;
                for(var col:int=1;col<width;++col) {
                    // Last column is the same non-placeable sentinel as the
                    // combat selector. The independent EDGE guard is stricter.
                    var column:*=loc.space[col];
                    var floor:*=col<width-1 && column?column[row]:null;
                    var valid:Boolean=floor && fullFloor(floor,col,row)
                        && clearColumn(loc,col,Number(floor.phY1),clearance,height);
                    ++cells;
                    if(start>=0 && (!valid || Math.abs(Number(floor.phY1)-top)>.001)) {
                        ++runs;splitObjects(spans,start*TILE,col*TILE,top,row,clearance,requiredWidth,obstacles);
                        start=-1;
                    }
                    if(valid && start<0){start=col;top=Number(floor.phY1);}
                }
            }
            var best:Object=null,longest:Number=0,eligible:int=0;
            for each(var span:Object in spans) {
                longest=Math.max(longest,span.right-span.left);
                var y:Number=span.floorY-1;
                if(y<EDGE || y>mapHeight-EDGE)continue;
                var low:Number=Math.max(EDGE,span.left+leftExtent+SIDE);
                var high:Number=Math.min(mapWidth-EDGE,span.right-rightExtent-SIDE);
                if(low>high)continue;
                ++eligible;
                var x:Number=Math.max(low,Math.min(high,preferredX));
                var distance:Number=(x-preferredX)*(x-preferredX)+(y-preferredY)*(y-preferredY);
                if(best && distance>=best.distanceSquared)continue;
                best={x:x,y:y,distanceSquared:distance,
                    platform:{left:span.left,right:span.right,y:y,floorY:span.floorY,row:span.row},
                    footprint:{left:x-leftExtent,right:x+rightExtent,top:y-bodyHeight,bottom:y},
                    clearanceRect:{left:x-leftExtent-SIDE,right:x+rightExtent+SIDE,
                        top:span.floorY-clearance,bottom:span.floorY},
                    edgeDistances:{left:x,right:mapWidth-x,top:y,bottom:mapHeight-y},
                    reason:"Nearest qualifying existing flat platform by squared Euclidean distance to the preferred position"};
            }
            var evidence:Object={version:"existing-camera-platform-1",diagnosticFixture:true,readOnly:true,
                preferred:{x:preferredX,y:preferredY},
                map:{widthTiles:width,heightTiles:height,limitX:limitX,limitY:limitY,
                    effectiveWidth:mapWidth,effectiveHeight:mapHeight},
                minimumEdgeMargin:EDGE,sideMarginEach:SIDE,
                body:{width:x2-x1,leftExtent:leftExtent,rightExtent:rightExtent,height:bodyHeight},
                requiredFlatWidth:requiredWidth,clearance:clearance,scannedCells:cells,terrainRuns:runs,
                objectFreeSpans:spans.length,eligibleSpans:eligible,longestObjectFreeSpan:longest,
                obstaclesChecked:obstacles.length,
                terrainWrites:0,objectWrites:0,actorMoves:0,simulationSteps:0,
                checks:["full-width rectangular solid floor at identical height; no shelf or slope",
                    "continuous head/body column clearance; no doors, stairs/ladders, water or traps",
                    "physical objects including invisible boxes/doors do not intersect the clearance rectangle",
                    "player anchor is at least 480 px inside all four effective map edges",
                    "native body width plus 40 px free on each horizontal side"],
                scope:"Initial fixture selection only. The caller must make its one reported placement, wait for natural physics to settle and independently verify the full camera route. Moving enemies, later terrain destruction and the renderer are not changed or qualified here."};
            if(!best) {
                evidence.selected=false;evidence.searchMs=getTimer()-started;
                throw new Error("No existing platform satisfies the camera fixture checks: "+JSON.stringify(evidence));
            }
            evidence.selected=true;
            evidence.floorCells=[];evidence.clearCells=[];
            var firstCol:int=int(Math.floor(best.clearanceRect.left/TILE));
            var lastCol:int=int(Math.ceil(best.clearanceRect.right/TILE))-1;
            var firstRow:int=int(Math.floor(best.clearanceRect.top/TILE));
            var lastRow:int=int(Math.floor((best.platform.floorY-.001)/TILE));
            for(col=firstCol;col<=lastCol;++col) {
                evidence.floorCells.push(tileEvidence(loc.space[col][best.platform.row],col,best.platform.row));
                for(row=firstRow;row<=lastRow;++row)
                    evidence.clearCells.push(tileEvidence(loc.space[col][row],col,row));
            }
            evidence.searchMs=getTimer()-started;best.evidence=evidence;
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
            if(first<0 || last>=height || !loc.space[col])return false;
            for(var row:int=first;row<=last;++row) {
                var t:*=loc.space[col][row];
                if(!t || t.door || t.trap || int(t.stair)!=0 || int(t.water)!=0)return false;
                if(int(t.phis)!=0 || t.shelf || int(t.diagon)!=0) {
                    var y1:Number=Number(t.phY1),y2:Number=Number(t.phY2);
                    // Invalid solid geometry is not evidence of an empty column.
                    if(!isFinite(y1) || !isFinite(y2) || y2<y1)return false;
                    if(y1<top && y2>top-clearance)return false;
                }
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
                    throw new Error("Cannot verify platform: physical object has invalid bounds");
                out.push({left:x1,right:x2,top:y1,bottom:y2});
            }
            return out;
        }

        private static function splitObjects(out:Array,left:Number,right:Number,top:Number,row:int,
            clearance:Number,minimumWidth:Number,obstacles:Array):void {
            if(right-left<minimumWidth)return;
            var blocked:Array=[];
            for each(var b:Object in obstacles) {
                if(b.top<top && b.bottom>top-clearance && b.left<right && b.right>left)
                    blocked.push({left:Math.max(left,b.left),right:Math.min(right,b.right)});
            }
            blocked.sortOn("left",Array.NUMERIC);
            var cursor:Number=left;
            for each(b in blocked) {
                if(b.left-cursor>=minimumWidth)out.push({left:cursor,right:b.left,floorY:top,row:row});
                cursor=Math.max(cursor,b.right);
            }
            if(right-cursor>=minimumWidth)out.push({left:cursor,right:right,floorY:top,row:row});
        }

        private static function tileEvidence(t:*,col:int,row:int):Object {
            return {col:col,row:row,phis:int(t.phis),shelf:Boolean(t.shelf),diagon:int(t.diagon),
                door:Boolean(t.door),trap:Boolean(t.trap),stair:int(t.stair),water:int(t.water),
                phX1:finiteOrNull(t.phX1),phX2:finiteOrNull(t.phX2),
                phY1:finiteOrNull(t.phY1),phY2:finiteOrNull(t.phY2)};
        }

        private static function finiteOrNull(value:*):Object {
            var number:Number=Number(value);return isFinite(number)?number:null;
        }
    }
}
