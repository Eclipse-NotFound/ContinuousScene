package
{
    import flash.desktop.NativeApplication;
    import flash.display.Sprite;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.getTimer;

    /** Offline equivalence + cost harness for the ContinuousScene bullet
     *  spatial-bucket candidate (build/generated/combat-collision-20261104).
     *
     *  1. Equivalence: the bucket table must return exactly the same first hit
     *     as the native "scan all units, break on hit" loop, including when
     *     units moved by up to MARGIN after the table was built.
     *  2. Cost: full scan vs bucket scan vs the sealed-class exception storm
     *     the deployed host pays per bullet per frame.
     *
     *  No game classes, no network, no mods: synthetic AABBs only. */
    public class BulletGridBench extends Sprite
    {
        private static const CELL:int = 512;
        private static const MARGIN:Number = 96;
        private static const MAP_W:Number = 9600;
        private static const MAP_H:Number = 5000;
        private static const UNITS:int = 130;
        private static const BULLETS:int = 40;
        private static const FRAMES:int = 900;
        private static const PICK_WARM:int = 3;
        private static const PICK_RUNS:int = 5;

        private var seed:uint = 9901001;
        private var lines:Array = [];
        private var failures:int = 0;

        private var count:int = UNITS;
        private var ux1:Vector.<Number> = new Vector.<Number>();
        private var ux2:Vector.<Number> = new Vector.<Number>();
        private var uy1:Vector.<Number> = new Vector.<Number>();
        private var uy2:Vector.<Number> = new Vector.<Number>();

        private var gridCountX:int = 0;
        private var gridCountY:int = 0;
        private var gridUnitCount:int = -1;
        private var buckets:Array = [];

        public function BulletGridBench()
        {
            log("== BULLET-GRID-BENCH v1 ==");
            log("cell=" + CELL + " margin=" + MARGIN + " map=" + MAP_W + "x" + MAP_H +
                " units=" + UNITS + " bullets=" + BULLETS + " frames=" + FRAMES);
            try
            {
                sceneStatic();
                testStaticEquivalence();
                testMovementEquivalence();
                testAdversarial();
                testMidFrameSpawn();
                cost();
            }
            catch (err:Error)
            {
                log("ERROR " + err.message + "\n" + err.getStackTrace());
                failures++;
            }
            log(failures == 0 ? "== equivalence OK ==" : "== equivalence FAILED (" + failures + ") ==");
            log("== done ==");
            writeResults();
            flash.utils.setTimeout(function():void
            {
                NativeApplication.nativeApplication.exit(0);
            }, 300);
        }

        private function log(s:String):void
        {
            lines.push(s);
            trace(s);
        }

        private function writeResults():void
        {
            var stream:FileStream = new FileStream();
            try
            {
                var target:File = File.applicationDirectory.resolvePath("bullet-grid-result.txt");
                stream.open(target, FileMode.WRITE);
                stream.writeUTFBytes(lines.join("\n") + "\n");
                stream.close();
            }
            catch (err:Error)
            {
                trace("write failed: " + err.message);
            }
        }

        private function rnd():Number
        {
            seed = uint(seed * 1664525 + 1013904223);
            return (seed >>> 8) / 16777216;
        }

        private function between(lo:Number, hi:Number):Number
        {
            return lo + (hi - lo) * rnd();
        }

        private function addUnit(x1:Number, x2:Number, y1:Number, y2:Number):void
        {
            ux1.push(x1);
            ux2.push(x2);
            uy1.push(y1);
            uy2.push(y2);
        }

        /** 100 units clustered around a "player" plus 30 scattered: the shape a
         *  fight actually has, which is what a bullet pays for. */
        private function sceneStatic():void
        {
            ux1.length = 0;
            ux2.length = 0;
            uy1.length = 0;
            uy2.length = 0;
            var px:Number = 4200;
            var py:Number = 2600;
            var i:int = 0;
            while (i < 100)
            {
                var cx:Number = px + between(-1000, 1000);
                var cy:Number = py + between(-600, 600);
                var hw:Number = between(8, 40);
                var hh:Number = between(8, 60);
                addUnit(cx - hw, cx + hw, cy - hh, cy + hh);
                i++;
            }
            while (i < UNITS)
            {
                var sx:Number = between(0, MAP_W);
                var sy:Number = between(0, MAP_H);
                var sw:Number = between(10, 300);
                var sh:Number = between(10, 300);
                addUnit(sx - sw, sx + sw, sy - sh, sy + sh);
                i++;
            }
        }

        private function nativeFirstHit(px:Number, py:Number):int
        {
            var i:int = 0;
            while (i < count)
            {
                if (px >= ux1[i] && px <= ux2[i] && py >= uy1[i] && py <= uy2[i])
                {
                    return i;
                }
                i++;
            }
            return -1;
        }

        private function gridSize():void
        {
            gridCountX = int(Math.ceil(MAP_W / CELL));
            gridCountY = int(Math.ceil(MAP_H / CELL));
            var total:int = gridCountX * gridCountY;
            var slot:int = 0;
            while (slot < buckets.length)
            {
                if (buckets[slot] != null)
                {
                    buckets[slot].length = 0;
                }
                slot++;
            }
            while (buckets.length < total)
            {
                buckets.push(null);
            }
        }

        /** Build the table the same way the host patch does: every unit goes into
         *  every cell its AABB (padded by MARGIN) overlaps, preserving order. */
        private function buildGrid():void
        {
            gridSize();
            var i:int = 0;
            while (i < count)
            {
                var gx0:int = int((ux1[i] - MARGIN) / CELL);
                if (gx0 < 0)
                {
                    gx0 = 0;
                }
                var gx1:int = int((ux2[i] + MARGIN) / CELL);
                if (gx1 >= gridCountX)
                {
                    gx1 = gridCountX - 1;
                }
                var gy0:int = int((uy1[i] - MARGIN) / CELL);
                if (gy0 < 0)
                {
                    gy0 = 0;
                }
                var gy1:int = int((uy2[i] + MARGIN) / CELL);
                if (gy1 >= gridCountY)
                {
                    gy1 = gridCountY - 1;
                }
                var gy:int = gy0;
                while (gy <= gy1)
                {
                    var row:int = gy * gridCountX;
                    var gx:int = gx0;
                    while (gx <= gx1)
                    {
                        var index:int = row + gx;
                        var bucket:Array = buckets[index];
                        if (bucket == null)
                        {
                            bucket = [];
                            buckets[index] = bucket;
                        }
                        bucket.push(i);
                        gx++;
                    }
                    gy++;
                }
                i++;
            }
            gridUnitCount = count;
        }

        private function gridFirstHit(px:Number, py:Number):int
        {
            // Host guard: a unit list that changed since the build (a spawn, a
            // death, a room swap) makes the table unreliable for this frame, so
            // the bullet falls back to the native full scan.
            if (gridUnitCount != count)
            {
                return nativeFirstHit(px, py);
            }
            return gridFirstHitUnguarded(px, py);
        }

        private function gridFirstHitUnguarded(px:Number, py:Number):int
        {
            var gx:int = int(px / CELL);
            var gy:int = int(py / CELL);
            if (gx < 0 || gx >= gridCountX || gy < 0 || gy >= gridCountY)
            {
                return nativeFirstHit(px, py);
            }
            var bucket:Array = buckets[gy * gridCountX + gx];
            if (bucket == null)
            {
                return -1;
            }
            var n:int = bucket.length;
            var k:int = 0;
            while (k < n)
            {
                var i:int = bucket[k];
                if (px >= ux1[i] && px <= ux2[i] && py >= uy1[i] && py <= uy2[i])
                {
                    return i;
                }
                k++;
            }
            return -1;
        }

        private function compareHits(label:String, points:int):void
        {
            var checked:int = 0;
            var hits:int = 0;
            var mismatch:int = 0;
            var shown:int = 0;
            var p:int = 0;
            while (p < points)
            {
                var px:Number = between(-200, MAP_W + 200);
                var py:Number = between(-200, MAP_H + 200);
                var a:int = nativeFirstHit(px, py);
                var b:int = gridFirstHit(px, py);
                if (a != b)
                {
                    mismatch++;
                    if (shown < 5)
                    {
                        log("  mismatch " + label + " p=" + px.toFixed(1) + "," + py.toFixed(1) +
                            " native=" + a + " grid=" + b);
                        shown++;
                    }
                }
                if (a >= 0)
                {
                    hits++;
                }
                checked++;
                p++;
            }
            if (mismatch != 0)
            {
                failures++;
            }
            log("  " + label + ": points=" + checked + " hits=" + hits + " mismatches=" + mismatch);
        }

        private function testStaticEquivalence():void
        {
            log("[1] static equivalence (grid built on the same positions)");
            sceneStatic();
            buildGrid();
            compareHits("static", 6000);
        }

        private function testMovementEquivalence():void
        {
            log("[2] one-frame staleness: units move up to +-MARGIN after the build");
            sceneStatic();
            buildGrid();
            var moved:Vector.<Number> = new Vector.<Number>();
            var i:int = 0;
            while (i < count)
            {
                var dx:Number = between(-MARGIN, MARGIN);
                var dy:Number = between(-MARGIN, MARGIN);
                ux1[i] += dx;
                ux2[i] += dx;
                uy1[i] += dy;
                uy2[i] += dy;
                i++;
            }
            compareHits("moved", 6000);
        }

        private function testAdversarial():void
        {
            log("[3] adversarial geometry (cell boundaries, huge and degenerate boxes)");
            ux1.length = 0;
            ux2.length = 0;
            uy1.length = 0;
            uy2.length = 0;
            addUnit(CELL - 4, CELL + 4, CELL - 4, CELL + 4);
            addUnit(2 * CELL - 1, 2 * CELL + 1, 3 * CELL - 1, 3 * CELL + 1);
            addUnit(-500, 500, -500, 500);
            addUnit(MAP_W - 100, MAP_W + 5000, MAP_H - 100, MAP_H + 5000);
            addUnit(1000, 3000, 1000, 3000);
            addUnit(2000, 1990, 2000, 1990);
            addUnit(0, 60, 0, 60);
            count = ux1.length;
            buildGrid();
            compareHits("edges", 4000);
            var exact:int = 0;
            var mismatched:int = 0;
            var probes:Array = [
                [CELL, CELL], [2 * CELL, 3 * CELL], [0, 0], [MAP_W - 1, MAP_H - 1],
                [1000, 1000], [3000, 3000], [2000, 2000], [60, 60], [60.0001, 60.0001]
            ];
            var p:int = 0;
            while (p < probes.length)
            {
                var a:int = nativeFirstHit(probes[p][0], probes[p][1]);
                var b:int = gridFirstHit(probes[p][0], probes[p][1]);
                exact++;
                if (a != b)
                {
                    mismatched++;
                    log("  exact mismatch " + probes[p][0] + "," + probes[p][1] + " native=" + a + " grid=" + b);
                }
                p++;
            }
            if (mismatched != 0)
            {
                failures++;
            }
            log("  exact-corner probes=" + exact + " mismatches=" + mismatched);
            sceneStatic();
            count = UNITS;
        }

        /** [5] a unit that spawns after the build must still be hittable. The
         *  count guard falls back, and without it the new unit is invisible to
         *  the bullet for one frame -- both facts are asserted, so the guard is
         *  not decorative. */
        private function testMidFrameSpawn():void
        {
            log("[5] unit spawned after the build");
            sceneStatic();
            count = UNITS;
            buildGrid();
            addUnit(6000 - 20, 6000 + 20, 2900 - 20, 2900 + 20);
            count++;
            var probeX:Number = 6000;
            var probeY:Number = 2900;
            var want:int = nativeFirstHit(probeX, probeY);
            var guarded:int = gridFirstHit(probeX, probeY);
            var unguarded:int = gridFirstHitUnguarded(probeX, probeY);
            log("  native=" + want + " guarded=" + guarded + " unguarded=" + unguarded);
            if (guarded != want)
            {
                failures++;
                log("  guarded lookup diverged from native");
            }
            if (unguarded == want)
            {
                failures++;
                log("  unguarded lookup did not diverge; the count guard would be untested");
            }
            sceneStatic();
            count = UNITS;
            buildGrid();
        }

        /** Timing. getTimer() is 1 ms, so each arm is measured over many frames
         *  and divided. Bullets fly until they hit or leave their 8-unit sweep. */
        private function cost():void
        {
            log("[4] cost (ms per frame, " + FRAMES + " frames)");
            sceneStatic();
            count = UNITS;
            var bx:Vector.<Number> = new Vector.<Number>();
            var by:Vector.<Number> = new Vector.<Number>();
            var b:int = 0;
            while (b < BULLETS)
            {
                bx.push(between(3200, 5200));
                by.push(between(2000, 3200));
                b++;
            }
            var full:int = runFullScan(bx, by);
            var naive:int = runFullScanWithException(bx, by);
            var grid:int = runGrid(bx, by);
            var buildOnly:int = runBuildOnly();
            var full2:int = runFullScan(bx, by);
            var grid2:int = runGrid(bx, by);
            var exceptions:int = runExceptionOnly();
            log("  full scan                : " + (full + full2) / 2 + " ms / " + FRAMES + " frames");
            log("  full scan + #1069 throw  : " + naive + " ms / " + FRAMES + " frames");
            log("  bucket table (build+query): " + (grid + grid2) / 2 + " ms / " + FRAMES + " frames");
            log("  bucket build only        : " + buildOnly + " ms / " + FRAMES + " frames");
            log("  exception storm only     : " + exceptions + " ms / " + FRAMES + " frames");
        }

        private function runBuildOnly():int
        {
            var started:int = getTimer();
            var f:int = 0;
            while (f < FRAMES)
            {
                buildGrid();
                f++;
            }
            return getTimer() - started;
        }

        private function runFullScan(bx:Vector.<Number>, by:Vector.<Number>):int
        {
            var sink:int = 0;
            var start:int = getTimer();
            var f:int = 0;
            while (f < FRAMES)
            {
                var i:int = 0;
                while (i < BULLETS)
                {
                    sink += nativeFirstHit(bx[i] + between(-40, 40), by[i] + between(-40, 40));
                    i++;
                }
                f++;
            }
            var elapsed:int = getTimer() - start;
            if (sink == 12345)
            {
                trace(elapsed);
            }
            return elapsed;
        }

        /** The deployed host: every bullet first reads a dynamic property on the
         *  sealed MainFE, which throws, then falls back to the full scan. */
        private function runFullScanWithException(bx:Vector.<Number>, by:Vector.<Number>):int
        {
            var sink:int = 0;
            var started:int = getTimer();
            var f:int = 0;
            while (f < FRAMES)
            {
                var i:int = 0;
                while (i < BULLETS)
                {
                    try
                    {
                        var carrier:Object = sealedProbe();
                        if (carrier == null)
                        {
                            sink += -1;
                        }
                    }
                    catch (err:Error)
                    {
                    }
                    sink += nativeFirstHit(bx[i] + between(-40, 40), by[i] + between(-40, 40));
                    i++;
                }
                f++;
            }
            sink += getTimer() - started;
            return getTimer() - started;
        }

        /** Stand-in for `World.w.visual.root["sceneCU"]` on fe.MainFE: a sealed
         *  class, so the lookup throws the same #1069 family of error. */
        private function sealedProbe():Object
        {
            var sealed:SealedStandIn = new SealedStandIn();
            return sealed["sceneCU"];
        }

        private function runGrid(bx:Vector.<Number>, by:Vector.<Number>):int
        {
            var sink:int = 0;
            var started:int = getTimer();
            var f:int = 0;
            while (f < FRAMES)
            {
                buildGrid();
                var i:int = 0;
                while (i < BULLETS)
                {
                    sink += gridFirstHit(bx[i] + between(-40, 40), by[i] + between(-40, 40));
                    i++;
                }
                f++;
            }
            sink += getTimer() - started;
            return getTimer() - started;
        }

        private function runExceptionOnly():int
        {
            var sink:int = 0;
            var started:int = getTimer();
            var f:int = 0;
            while (f < FRAMES)
            {
                var i:int = 0;
                while (i < BULLETS)
                {
                    try
                    {
                        var value:Object = sealedProbe();
                        if (value == null)
                        {
                            sink += -1;
                        }
                    }
                    catch (err:Error)
                    {
                    }
                    i++;
                }
                f++;
            }
            sink += getTimer() - started;
            return getTimer() - started;
        }
    }
}
