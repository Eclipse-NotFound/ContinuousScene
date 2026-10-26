        private function mergeFallbackCheck():void {
            var parent:*=grafon.visBack,oldAlpha:Number=parent.alpha;
            var item:Object={startedAtMs:getTimer(),passed:false};report.mergeFallback=item;
            try {
                presenter.beginFrame();applyCamera(views[0].x,views[0].y);
                parent.alpha=.7;
                var nativeAltered:BitmapData=capture();presenter.update(world,true,true);item.during=presenter.snapshot();
                var fallbackImage:BitmapData=capture();item.native=compare(nativeAltered,fallbackImage);
                require(!presenter.presented && item.during.fallbackReason=="background-order-or-effects" && item.native.equal,"Background alpha must fall back to exact native rendering");
                presenter.beginFrame();parent.alpha=oldAlpha;
                var nativeRestored:BitmapData=capture();presenter.update(world,true,true);item.resumed=presenter.snapshot();
                var merged:BitmapData=capture();item.merged=compare(nativeRestored,merged);
                require(presenter.presented && item.merged.maxAlpha==0 && item.merged.maxRGB<=2,"Merge did not resume correctly after native fallback");
                presenter.beginFrame();var restored:BitmapData=capture();item.restore=compare(nativeRestored,restored);
                require(item.restore.equal,"Merge fallback restoration differs from native");
                item.passed=true;
            } finally {presenter.beginFrame();parent.alpha=oldAlpha;disposeOwned();item.endedAtMs=getTimer();}
        }
