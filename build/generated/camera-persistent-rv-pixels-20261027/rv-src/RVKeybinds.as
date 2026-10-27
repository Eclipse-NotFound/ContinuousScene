package
{
   import flash.events.KeyboardEvent;
   import flash.filesystem.File;
   import flash.filesystem.FileMode;
   import flash.filesystem.FileStream;
   import flash.text.TextField;
   import flash.utils.getDefinitionByName;
   import modlocales.vision.RVLocale;

   /** Owns only this client's bindings; the neutral menu owns capture and conflicts. */
   public class RVKeybinds
   {
      private var bindings:Object = {debug:{code:121,ctrl:false,alt:false,shift:false},
         toggle:{code:122,ctrl:false,alt:false,shift:false},mode:{code:123,ctrl:false,alt:false,shift:false}};
      private var api:*, registered:*, failed:Boolean = false;
      private static const PAGE:String = "realisticvision-hotkeys";

      public function RVKeybinds() { load(); }
      private function world():* {var w:* = null;try {w=getDefinitionByName("fe.World")["w"];}catch(e:*){}return w;}
      private function canonical(v:*):Object
      {
         var b:Object = null;
         try
         {
            var n:Number = Number(v.code);
            if(v != null && !(v.code is Boolean) && isFinite(n) && n==int(n) &&
               (n==0 || n>=8 && n<=222 && [16,17,18,91,92,93].indexOf(int(n))<0))
               b={code:int(n),ctrl:n!=0&&v.ctrl===true,alt:n!=0&&v.alt===true,shift:n!=0&&v.shift===true};
         }
         catch(e:*) {}
         return b;
      }
      private function file():File {return File.applicationStorageDirectory.resolvePath("RealisticVision.hotkeys.json");}
      private function load():void
      {
         var stream:FileStream = new FileStream();
         try
         {
            var f:File=file();if(!f.exists)return;
            stream.open(f,FileMode.READ);var data:Object=JSON.parse(stream.readUTFBytes(stream.bytesAvailable));stream.close();
            if(data.version!=1 || data.bindings==null)return;
            for(var id:String in bindings){var b:Object=canonical(data.bindings[id]);if(b!=null)bindings[id]=b;}
         }
         catch(e:*) {try{stream.close();}catch(ignored:*){}trace("[RVision] key configuration rejected: "+e);}
      }
      private function setBinding(id:String,v:*):void
      {
         var b:Object=canonical(v);if(b==null)throw new Error("Invalid key binding");
         var previous:Object=bindings[id],stream:FileStream=new FileStream();bindings[id]=b;
         try
         {
            var temp:File=File.applicationStorageDirectory.resolvePath("RealisticVision.hotkeys.tmp");
            stream.open(temp,FileMode.WRITE);stream.writeUTFBytes(JSON.stringify({version:1,bindings:bindings}));stream.close();temp.moveTo(file(),true);
         }
         catch(e:*){try{stream.close();}catch(ignored:*){}bindings[id]=previous;throw e;}
      }
      private function item(id:String,label:String,code:int):Object
      {
         var self:RVKeybinds=this;
         return {key:id,label:label,kind:"keybind",def:{code:code,ctrl:false,alt:false,shift:false},
            get:function():*{return self.bindings[id];},set:function(v:*):void{self.setBinding(id,v);}};
      }
      public function tick():void
      {
         try
         {
            var w:*=world();if(w==null || w.main==null)return;
            var carrier:*=w.main.getChildByName("ModSettingsCarrier");api=carrier==null?null:carrier["modAPI"];
            if(api==null || !("keybindVersion" in api) || api.keybindVersion<1 || registered===api)return;
            api.registerPage(PAGE,"视野系统 · 快捷键",[
               item("debug","调试显示",121),item("toggle","视野系统总开关",122),item("mode","切换渲染模式",123)
            ],null,"点击当前按键以修改；原有默认键保留。F10与联机浮窗共用时会提示冲突。",
               {moduleId:"realisticvision",moduleName:"视野系统",featureName:"快捷键",featureOrder:99,
                  translate:function(s:String):String{return RVLocale.render(s);}});
            registered=api;
         }
         catch(e:*) {if(!failed){failed=true;trace("[RVision] key menu registration failed: "+e);}}
      }
      public function matches(id:String,e:KeyboardEvent):Boolean
      {
         if(api!=null && "keybindVersion" in api && registered===api)return api.matchesKey(PAGE,id,e);
         var b:Object=bindings[id];return b!=null && b.code!=0 && b.code==e.keyCode && b.ctrl==e.ctrlKey && b.alt==e.altKey && b.shift==e.shiftKey;
      }
      public function label(id:String):String
      {
         var b:Object=bindings[id];if(api!=null&&"keyLabel" in api)return api.keyLabel(b);
         if(b.code==0)return RVLocale.text("未绑定");
         var name:String=b.code>=112&&b.code<=123?"F"+(b.code-111):b.code>=65&&b.code<=90?String.fromCharCode(b.code):"Key "+b.code;
         return (b.ctrl?"Ctrl+":"")+(b.alt?"Alt+":"")+(b.shift?"Shift+":"")+name;
      }
      public function hint(source:String):String
      {
         var self:RVKeybinds=this;
         return RVLocale.render(source).replace(/F10|F11|F12/g,function(...args):String {
            return self.label(args[0]=="F10"?"debug":args[0]=="F11"?"toggle":"mode");
         });
      }
      public function canAct():Boolean
      {
         var allowed:Boolean=false;
         try
         {
            var w:*=world();if(w==null)return false;
            if(api!=null && "isCapturingKey" in api && api.isCapturingKey())return false;
            if(w.onConsol || w.ctr!=null && w.ctr.setkeyOn)return false;
            for each(var key:String in ["mm","pip","sats","stand"])if(w[key]!=null && w[key].active)return false;
            var f:*=w.main.stage.focus;
            if(f is TextField && TextField(f).type=="input" && f.stage!=null)
            {
               var visible:Boolean=true;
               for(var node:*=f;node!=null;node=node.parent)if(!node.visible)visible=false;
               if(visible)return false;
            }
            allowed=true;
         }
         catch(e:*) {}
         return allowed;
      }
      public function nativeTeleKey(e:KeyboardEvent):Boolean {return nativeTeleToken(String(e.keyCode));}
      public function nativeTeleToken(token:String):Boolean
      {
         var result:Boolean=false;
         try{var w:*=world();var keys:Object=w.ctr.save();var b:Object=keys.keyTele;result=b!=null && (String(b.a1)==token || String(b.a2)==token);}catch(e:*){}
         return result;
      }
   }
}
