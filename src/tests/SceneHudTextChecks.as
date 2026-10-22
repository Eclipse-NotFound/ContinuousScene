package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.text.AntiAliasType;
    import flash.text.GridFitType;
    import flash.text.StyleSheet;
    import flash.text.TextField;
    import flash.text.TextFieldAutoSize;
    import flash.text.TextFormat;

    /** Off-stage diagnostic only. Never calls GUI.setWeapon or changes its HUD.
     * Run AFTER all timing samples: synchronous bitmap draws are not frame-time
     * measurements. An unequal result is evidence, not an execution failure.
     */
    public class SceneHudTextChecks {
        private static const WIDTH:int=920;
        private static const HEIGHT:int=104;
        private static const BACKGROUND:uint=0xFF101010;
        private static const HTML:String="<span class = 'r'>Assault rifle (95%)</span> <span class = 'r2'>6/90 (470)</span>";

        public static function run(w:*,check:Function):Object {
            var app:String=NativeApplication.nativeApplication.applicationID;
            var prefix:String="pfe-modsettings-continuous-motion-";
            var isolated:Boolean=app.indexOf(prefix)==0 && app.length>prefix.length+7;
            check("hud-text-isolated-storage",isolated,app);
            if(!isolated)throw new Error("HUD text diagnostics require isolated motion storage");
            var source:StyleSheet=w && w.gui ? w.gui.style as StyleSheet : null;
            check("hud-text-native-style-readable",source!=null);
            if(!source)throw new Error("GUI.style is unavailable; do not substitute invented native styles");
            var before:Array=styleSnapshot(source);
            var result:Object={version:"hud-text-guard-diagnostic-1",diagnosticOnly:true,
                performanceEligible:false,valid:true,applicationID:app,html:HTML,cases:[],
                styleSource:"read-only GUI.style copied into owned StyleSheets",
                sourceStyles:before,canvas:{width:WIDTH,height:HEIGHT,background:BACKGROUND},
                guard:"styleSheet == null || htmlText !== desired: assign; otherwise skip",
                limitation:"Same synchronous frame, owned off-stage fields, identical device-font format. "
                    +"Does not prove native HUD asset/font/layout equality or performance improvement. "
                    +"equal is observational; valid means execution and owned-resource cleanup succeeded."};
            var names:Array=["same-value","setstyle-color","setstyle-size","parse-css","clear-css",
                "replace-stylesheet","external-html","without-stylesheet","remove-stylesheet","attach-style-late"];
            try {
                for each(var name:String in names) {
                    var row:Object=runCase(source,name);
                    result.cases.push(row);
                    if(!row.valid)result.valid=false;
                    check("hud-text-"+name+"-executed",row.valid,row);
                }
            } finally {
                result.sourceStyleUnchanged=w.gui.style===source
                    && JSON.stringify(before)===JSON.stringify(styleSnapshot(source));
                if(!result.sourceStyleUnchanged)result.valid=false;
                check("hud-text-native-style-untouched",result.sourceStyleUnchanged);
            }
            return result;
        }

        private static function runCase(source:StyleSheet,name:String):Object {
            var row:Object={name:name,valid:false,equal:false,changeEvents:0,nativeWrites:0,guardWrites:0,
                ownedBitmaps:0,disposedBitmaps:0,cleanupErrors:[],guardDecisions:[]};
            var bitmaps:Array=[],styles:Array=[];
            var a:TextField=null,b:TextField=null,sa:Sprite=null,sb:Sprite=null;
            var onChange:Function=function(event:Event):void {++row.changeEvents;};
            try {
                var sheet:StyleSheet=copyStyle(source);styles.push(sheet);
                sheet.addEventListener(Event.CHANGE,onChange);
                var noInitialStyle:Boolean=name=="without-stylesheet" || name=="attach-style-late";
                a=makeField(noInitialStyle?null:sheet);b=makeField(noInitialStyle?null:sheet);
                sa=new Sprite();sb=new Sprite();sa.addChild(a);sb.addChild(b);
                a.htmlText=HTML;b.htmlText=HTML;
                row.initial={native:fieldState(a),guard:fieldState(b),
                    nativeExactInput:a.htmlText===HTML,guardExactInput:b.htmlText===HTML};
                var initialA:BitmapData=capture(sa,bitmaps),initialB:BitmapData=capture(sb,bitmaps);
                row.initialPixels=compare(initialA,initialB);
                row.initialNonBackground={native:ink(initialA),guard:ink(initialB)};
                if(!row.initialPixels.equal || row.initialNonBackground.native==0 || row.initialNonBackground.guard==0)
                    throw new Error("Initial text fixtures must render visible identical glyphs");

                if(name=="setstyle-color") {
                    changeStyle(sheet,".r","color","#FF236A");
                    changeStyle(sheet,".r2","color","#00FFFF");
                } else if(name=="setstyle-size") {
                    changeStyle(sheet,".r","fontSize",31);
                    changeStyle(sheet,".r2","fontSize",19);
                } else if(name=="parse-css") {
                    sheet.parseCSS(".r { color: #BB99FF; font-size: 29px; } .r2 { color: #FF9900; font-size: 18px; }");
                } else if(name=="clear-css") {
                    sheet.clear();
                } else if(name=="replace-stylesheet") {
                    var replacement:StyleSheet=copyStyle(source);styles.push(replacement);
                    replacement.addEventListener(Event.CHANGE,onChange);
                    changeStyle(replacement,".r","color","#FC7FED");
                    changeStyle(replacement,".r2","fontSize",30);
                    a.styleSheet=replacement;b.styleSheet=replacement;
                } else if(name=="external-html") {
                    a.htmlText="<span class='r5'>EXTERNAL HUD WRITE</span>";
                    b.htmlText="<span class='r5'>EXTERNAL HUD WRITE</span>";
                } else if(name=="remove-stylesheet") {
                    a.styleSheet=null;b.styleSheet=null;
                } else if(name=="attach-style-late") {
                    a.styleSheet=sheet;b.styleSheet=sheet;
                }

                // Capture before either input is reassigned. This distinguishes
                // a style change that already redraws attached fields from one
                // which only becomes visible after the native htmlText setter.
                var mutatedA:BitmapData=capture(sa,bitmaps),mutatedB:BitmapData=capture(sb,bitmaps);
                row.beforeReassignment={native:fieldState(a),guard:fieldState(b),
                    pixels:compare(mutatedA,mutatedB),
                    nativeChangeFromInitial:compare(initialA,mutatedA),
                    guardChangeFromInitial:compare(initialB,mutatedB)};
                var repeats:int=name=="same-value"?4:1;
                for(var iteration:int=0;iteration<repeats;++iteration) {
                    a.htmlText=HTML;++row.nativeWrites;
                    var hasStyle:Boolean=b.styleSheet!=null,htmlEqual:Boolean=b.htmlText===HTML;
                    var write:Boolean=!hasStyle || !htmlEqual;
                    if(write){b.htmlText=HTML;++row.guardWrites;}
                    row.guardDecisions.push({iteration:iteration,hasStyle:hasStyle,
                        htmlEqual:htmlEqual,wrote:write});
                }
                var finalA:BitmapData=capture(sa,bitmaps),finalB:BitmapData=capture(sb,bitmaps);
                row.pixels=compare(finalA,finalB);row.equal=row.pixels.equal;
                row.after={native:fieldState(a),guard:fieldState(b),
                    nativeExactInput:a.htmlText===HTML,guardExactInput:b.htmlText===HTML,
                    nativeChangeFromInitial:compare(initialA,finalA),
                    guardChangeFromInitial:compare(initialB,finalB),
                    nativeReassignmentChange:compare(mutatedA,finalA),
                    guardReassignmentChange:compare(mutatedB,finalB)};
                row.sharedSheet=a.styleSheet===b.styleSheet;
                row.sheetIdentityChanged=a.styleSheet!==sheet;
                row.activeStyles=a.styleSheet ? styleSnapshot(a.styleSheet) : null;
                row.offStage=sa.stage==null && sb.stage==null && a.stage==null && b.stage==null;
                if(!row.offStage)throw new Error("Owned text fixtures unexpectedly attached to a Stage");
                row.valid=true;
            } catch(error:Error) {
                row.error={id:error.errorID,message:error.message,stack:error.getStackTrace()};
            } finally {
                row.ownedBitmaps=bitmaps.length;
                for each(var bitmap:BitmapData in bitmaps) {
                    try {bitmap.dispose();++row.disposedBitmaps;}
                    catch(disposeError:Error) {row.cleanupErrors.push(disposeError.message);}
                }
                for each(var ownedStyle:StyleSheet in styles) {
                    try {ownedStyle.removeEventListener(Event.CHANGE,onChange);}
                    catch(listenerError:Error) {row.cleanupErrors.push(listenerError.message);}
                }
                // Only owned fields and sprites are changed during cleanup.
                try {
                    if(a){a.styleSheet=null;if(a.parent)a.parent.removeChild(a);}
                    if(b){b.styleSheet=null;if(b.parent)b.parent.removeChild(b);}
                } catch(fieldError:Error) {row.cleanupErrors.push(fieldError.message);}
                row.cleaned=row.disposedBitmaps==row.ownedBitmaps && row.cleanupErrors.length==0;
                row.valid=row.valid && row.cleaned;
            }
            return row;
        }

        private static function makeField(sheet:StyleSheet):TextField {
            var field:TextField=new TextField();
            field.defaultTextFormat=new TextFormat("_sans",24,0xFFFFFF);
            field.x=8;field.y=8;field.width=WIDTH-16;field.height=HEIGHT-16;
            field.autoSize=TextFieldAutoSize.LEFT;field.multiline=false;field.wordWrap=false;
            field.selectable=false;field.embedFonts=false;
            field.antiAliasType=AntiAliasType.ADVANCED;field.gridFitType=GridFitType.PIXEL;
            field.styleSheet=sheet;return field;
        }
        private static function copyStyle(source:StyleSheet):StyleSheet {
            var copy:StyleSheet=new StyleSheet();
            for each(var name:String in source.styleNames)copy.setStyle(name,source.getStyle(name));
            return copy;
        }
        private static function changeStyle(sheet:StyleSheet,name:String,key:String,value:*):void {
            var data:Object=sheet.getStyle(name);
            if(!data)data={};
            data[key]=value;sheet.setStyle(name,data);
        }
        private static function styleSnapshot(sheet:StyleSheet):Array {
            var rows:Array=[],names:Array=sheet.styleNames.concat();names.sort();
            for each(var name:String in names) {
                var style:Object=sheet.getStyle(name),keys:Array=[],values:Array=[];
                for(var key:String in style)keys.push(key);
                keys.sort();
                for each(key in keys)values.push({key:key,type:typeof style[key],value:String(style[key])});
                rows.push({name:name,values:values});
            }
            return rows;
        }
        private static function fieldState(field:TextField):Object {
            return {html:field.htmlText,text:field.text,hasStyle:field.styleSheet!=null,
                x:field.x,y:field.y,width:field.width,height:field.height,
                textWidth:field.textWidth,textHeight:field.textHeight,length:field.length,
                autoSize:field.autoSize,embedFonts:field.embedFonts,
                antiAliasType:field.antiAliasType,gridFitType:field.gridFitType};
        }
        private static function capture(sprite:Sprite,owned:Array):BitmapData {
            var bitmap:BitmapData=new BitmapData(WIDTH,HEIGHT,true,BACKGROUND);
            owned.push(bitmap);bitmap.draw(sprite);return bitmap;
        }
        private static function ink(bitmap:BitmapData):int {
            var data:Vector.<uint> = bitmap.getVector(bitmap.rect),count:int=0;
            for each(var pixel:uint in data)if(pixel!=BACKGROUND)++count;
            return count;
        }
        private static function compare(a:BitmapData,b:BitmapData):Object {
            var av:Vector.<uint> = a.getVector(a.rect),bv:Vector.<uint> = b.getVector(b.rect);
            var changed:int=0,maximum:int=0,first:Object=null;
            for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i]) {
                ++changed;if(!first)first={x:i%WIDTH,y:int(i/WIDTH),nativePixel:av[i],guardPixel:bv[i]};
                for(var shift:int=0;shift<32;shift+=8)
                    maximum=Math.max(maximum,Math.abs(int((av[i]>>>shift)&255)-int((bv[i]>>>shift)&255)));
            }
            return {equal:changed==0,comparedPixels:av.length,changedPixels:changed,maxChannel:maximum,first:first};
        }
    }
}
