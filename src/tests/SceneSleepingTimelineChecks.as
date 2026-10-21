package tests {
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;

    /** Read-only eight-frame observation, not a performance measurement.
     * The caller invokes sample once per successive world/display frame at the
     * same point in its frame callback. No activity(), stop/play, pose selection,
     * AI step, display-property write or unit-attached bookkeeping is used.
     * A change proves a sleeping visual advanced, not which engine/mod moved it.
     * No change in this short window does not prove every timeline stays frozen.
     */
    public class SceneSleepingTimelineChecks {
        private static const LIMIT:int=8;
        private var location:*;
        private var owners:Array=[];
        private var clips:Array=[];
        private var observations:int=0;
        private var begun:Boolean=false;
        private var failure:String=null;
        private var initialSleeping:int=0;
        private var missingRoots:int=0;
        private var duplicateRoots:int=0;

        public function begin(w:*):void {
            location=w ? w.loc : null;
            owners=[];clips=[];observations=0;failure=null;
            initialSleeping=missingRoots=duplicateRoots=0;begun=true;
            if(!location) {failure="No current location";return;}
            var sleeping:Object=readSleeping(w);
            if(!sleeping) {failure="Native sleeping dictionary unavailable";return;}
            var seen:Dictionary=new Dictionary(true);
            for each(var unit:* in location.units) {
                if(!unit || !sleeping[unit])continue;
                ++initialSleeping;
                var root:DisplayObjectContainer=unit.vis as DisplayObjectContainer;
                if(!root){++missingRoots;continue;}
                if(seen[root]){++duplicateRoots;continue;}
                seen[root]=true;
                var record:Object={unit:unit,root:root,valid:true,reason:null,
                    type:getQualifiedClassName(unit),index:owners.length,samples:0};
                owners.push(record);
                walk(root,record,"root");
            }
        }

        public function sample(w:*):Boolean {
            if(!begun) {failure="begin was not called";return true;}
            if(observations>=LIMIT || failure!=null)return true;
            ++observations;
            var sleeping:Object=readSleeping(w);
            for each(var owner:Object in owners) {
                if(!owner.valid)continue;
                if(!w || w.loc!==location || owner.unit.loc!==location)
                    excludeOwner(owner,"location-changed");
                else if(!sleeping)excludeOwner(owner,"sleeping-dictionary-unavailable");
                else if(!sleeping[owner.unit])excludeOwner(owner,"owner-awake");
                else if(owner.unit.vis!==owner.root)excludeOwner(owner,"root-replaced");
                else ++owner.samples;
            }
            for each(var item:Object in clips) {
                if(!item.valid)continue;
                if(!item.owner.valid) {item.valid=false;item.reason=item.owner.reason;continue;}
                var mc:MovieClip=item.clip;
                var root:DisplayObjectContainer=item.owner.root;
                if(mc!==root && !root.contains(mc)) {
                    item.valid=false;item.reason="clip-left-root";continue;
                }
                var frame:int=mc.currentFrame;
                var label:String=mc.currentLabel;
                var playing:Boolean=mc.isPlaying;
                var frameChanged:Boolean=frame!=item.frame;
                var labelChanged:Boolean=label!=item.label;
                if(frameChanged || labelChanged) {
                    item.changes.push({sample:observations,fromFrame:item.frame,toFrame:frame,
                        fromLabel:item.label,toLabel:label,beforePlaying:item.playing,playing:playing});
                }
                if(frameChanged) {
                    ++item.frameChanges;
                    if(!labelChanged)++item.sameLabelFrameChanges;
                    if(!item.playing && !playing) {
                        ++item.falsePlayingFrameChanges;
                        if(!labelChanged)++item.falsePlayingSameLabelChanges;
                    }
                }
                if(labelChanged)++item.labelChanges;
                if(playing)item.anyPlaying=true;
                item.frame=frame;item.label=label;item.playing=playing;++item.samples;
            }
            return observations>=LIMIT;
        }

        public function report():Object {
            var result:Object={version:"sleeping-timelines-1",readOnly:true,
                diagnosticOnly:true,performanceEligible:false,
                complete:begun && failure==null && observations==LIMIT,
                requestedFrames:LIMIT,observations:observations,error:failure,
                initialSleepingOwners:initialSleeping,ownersWithRoots:owners.length,
                ownersWithoutRoots:missingRoots,duplicateRoots:duplicateRoots,
                initialMultiFrameClips:clips.length,stableSleepingOwners:0,
                stableMultiFrameClips:0,changedClips:0,frameChanges:0,labelChanges:0,
                falsePlayingChangedClips:0,falsePlayingSameLabelChangedClips:0,
                ownerClasses:{},clipClasses:{},excludedOwners:{},excludedClips:{},examples:[],
                limitations:[
                    "sample must be called once per successive frame at a consistent phase.",
                    "Only clips already present at begin are observed; replacement clips are excluded.",
                    "Stable sleeping is verified at sample boundaries, not during the interval.",
                    "Frame movement may originate in authored timelines, frame scripts or another mod.",
                    "Eight unchanged frames do not exclude slower, delayed or aliased animation."
                ]};
            for each(var owner:Object in owners) {
                var oc:Object=result.ownerClasses[owner.type];
                if(!oc)result.ownerClasses[owner.type]=oc={initial:0,stable:0,excluded:0};
                ++oc.initial;
                if(owner.valid && owner.samples==observations) {++oc.stable;++result.stableSleepingOwners;}
                else {++oc.excluded;addReason(result.excludedOwners,owner.reason);}
            }
            var changed:Array=[],unchanged:Array=[];
            for each(var item:Object in clips) {
                var cc:Object=result.clipClasses[item.type];
                if(!cc)result.clipClasses[item.type]=cc={initial:0,stable:0,excluded:0,
                    changed:0,frameChanges:0,labelChanges:0,falsePlayingChanged:0,
                    falsePlayingSameLabelChanged:0,initialPlaying:0};
                ++cc.initial;
                if(item.initialPlaying)++cc.initialPlaying;
                if(!item.valid || !item.owner.valid || item.samples!=observations) {
                    ++cc.excluded;addReason(result.excludedClips,item.reason || item.owner.reason);continue;
                }
                ++cc.stable;++result.stableMultiFrameClips;
                cc.frameChanges+=item.frameChanges;result.frameChanges+=item.frameChanges;
                cc.labelChanges+=item.labelChanges;result.labelChanges+=item.labelChanges;
                if(item.frameChanges>0) {++cc.changed;++result.changedClips;}
                if(item.falsePlayingFrameChanges>0) {++cc.falsePlayingChanged;++result.falsePlayingChangedClips;}
                if(item.falsePlayingSameLabelChanges>0) {++cc.falsePlayingSameLabelChanged;++result.falsePlayingSameLabelChangedClips;}
                if(item.frameChanges>0 || item.labelChanges>0)changed.push(item);else unchanged.push(item);
            }
            // Prefer evidence hidden by isPlaying, then other movement, then
            // unchanged coverage. Never serialize unit/display references.
            for each(item in changed)
                if(item.falsePlayingSameLabelChanges>0)appendExample(result.examples,item);
            for each(item in changed)
                if(item.falsePlayingSameLabelChanges==0)appendExample(result.examples,item);
            for each(item in unchanged)appendExample(result.examples,item);
            result.coverage=result.complete && result.stableMultiFrameClips>0;
            result.observedSleepingFrameAdvance=result.coverage && result.changedClips>0;
            result.observedFalsePlayingAdvance=result.coverage && result.falsePlayingChangedClips>0;
            return result;
        }

        /** References stay inside the isolated probe, never in JSON reports.
         * The consumer must revalidate sleeping/location/root before any action.
         */
        public function observedCandidates():Array {
            var result:Array=[];
            if(!begun || failure!=null || observations!=LIMIT)return result;
            for each(var item:Object in clips) {
                if(item.valid && item.owner.valid && item.samples==LIMIT
                   && item.owner.samples==LIMIT && item.falsePlayingSameLabelChanges>0)
                    result.push({unit:item.owner.unit,root:item.owner.root,clip:item.clip});
            }
            return result;
        }

        private function readSleeping(w:*):Object {
            if(!w || !w.main || !location)return null;
            var carrier:*=w.main.getChildByName("ContinuousSceneCarrier");
            var api:*=carrier ? carrier["nativeAPI"] : null;
            return api && api.sleeping is Function ? api.sleeping(location) : null;
        }

        private function walk(parent:DisplayObjectContainer,owner:Object,path:String):void {
            var mc:MovieClip=parent as MovieClip;
            if(mc && mc.totalFrames>1) {
                clips.push({owner:owner,clip:mc,path:path,type:getQualifiedClassName(mc),
                    totalFrames:mc.totalFrames,initialFrame:mc.currentFrame,frame:mc.currentFrame,
                    initialLabel:mc.currentLabel,label:mc.currentLabel,
                    initialPlaying:mc.isPlaying,playing:mc.isPlaying,anyPlaying:mc.isPlaying,
                    valid:true,reason:null,samples:0,frameChanges:0,labelChanges:0,
                    sameLabelFrameChanges:0,falsePlayingFrameChanges:0,
                    falsePlayingSameLabelChanges:0,changes:[]});
            }
            for(var i:int=0;i<parent.numChildren;++i) {
                var child:DisplayObjectContainer=parent.getChildAt(i) as DisplayObjectContainer;
                if(child)walk(child,owner,path+"/"+i+":"+child.name);
            }
        }

        private function excludeOwner(owner:Object,reason:String):void {
            owner.valid=false;owner.reason=reason;
        }

        private function addReason(reasons:Object,reason:String):void {
            if(!reason)reason="incomplete-observation";
            reasons[reason]=int(reasons[reason])+1;
        }

        private function appendExample(examples:Array,item:Object):void {
            if(examples.length>=20)return;
            examples.push({ownerIndex:item.owner.index,ownerClass:item.owner.type,
                clipClass:item.type,path:item.path,totalFrames:item.totalFrames,
                initialFrame:item.initialFrame,lastFrame:item.frame,
                initialLabel:item.initialLabel,lastLabel:item.label,
                initialPlaying:item.initialPlaying,lastPlaying:item.playing,anyPlaying:item.anyPlaying,
                observations:item.samples,frameChanges:item.frameChanges,labelChanges:item.labelChanges,
                falsePlayingFrameChanges:item.falsePlayingFrameChanges,
                falsePlayingSameLabelChanges:item.falsePlayingSameLabelChanges,changes:item.changes.concat()});
        }
    }
}
