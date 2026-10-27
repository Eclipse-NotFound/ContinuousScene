        private function environmentCheck():Object {
            var out:Object={sceneLarge:Boolean(grafon.sceneLarge),passed:false,cases:[],fieldsChecked:0,
                cachePresent:false,mapEntryRestored:false,originRestored:false,environmentRestored:false};
            if(!grafon.sceneLarge) {out.passed=true;out.skipped="ordinary-room";return out;}
            var land:*=location.land;
            var state:Object=api.state(land);
            require(state!=null && state.loc===location && state.byCell!=null && state.regions.length>1,"Missing native environment state");
            var names:Array=[];
            for(var envName:String in state.regions[0].environment)names.push(envName);
            grafon.sceneNativeEnvironment(location,player.X,player.Y);
            out.playerRegionSynchronized=true;
            var initial:Object=fields(location,names),oldX:*=land.minLocX,oldY:*=land.minLocY;
            var playerX:Number=player.X,playerY:Number=player.Y;
            var playerKey:String=(land.minLocX+int(Math.max(0,playerX)/1920))+":"+(land.minLocY+int(Math.max(0,playerY)/1000));
            var originalEntry:Object=state.byCell[playerKey];
            require(originalEntry!=null && names.length>0,"Player has no native environment");
            var checkPoint:Function=function(x:Number,y:Number,label:String):void {
                var key:String=(land.minLocX+int(Math.max(0,x)/1920))+":"+(land.minLocY+int(Math.max(0,y)/1000));
                var region:Object=state.byCell[key];
                var expected:Object=region==null?fields(location,names):region.environment;
                grafon.sceneNativeEnvironment(location,x,y);
                for each(var field:String in names) {
                    require(location[field]===expected[field],"Environment mismatch "+label+" / "+key+" / "+field);
                    ++out.fieldsChecked;
                }
                out.cases.push({label:label,x:isFinite(x)?x:String(x),y:isFinite(y)?y:String(y),key:key,found:region!=null,matched:true});
            };
            try {
                for each(var region:Object in state.regions) {
                    var left:Number=(Number(region.lx)-Number(land.minLocX))*1920;
                    var top:Number=(Number(region.ly)-Number(land.minLocY))*1000;
                    checkPoint(left+960,top+500,"region-center");
                    checkPoint(left,top,"inclusive-corner");
                    checkPoint(left+1919.999,top+999.999,"inside-corner");
                    checkPoint(left+1920,top+500,"next-x-boundary");
                    checkPoint(left+960,top+1000,"next-y-boundary");
                }
                var edges:Array=[-Infinity,-1,-0,0,NaN,Infinity,Number.MAX_VALUE,255*1920,256*1920,4294967296*1920];
                for each(var edge:Number in edges)checkPoint(edge,0,"numeric-x");
                edges=[-Infinity,-1,-0,0,NaN,Infinity,Number.MAX_VALUE,255000,256000,4294967296000];
                for each(edge in edges)checkPoint(0,edge,"numeric-y");
                // No native update runs between this temporary metadata change and restoration.
                land.minLocX=Number(oldX)+1;checkPoint(0,0,"changed-origin-x");
                land.minLocY=Number(oldY)+1;checkPoint(0,0,"changed-origin-y");
                land.minLocX=oldX;land.minLocY=oldY;checkPoint(playerX,playerY,"restored-origin");
                var changedEnvironment:Object={};
                for each(envName in names)changedEnvironment[envName]=originalEntry.environment[envName];
                require(isFinite(Number(changedEnvironment.maxdy)),"Expected finite native maxdy");
                changedEnvironment.maxdy=Number(changedEnvironment.maxdy)+1;
                state.byCell[playerKey]={environment:changedEnvironment};
                checkPoint(playerX,playerY,"replaced-entry-same-key");
                state.byCell[playerKey]=originalEntry;
                checkPoint(playerX,playerY,"restored-entry-same-key");
                var cache:Array=state._csEnvironmentCellKeysV1 as Array;
                out.cachePresent=cache!=null;
                if(cache!=null) {
                    require(cache[0]===oldX && cache[1]===oldY && cache[2] is Array,"Cache origin not restored");
                    var columns:Array=cache[2] as Array;
                    out.cachedKeys=0;
                    for(var cx:String in columns) {
                        require(int(cx)>=0 && int(cx)<=255 && String(int(cx))==cx,"Unbounded cache column");
                        var column:Array=columns[cx] as Array;require(column!=null,"Cache column type");
                        for(var cy:String in column) {
                            require(int(cy)>=0 && int(cy)<=255 && String(int(cy))==cy,"Unbounded cache row");
                            require(column[cy]===(Number(oldX)+int(cx))+":"+(Number(oldY)+int(cy)),"Stale cached key");
                            ++out.cachedKeys;
                        }
                    }
                }
                out.passed=true;
            } finally {
                land.minLocX=oldX;land.minLocY=oldY;state.byCell[playerKey]=originalEntry;
                grafon.sceneNativeEnvironment(location,playerX,playerY);
                out.mapEntryRestored=state.byCell[playerKey]===originalEntry;
                out.originRestored=land.minLocX===oldX && land.minLocY===oldY;
                out.environmentRestored=sameFields(location,initial);
                require(out.mapEntryRestored && out.originRestored && out.environmentRestored,"Environment component restoration failed");
            }
            return out;
        }
