package tests {
    import flash.display.Bitmap;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Terminal, read-only structural census; not a presenter or performance test.
     * excludedViewport is the UNPADDED union of the tested camera viewports,
     * expressed in w.visual local/world coordinates. This reader adds 320px.
     * No native methods, timeline controls or display-property writes are used.
     */
    public class SceneStaticBoxCensus {
        public static const VERSION:String = "static-box-census-2";
        private static const ARRAY_LIMIT:int = 10000;
        private static const CHAIN_LIMIT:int = 10000;
        private static const TOTAL_NODE_LIMIT:int = 30000;
        private static const ROOT_NODE_LIMIT:int = 2048;
        private static const DEPTH_LIMIT:int = 64;
        private static const EXAMPLE_LIMIT:int = 48;
        private static const EXAMPLES_PER_REASON:int = 3;

        public static function read(w:Object, excludedViewport:Rectangle):Object {
            var start:int = getTimer();
            var out:Object = {version:VERSION,readOnly:true,diagnosticOnly:true,
                performanceEligible:false,detachEligible:false,structuralOnly:true,
                complete:false,truncated:false,elapsedMs:0,eligibleStructural:0,
                funnel:{arrayEntries:0,exactBox:0,wallFixed:0,noDoor:0,noInteraction:0,
                    ordinaryCurrentState:0,directNativeBody:0,uniqueBoxBody:0,
                    singleFrameBody:0,outsideSweep:0},
                exclusions:{},unknownFields:{},fieldTypes:{},fieldReadErrors:{},fieldValueExamples:{},
                referenceDeclarations:{osnova:"fe.loc::Box|null",scrDie:"fe.serv::Script|null",
                    un:"fe.unit::VirtualUnit|null",inter:"fe.serv::Interact|null"},
                examples:[],examplesOmitted:0,
                membership:{arrayOnly:0,both:0,chainOnly:0,arrayUniqueBoxes:0,chainUniqueBoxes:0,
                    arrayDuplicateEntries:0,arrayNullEntries:0,arrayOtherEntries:0,chainObjects:0,
                    arrayInChain:{yes:0,no:0,unknown:0},chainInChain:{yes:0,no:0,unknown:0},
                    chainOnlyExamples:[]},
                treeNodesRead:0,eligibleTreeNodes:0,deadBoxes:0,deadBoxesWithVisual:0,
                multiFrameExcludedBoxes:0,multiFrameExamples:[],multiFrameExamplesOmitted:0,
                errors:[],limits:{array:ARRAY_LIMIT,chain:CHAIN_LIMIT,totalTreeNodes:TOTAL_NODE_LIMIT,
                    perRootNodes:ROOT_NODE_LIMIT,depth:DEPTH_LIMIT,examples:EXAMPLE_LIMIT,multiFrameExamples:12},
                limitations:[
                    "One terminal snapshot cannot prove continuous immobility or future safety.",
                    "Single-frame topology does not prove absence of frame scripts, event handlers or external mutations.",
                    "Multi-frame counts cover only Box bodies reaching tree inspection after earlier eligibility filters; each example is the first rejecting timeline in that body.",
                    "Only exact native Box bodies are considered; shadows stay native and are never walked or detached.",
                    "loc.objs is the eligibility identity source; firstObj is independently cross-counted. in_chain=false is not an exclusion.",
                    "Reference documentation and Location.createObj differ on Box chain membership; actual arrayOnly/both/chainOnly observations are retained.",
                    "Body uniqueness is checked among exact Box objects in loc.objs, not arbitrary external owners.",
                    "Excluded viewport must cover the entire tested route; this reader cannot establish route coverage.",
                    "Counts do not measure render cost, guarantee interaction equivalence or qualify a detach candidate."
                ]};
            var reasonsShown:Object = {};
            try {
                if(!w || !excludedViewport || !finiteRect(excludedViewport)
                    || excludedViewport.width <= 0 || excludedViewport.height <= 0)
                    throw new Error("Missing world or invalid unpadded viewport union");
                var loc:* = field(w,"loc"), grafon:* = field(w,"grafon");
                var reference:DisplayObjectContainer = field(w,"visual") as DisplayObjectContainer;
                var layers:* = field(grafon,"visObjs");
                if(!loc || !reference || !reference.stage || !(layers is Array) || layers.length < 2)
                    throw new Error("Missing native location, visual or layer array");
                var layer0:DisplayObjectContainer = layers[0] as DisplayObjectContainer;
                var layer1:DisplayObjectContainer = layers[1] as DisplayObjectContainer;
                if(!layer0 || !layer1 || layer0 === layer1)
                    throw new Error("Invalid distinct native object layers 0 and 1");
                var layerInfo:Array = [ancestry(layer0,reference),ancestry(layer1,reference)];
                out.layerState = layerInfo;
                var expanded:Rectangle = new Rectangle(excludedViewport.x-320,excludedViewport.y-320,
                    excludedViewport.width+640,excludedViewport.height+640);
                if(!finiteRect(expanded)) throw new Error("Expanded viewport overflow");
                out.viewport = rectangle(excludedViewport);out.margin = 320;
                out.excludedViewport = rectangle(expanded);
                var objectArray:* = field(loc,"objs");
                if(!(objectArray is Array))throw new Error("Unknown native objs container type");
                var initialLength:Number=Number(objectArray.length);
                var arraySnapshot:Array=[];
                var arrayBoxes:Dictionary=new Dictionary();
                var arrayOccurrences:Dictionary=new Dictionary();
                var claims:Dictionary = new Dictionary();
                var boxes:Array = [];
                var item:Object;
                for(var arrayIndex:int=0;arrayIndex<initialLength && arrayIndex<ARRAY_LIMIT;arrayIndex++) {
                    var owner:*=objectArray[arrayIndex];arraySnapshot.push(owner);bump(out.funnel,"arrayEntries");
                    if(owner===null || owner===undefined){bump(out.membership,"arrayNullEntries");continue;}
                    if(typeof owner!="object" || getQualifiedClassName(owner)!="fe.loc::Box") {
                        bump(out.membership,"arrayOtherEntries");continue;
                    }
                    arrayOccurrences[owner]=int(arrayOccurrences[owner])+1;
                    if(arrayBoxes[owner]){bump(out.membership,"arrayDuplicateEntries");continue;}
                    arrayBoxes[owner]=true;bump(out.funnel,"exactBox");bump(out.membership,"arrayUniqueBoxes");
                    observeFields(owner,out);
                    item={owner:owner,index:arrayIndex,body:null,bodyError:null,inChain:inChainValue(owner)};
                    countInChain(out.membership.arrayInChain,item.inChain);
                    try {
                        item.body=field(owner,"vis");
                        if(item.body is DisplayObject)claims[item.body]=int(claims[item.body])+1;
                        if(booleanField(owner,"dead")) {
                            bump(out,"deadBoxes");
                            if(item.body is DisplayObject)bump(out,"deadBoxesWithVisual");
                        }
                    } catch(ownerError:Error) {item.bodyError=ownerError.message;}
                    boxes.push(item);
                }
                out.arrayEnded=initialLength<=ARRAY_LIMIT;out.arrayLength=initialLength;
                if(!out.arrayEnded){out.truncated=true;out.errors.push("Native object array limit");}
                var first:* = field(loc,"firstObj"), node:* = first;
                var seen:Dictionary = new Dictionary(),chainBoxes:Dictionary=new Dictionary();
                var chainSnapshot:Array=[];
                while(node !== null) {
                    if(out.membership.chainObjects >= CHAIN_LIMIT) {
                        out.truncated=true;out.errors.push("Logical chain limit");break;
                    }
                    if(typeof node != "object" || seen[node]) {
                        out.errors.push("Invalid or cyclic logical chain");break;
                    }
                    seen[node]=true;bump(out.membership,"chainObjects");
                    var next:* = field(node,"nobj");
                    chainSnapshot.push({owner:node,next:next});
                    if(getQualifiedClassName(node) == "fe.loc::Box") {
                        chainBoxes[node]=true;bump(out.membership,"chainUniqueBoxes");
                        var flag:*=inChainValue(node);countInChain(out.membership.chainInChain,flag);
                        if(!arrayBoxes[node]) {
                            bump(out.membership,"chainOnly");
                            if(out.membership.chainOnlyExamples.length<8)
                                out.membership.chainOnlyExamples.push({chainIndex:int(out.membership.chainObjects)-1,
                                    id:safeId(node),inChain:flag});
                        }
                    }
                    node=next;
                }
                out.chainEnded = node === null;
                var budget:Object = {nodes:0};
                for each(item in boxes) {
                    item.inObservedChain=Boolean(chainBoxes[item.owner]);
                    item.arrayOccurrences=int(arrayOccurrences[item.owner]);
                    bump(out.membership,item.inObservedChain?"both":"arrayOnly");
                    inspect(item,loc,reference,layers,layerInfo,expanded,claims,budget,out,reasonsShown);
                }
                out.treeNodesRead = budget.nodes;
                out.contextUnchanged = field(w,"loc") === loc && field(w,"grafon") === grafon
                    && field(w,"visual") === reference && field(grafon,"visObjs") === layers
                    && layers[0] === layer0 && layers[1] === layer1 && field(loc,"firstObj") === first
                    && field(loc,"objs")===objectArray && objectArray.length===initialLength;
                for(arrayIndex=0;arrayIndex<arraySnapshot.length;arrayIndex++)if(objectArray[arrayIndex]!==arraySnapshot[arrayIndex]) {
                    out.contextUnchanged=false;out.errors.push("Native object array changed during census");break;
                }
                for each(item in chainSnapshot)if(field(item.owner,"nobj") !== item.next) {
                    out.contextUnchanged=false;out.errors.push("Logical chain changed during census");break;
                }
                out.complete = out.arrayEnded && out.chainEnded && out.contextUnchanged && !out.truncated && out.errors.length == 0;
            } catch(error:Error) {out.errors.push(error.message);}
            out.elapsedMs = getTimer()-start;
            return out;
        }

        private static function inspect(item:Object,loc:*,reference:DisplayObjectContainer,layers:*,
            layerInfo:Array,excluded:Rectangle,claims:Dictionary,budget:Object,out:Object,shown:Object):void {
            var u:* = item.owner;
            var row:Object = {arrayIndex:item.index,ownerClass:"fe.loc::Box",id:null,reason:null,
                inChain:item.inChain,inObservedChain:item.inObservedChain,arrayOccurrences:item.arrayOccurrences};
            try {
                var id:* = field(u,"id");
                if(!(id is String))throw new Error("unknown-type:id");
                row.id=String(id).substr(0,100);
                if(item.arrayOccurrences!=1){exclude(out,shown,row,"duplicate-array-identity");return;}
                row.wall=numberField(u,"wall");
                if(row.wall <= 0){exclude(out,shown,row,"not-fixed-wall");return;}
                bump(out.funnel,"wallFixed");
                row.door=numberField(u,"door");
                if(row.door != 0){exclude(out,shown,row,"door");return;}
                bump(out.funnel,"noDoor");
                if(field(u,"inter") !== null) {
                    if(typeof field(u,"inter")!="object")throw new Error("unknown-reference-type:inter:"+getQualifiedClassName(field(u,"inter")));
                    exclude(out,shown,row,"interaction");return;
                }
                bump(out.funnel,"noInteraction");
                if(field(u,"loc") !== loc){exclude(out,shown,row,"wrong-location-owner");return;}
                row.dead=booleanField(u,"dead");row.invis=booleanField(u,"invis");
                row.hp=numberField(u,"hp");
                if(row.dead || row.invis || row.hp <= 0)
                    {exclude(out,shown,row,"dead-hidden-or-no-health");return;}
                for each(var nullable:String in ["scrDie","un","osnova"])
                    if(field(u,nullable) !== null) {
                        if(typeof field(u,nullable)!="object")throw new Error("unknown-reference-type:"+nullable+":"+getQualifiedClassName(field(u,nullable)));
                        exclude(out,shown,row,"special-reference:"+nullable);return;
                    }
                for each(var zero:String in ["lurk","molnDam","radioactiv","levit","t_throw","dx","dy","cdx","cdy"])
                    if(numberField(u,zero) != 0){exclude(out,shown,row,"special-or-moving:"+zero);return;}
                for each(var off:String in ["light","levitPoss","isThrow","isPlav","isPlav2","fixPlav"])
                    if(booleanField(u,off)){exclude(out,shown,row,"special-flag:"+off);return;}
                if(!booleanField(u,"stay")){exclude(out,shown,row,"not-staying");return;}
                row.position={x:numberField(u,"X"),y:numberField(u,"Y")};
                row.bodySize={width:numberField(u,"scX"),height:numberField(u,"scY")};
                if(row.bodySize.width <= 0 || row.bodySize.height <= 0)
                    {exclude(out,shown,row,"invalid-logic-size");return;}
                bump(out.funnel,"ordinaryCurrentState");
                if(item.bodyError !== null)throw new Error(String(item.bodyError));
                var body:DisplayObject = item.body as DisplayObject;
                row.layer=numberField(u,"sloy");
                row.bodyPresent=body!==null;row.rootClass=body?getQualifiedClassName(body):null;
                row.parentClass=body && body.parent?getQualifiedClassName(body.parent):null;
                row.parentName=body && body.parent?body.parent.name:null;
                row.parentNativeLayer=body && body.parent===layers[0]?0:body && body.parent===layers[1]?1:-1;
                if(!body || (row.layer != 0 && row.layer != 1) || body.parent !== layers[int(row.layer)])
                    {exclude(out,shown,row,"not-direct-native-body");return;}
                row.name=body.name;
                row.ownVisible=body.visible;row.alpha=safeNumber(body.alpha);row.cacheAsBitmap=body.cacheAsBitmap;
                if(!layerInfo[int(row.layer)].eligible)
                    {exclude(out,shown,row,"unsupported-layer-ancestry:"+layerInfo[int(row.layer)].reason);return;}
                if(!body.visible || !isFinite(body.alpha) || body.alpha <= 0)
                    {exclude(out,shown,row,"body-currently-hidden");return;}
                bump(out.funnel,"directNativeBody");
                if(int(claims[body]) != 1){exclude(out,shown,row,"body-shared-by-boxes");return;}
                bump(out.funnel,"uniqueBoxBody");
                var tree:Object={nodes:0,movieClips:0,shapes:0,bitmaps:0,sprites:0,playingFlags:0,
                    cachedNodes:0,maxDepth:0,reason:"",truncated:false};
                walk(body,0,tree,budget,new Dictionary());row.tree=tree;
                if(tree.truncated)out.truncated=true;
                if(tree.reason=="multi-frame-body") {
                    bump(out,"multiFrameExcludedBoxes");
                    if(out.multiFrameExamples.length<12)
                        out.multiFrameExamples.push({arrayIndex:row.arrayIndex,id:row.id,
                            rootClass:row.rootClass,timeline:tree.timelineFailure});
                    else bump(out,"multiFrameExamplesOmitted");
                }
                if(tree.reason != ""){exclude(out,shown,row,tree.reason);return;}
                bump(out.funnel,"singleFrameBody");
                var bounds:Rectangle = body.getBounds(reference);row.bounds=rectangle(bounds);
                if(!finiteRect(bounds) || bounds.width <= 0 || bounds.height <= 0)
                    {exclude(out,shown,row,"invalid-or-empty-display-bounds");return;}
                // Equality is deliberately inside: a touching edge retains native presentation.
                if(!(bounds.right < excluded.left || bounds.left > excluded.right
                    || bounds.bottom < excluded.top || bounds.top > excluded.bottom))
                    {exclude(out,shown,row,"inside-route-plus-margin");return;}
                bump(out.funnel,"outsideSweep");bump(out,"eligibleStructural");
                out.eligibleTreeNodes=int(out.eligibleTreeNodes)+int(tree.nodes);
                row.reason="eligible-structural-only";example(out,shown,row,12);
            } catch(error:Error) {
                if(error.message.indexOf("unknown-") == 0)bump(out.unknownFields,error.message);
                exclude(out,shown,row,error.message.indexOf("unknown-") == 0?error.message:"read-error:"+error.message);
            }
        }

        private static function walk(node:DisplayObject,depth:int,tree:Object,budget:Object,seen:Dictionary):void {
            if(tree.reason != "")return;
            if(!node || seen[node]){tree.reason="invalid-or-duplicate-display-node";return;}
            if(depth > DEPTH_LIMIT || tree.nodes >= ROOT_NODE_LIMIT || budget.nodes >= TOTAL_NODE_LIMIT) {
                tree.truncated=true;tree.reason="display-traversal-limit";return;
            }
            seen[node]=true;bump(tree,"nodes");bump(budget,"nodes");tree.maxDepth=Math.max(tree.maxDepth,depth);
            try {
                if(node.mask || node.filters.length || node.scrollRect || node.blendMode != "normal")
                    {tree.reason="special-display-state";return;}
                if(!isFinite(node.alpha) || !finiteMatrix(node.transform.matrix))
                    {tree.reason="invalid-display-transform";return;}
                if(node.cacheAsBitmap)bump(tree,"cachedNodes");
                var clip:MovieClip=node as MovieClip;
                if(clip) {
                    bump(tree,"movieClips");
                    if(clip.isPlaying)bump(tree,"playingFlags");
                    if(clip.totalFrames != 1 || clip.currentFrame != 1) {
                        tree.timelineFailure={nodeClass:getQualifiedClassName(clip),name:clip.name,
                            depth:depth,totalFrames:clip.totalFrames,currentFrame:clip.currentFrame,
                            isPlaying:clip.isPlaying};
                        tree.reason=clip.totalFrames>1?"multi-frame-body":"unknown-timeline-state";return;
                    }
                } else if(node is Bitmap) {
                    bump(tree,"bitmaps");
                    if(!Bitmap(node).bitmapData){tree.reason="missing-bitmap-data";return;}
                } else if(node is Shape)bump(tree,"shapes");
                else if(node is Sprite)bump(tree,"sprites");
                else {tree.reason="unsupported-display-type:"+getQualifiedClassName(node);return;}
                var container:DisplayObjectContainer=node as DisplayObjectContainer;
                if(container)for(var i:int=0;i<container.numChildren && tree.reason=="";i++)
                    walk(container.getChildAt(i),depth+1,tree,budget,seen);
            } catch(error:Error) {tree.reason="display-read-error:"+error.message;}
        }

        private static function ancestry(layer:DisplayObject,reference:DisplayObject):Object {
            var result:Object={eligible:false,reason:"",nodes:0,effectiveVisible:true,effectiveAlpha:1};
            var node:DisplayObject=layer,seen:Dictionary=new Dictionary();
            while(node && result.nodes <= DEPTH_LIMIT) {
                if(seen[node]){result.reason="cycle";return result;}
                seen[node]=true;bump(result,"nodes");
                if(node.mask || node.filters.length || node.scrollRect || node.blendMode!="normal")
                    {result.reason="special-display-state";return result;}
                if(!finiteMatrix(node.transform.matrix) || !isFinite(node.alpha))
                    {result.reason="invalid-transform";return result;}
                result.effectiveVisible=result.effectiveVisible && node.visible;
                var multiplied:Number=Number(result.effectiveAlpha)*node.alpha;
                if(!isFinite(multiplied)) {
                    result.effectiveAlpha=safeNumber(multiplied);result.reason="invalid-effective-alpha";return result;
                }
                result.effectiveAlpha=multiplied;
                if(node===reference) {
                    result.eligible=result.effectiveVisible && isFinite(result.effectiveAlpha) && result.effectiveAlpha>0;
                    result.reason=result.eligible?"":"hidden-ancestry";return result;
                }
                node=node.parent;
            }
            result.reason=node?"depth-limit":"does-not-reach-world-visual";return result;
        }

        private static function observeFields(u:*,out:Object):void {
            var names:Array=["wall","door","inter","scrDie","un","osnova","light","lurk",
                "radioactiv","molnDam","levit","levitPoss","isThrow","t_throw","isPlav",
                "isPlav2","fixPlav","stay","dx","dy","cdx","cdy","dead","invis","hp",
                "sloy","in_chain","X","Y","scX","scY"];
            for each(var name:String in names) {
                var types:Object=out.fieldTypes[name];
                if(!types)out.fieldTypes[name]=types={};
                var examples:Array=out.fieldValueExamples[name] as Array;
                if(!examples)out.fieldValueExamples[name]=examples=[];
                var kind:String,value:*;
                try {
                    value=field(u,name);kind=value===null?"null":getQualifiedClassName(value);
                    if(typeof value=="number")value=safeNumber(Number(value));
                    else if(value!==null && !(value is Boolean) && !(value is String))value="reference-not-expanded";
                    else if(value is String)value=String(value).substr(0,100);
                } catch(error:Error) {
                    kind="read-error";value=error.message;bump(out.fieldReadErrors,name+":"+error.message);
                }
                bump(types,kind);
                var exists:Boolean=false;
                for each(var old:Object in examples)if(old.type==kind && old.value===value){exists=true;break;}
                if(!exists && examples.length<4)examples.push({type:kind,value:value});
            }
        }
        private static function inChainValue(u:*):* {
            var result:*;
            try {
                var value:*=field(u,"in_chain");
                result=value is Boolean?value:"unknown-type:"+(value===null?"null":getQualifiedClassName(value));
            } catch(error:Error) {result="unknown:"+error.message;}
            return result;
        }
        private static function countInChain(counts:Object,value:*):void {
            bump(counts,value===true?"yes":value===false?"no":"unknown");
        }
        private static function safeId(u:*):String {
            var result:String;
            try {
                var value:*=field(u,"id");
                result=value is String?String(value).substr(0,100):"unknown-id-type";
            } catch(error:Error) {result="unknown:"+error.message;}
            return result;
        }
        private static function field(o:*,name:String):* {
            var key:QName=new QName("",name);
            if(o===null || o===undefined || !(key in o))throw new Error("unknown-field:"+name);
            var value:*=o[key];
            if(value===undefined)throw new Error("unknown-value:"+name);
            return value;
        }
        private static function numberField(o:*,name:String):Number {
            var value:*=field(o,name);
            if(typeof value!="number" || !isFinite(Number(value)))throw new Error("unknown-number:"+name);
            return Number(value);
        }
        private static function booleanField(o:*,name:String):Boolean {
            var value:*=field(o,name);
            if(!(value is Boolean))throw new Error("unknown-boolean:"+name);
            return Boolean(value);
        }
        private static function finiteRect(r:Rectangle):Boolean {
            return r && isFinite(r.x) && isFinite(r.y) && isFinite(r.width) && isFinite(r.height)
                && isFinite(r.right) && isFinite(r.bottom);
        }
        private static function finiteMatrix(m:Matrix):Boolean {
            return m && isFinite(m.a) && isFinite(m.b) && isFinite(m.c)
                && isFinite(m.d) && isFinite(m.tx) && isFinite(m.ty);
        }
        private static function rectangle(r:Rectangle):Object {
            return r?{x:safeNumber(r.x),y:safeNumber(r.y),width:safeNumber(r.width),height:safeNumber(r.height)}:null;
        }
        private static function safeNumber(n:Number):* {return isFinite(n)?n:"nonfinite:"+String(n);}
        private static function bump(o:Object,key:String):void {o[key]=int(o[key])+1;}
        private static function exclude(out:Object,shown:Object,row:Object,reason:String):void {
            row.reason=reason;bump(out.exclusions,reason);example(out,shown,row,EXAMPLES_PER_REASON);
        }
        private static function example(out:Object,shown:Object,row:Object,perReason:int):void {
            var key:String=String(row.reason);
            var eligible:Boolean=key=="eligible-structural-only";
            var rejectedStored:int=out.examples.length-int(shown["eligible-structural-only"]);
            if(out.examples.length<EXAMPLE_LIMIT && int(shown[key])<perReason
                && (eligible || rejectedStored<EXAMPLE_LIMIT-12)) {
                out.examples.push(row);bump(shown,key);
            } else bump(out,"examplesOmitted");
        }
    }
}
