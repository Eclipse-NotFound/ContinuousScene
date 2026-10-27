package
{
   import modlocales.vision.RVLocale;
   import flash.display.Bitmap;
   import flash.display.BitmapData;
   import flash.display.BitmapDataChannel;
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.display.Shape;
   import flash.display.Sprite;
   import flash.display.Stage;
   import flash.events.Event;
   import flash.events.KeyboardEvent;
   import flash.events.MouseEvent;
   import flash.filesystem.File;
   import flash.filesystem.FileMode;
   import flash.filesystem.FileStream;
   import flash.filters.BlurFilter;
   import flash.geom.ColorTransform;
   import flash.geom.Matrix;
   import flash.geom.Point;
   import flash.geom.Rectangle;
   import flash.text.TextField;
   import flash.text.TextFieldAutoSize;
   import flash.ui.Keyboard;
   import flash.utils.Dictionary;
   import flash.utils.getTimer;
   import flash.utils.getQualifiedClassName;

   import fe.World;
   import fe.Obj;
   import fe.Pt;
   import fe.loc.Location;
   import fe.loc.Tile;
   import fe.unit.Pers;
   import fe.unit.Unit;
   import fe.unit.UnitPlayer;
   import fe.weapon.Weapon;

   /**
    * RealisticVision v0.3 —— 视野系统模组。
    *
    * v0.3：
    * - 软雾：4×4 子格低分辨率雾图 + 高斯模糊（去锯齿），脏标记门控。
    * - 性能：FOV 仅在玩家移动/墙体变化/周期兜底时重算；雾图仅在淡入淡出
    *   变化时重绘；掩膜按 FOV 版本 + 包围盒签名门控；显示树扫描提前退出。
    * - 看门狗：onFrame 全程 try/catch，连续错误自动禁用模组（防错误风暴卡死）。
    *
    * 文档类。由补丁后 MainFE 加载并调用静态 RealisticVisionMod.init(main)。
    */
   public class RealisticVisionMod extends Sprite
   {
      // Lazily classify only tiles actually queried by units. A new immutable
      // sight snapshot invalidates all summaries, including stationary changes.
      private var wallViewBounds:Rectangle;
      private var wallViewOwner:Location;
      private var weaponVisuals:Dictionary = new Dictionary(true);
      private var weaponPass:int = 0;
      private var worldVisuals:Dictionary = new Dictionary(true);
      private var worldMasks:Object = {};
      private var worldSupportRect:Rectangle = new Rectangle();
      private var worldTypes:Dictionary = new Dictionary(true);
      private var worldPass:int = 0;

      private var maskAlphaMap:Array;
      private var maskZeroMap:Array;
      private var classifiedSight:Vector.<uint>;
      private var sightClasses:Vector.<int>;
      // ---- 默认配置（可被 config.txt 覆盖）----
      private var cfgEnabled:Boolean = true;
      private var keybinds:RVKeybinds = new RVKeybinds();
      private var cfgMode:String = "current";   // vanilla=原版 / classic=v0.7.2 / current=当前
      private var cfgDim:Number = 0.35;
      private var cfgViewScale:Number = 1;
      private var cfgSoftCurrent:Number = 20;
      private var cfgSoftClassic:Number = 0;
      private var settingsDirty:Boolean = false;
      private var rangeLight:Array;
      private var rangeRoom:Location;
      private var rangeMem:Object = {};
      private var classicLogicCache:BitmapData;
      // D35: preserve the canonical field, but finish wall seams only in mask
      // regions that are actually queried. Display brightness never grants sight.
      private var classicLogicMemorySamples:BitmapData;
      private var classicLogicVisibilitySamples:BitmapData;
      private var classicLogicRaw:BitmapData;
      private var classicLogicVisibility:BitmapData;
      private var classicLogicWalls:BitmapData;
      private var classicLogicDeltas:Array;
      private var classicLogicTiles:Vector.<int>;
      private var classicSoftInput:BitmapData;
      private var cfgWallBright:Boolean = false;
      private var cfgDoorDim:Number = 0.5;      // 透光门/水后视野的亮度（比记忆暗色亮）
      private var cfgLitMin:Number = 0.6;
      private var cfgFadeStep:Number = 0.1;
      private var cfgMaskBlurClassic:Number = 6.0; // 敌人掩膜模糊（classic，子格 px=5px；0=硬边）
      private var cfgMaskBlurCurrent:Number = 4.0; // current 敌人在真实可见一侧淡出
      private var cfgTeleGrace:Number = 3;
      private var cfgBaseRooms:Object = {};
      private var cfgDebug:Boolean = false;

      // 发布门禁第 2 项：启动日志版本标记（fileLog init 行携带，防"线上跑旧构建"）
      private static const VERSION:String = "v0.33.10-cs-native-reader-test";

      private static const FOV_VISIBLE:int = 2;
      private static const FOV_DIM:int = 1;
      private static const FOV_NONE:int = 0;

      private static const WALL_NEIGHBORS:Array = [[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]];

      private static const ARM_SCAN_R:Number = 64;

      // 瓦片 4 角采样的子格中心偏移（current 模式分类用，避免每瓦片分配数组）
      private static const CORNER_OFFS_X:Array = [0.5,FOG_SUB - 0.5];
      private static const CORNER_OFFS_Y:Array = [0.5,FOG_SUB - 0.5];

      // current：8×8 子格（5px）采样投影轮廓，显示层连续柔化；
      // classic：原版格角光照与格中心记忆分别插值。墙使用独立原版光场。
      private static const FOG_SUB:int = 8;
      private static const FOG_PAD:int = 4;

      // 敌人 FOV 掩膜参数：每瓦片 8px 子格（5px，与雾层一致）。掩膜 = 矢量
      // Shape + 模糊位图填充 + cacheAsBitmap（v0.24.4：alpha 掩膜须双方
      // cacheAsBitmap=true，否则掩膜忽略 alpha/位图填充 → 二分；模糊按模式
      // 对齐雾层边界宽度，敌人明暗交界渐变淡出）；区域外扩覆盖血条（头顶）
      // 与动画超出手臂/翅膀等超出逻辑包围盒的视觉部分
      private static const MASK_SUB:int = 8;
      // current 掩膜采样 fogCache 的亮度阈值（v0.24.5）：门景(≤128)/亮部
      // (<140) 可见；记忆区(166)/未探索(255)/暗部(≥140) 不可见
      private static const MASK_LIT_A:int = 140;
      private static const MASK_PAD_X:int = 2;
      private static const MASK_PAD_TOP:int = 3;
      private static const MASK_PAD_BOTTOM:int = 1;

      private static var inst:RealisticVisionMod;

      /** 游戏调用入口（静态）。 */
      public static function init(main:*):void
      {
         inst = new RealisticVisionMod();
         inst.startup(main);
      }

      private var stageRef:Stage;
      // Optional public API; neither RConnect nor network classes are referenced.
      private static const EXP_HEX:String = "0123456789abcdef";
      // Packed local history only. Current brightness is read on every capture.
      private var explorationBits:Array;
      private var memoryTileState:Array;
      private var sharedRooms:Dictionary = new Dictionary(true);
      private var sharedLight:Array;
      private var sharedSeen:Array;
      private var sharedExplored:Array;
      private var sharedFull:Array;

      private function publishExploration(main:DisplayObjectContainer):void
      {
         if(main == null) return;
         var carrier:RVExplorationCarrier = new RVExplorationCarrier();
         carrier.name = "RVExplorationAPI";
         carrier.visible = false;
         carrier.mouseEnabled = carrier.mouseChildren = false;
         var self:RealisticVisionMod = this;
         carrier["api"] = {version:1,
            terrainReadStats:function():Object {return {calls:self.wallSurface.nativeReadCalls,provided:self.wallSurface.nativeReadProvided,active:self.explorationActive(World.w.loc),mode:self.cfgMode,enabled:self.cfgEnabled,errorCount:self.errCount};},
            active:function(loc:Object):Boolean { return self.explorationActive(loc); },
            capture:function(loc:Object):Array { return self.captureExploration(loc); },
            merge:function(loc:Object, rows:Array):Boolean { return self.mergeExploration(loc,rows); }};
         main.addChild(carrier);
      }

      private function explorationActive(loc:Object):Boolean
      {
         var w:World = World.w;
         return w != null && loc != null && loc === this.curLoc && w.loc === loc && loc.active
            && this.cfgEnabled && w.black && this.cfgMode != "vanilla"
            && !loc.base && this.cfgBaseRooms[loc.id] != true;
      }

      private function captureExploration(loc:Object):Array
      {
         if(!this.explorationActive(loc)) return null;
         var rows:Array = [];
         for(var y:int = 0; y < this.spaceY; y++)
         {
            var row:Array = [];
            for(var x:int = 0; x < this.spaceX; x++)
            {
               var i:int = x+y*this.spaceX;
               var light:int = Math.max(0,Math.min(15,Math.round(Number(loc.getTile(x,y).visi)*15)));
               var bits:String = "";
               if(this.fullySeen[i] || (this.cfgMode == "classic" && this.explored[i] == 1)) bits = "ffffffffffffffff";
               else if(this.explorationBits[i] != null) bits = this.explorationBits[i];
               else
               {
                  for(var b:int = 0; b < 64; b += 4)
                  {
                     var nibble:int = 0;
                     for(var q:int = 0; q < 4; q++)
                     {
                        var sub:int = b+q;
                        if(this.seenSub[(y*8+int(sub/8))*this.subW+x*8+(sub%8)] == 1) nibble |= 1 << q;
                     }
                     bits += EXP_HEX.charAt(nibble);
                  }
                  this.explorationBits[i] = bits;
               }
               row.push(EXP_HEX.charAt(light)+bits);
            }
            rows.push(row.join(""));
         }
         return rows;
      }

      private function mergeExploration(loc:Object, rows:Array):Boolean
      {
         var w:World = World.w;
         if(w == null || loc == null || loc !== w.loc || loc !== this.curLoc
            || this.spaceX < 1 || this.spaceX > 200 || this.spaceY < 1 || this.spaceY > 200
            || rows == null || rows.length != this.spaceY) return false;
         for each(var row:* in rows)
            if(!(row is String) || row.length != this.spaceX*17 || /[^0-9a-f]/.test(row)) return false;
         var old:Array = this.sharedRooms[loc] as Array;
         if(old != null && (old.length != this.spaceY || old[0].length != this.spaceX*17)) old = null;
         var merged:Array = [];
         var changed:Boolean = old == null;
         for(var y:int = 0; y < rows.length; y++)
         {
            var parts:Array = [];
            for(var k:int = 0; k < rows[y].length; k++)
            {
               var a:int = old == null ? 0 : EXP_HEX.indexOf(old[y].charAt(k));
               var b:int = EXP_HEX.indexOf(rows[y].charAt(k));
               parts.push(EXP_HEX.charAt(k%17 == 0 ? Math.max(a,b) : a|b));
            }
            merged[y] = parts.join("");
            if(old != null && merged[y] != old[y]) changed = true;
         }
         if(changed)
         {
            this.sharedRooms[loc] = merged;
            this.restoreSharedExploration();
         }
         return true;
      }

      private function restoreSharedExploration():void
      {
         this.sharedLight = null;
         this.sharedSeen = this.sharedExplored = this.sharedFull = null;
         var rows:Array = this.sharedRooms[this.curLoc] as Array;
         if(rows == null || rows.length != this.spaceY || rows[0].length != this.spaceX*17) return;
         this.sharedLight = new Array(this.spaceX*this.spaceY);
         this.sharedSeen = new Array(this.subW*this.spaceY*8);
         this.sharedExplored = new Array(this.spaceX*this.spaceY);
         this.sharedFull = new Array(this.spaceX*this.spaceY);
         for(var y:int = 0; y < this.spaceY; y++) for(var x:int = 0; x < this.spaceX; x++)
         {
            var i:int = x+y*this.spaceX;
            this.sharedLight[i] = EXP_HEX.indexOf(rows[y].charAt(x*17))/15;
            var all:Boolean = true, any:Boolean = false;
            for(var b:int = 0; b < 64; b++)
            {
               var nibble:int = EXP_HEX.indexOf(rows[y].charAt(x*17+1+int(b/4)));
               var si:int = (y*8+int(b/8))*this.subW+x*8+(b%8);
               if((nibble & (1 << (b%4))) != 0) { this.sharedSeen[si] = 1; any = true; }
               else all = false;
            }
            if(any) this.sharedExplored[i] = 1;
            if(all) this.sharedFull[i] = true;
         }
         this.fogDirty = true;
         this.lastGX = -99999;
      }

      /** Display input only; native visibility and interaction permissions stay local. */
      private function explorationLight(loc:Location, x:int, y:int):Number
      {
         var light:Number = Math.max(0,Math.min(1,loc.getTile(x,y).visi));
         if(!loc.retDark && this.sharedLight != null)
            light = Math.max(light,Number(this.sharedLight[x+y*this.spaceX]));
         if(this.cfgViewScale != 1 && this.rangeRoom === loc && this.rangeLight != null)
            light = Math.max(light,Number(this.rangeLight[x+y*this.spaceX]) || 0);
         return light;
      }

      private function memorySeen(i:int):Boolean
      {
         return this.seenSub[i] == 1 || (this.sharedSeen != null && this.sharedSeen[i] == 1);
      }

      private function memoryExplored(i:int):Boolean
      {
         return this.explored[i] == 1 || (this.sharedExplored != null && this.sharedExplored[i] == 1);
      }

      // 房间状态
      private var curLoc:Location = null;
      private var spaceX:int = 0;
      private var spaceY:int = 0;
      private var fov:Array;
      private var explored:Array;
      private var visCur:Array;
      private var br:Array;   // 连续亮度（原版渐变）：LOS 亮度 × 距离衰减
      private var litArr:Array; // 瓦片 LOS 亮度（1-累计遮光，0..1；墙=1）
      // 子格级"曾见过"历史（0/1）：记忆区↔未探索边界按 5px 子格粒度，而非 40px 瓦片
      private var seenSub:Array;
      private var subW:int = 0;
      private var fullySeen:Array;
      // 射线批次内复用遮光快照；批次外继续实时读取，避免独立查询用到旧值。
      private var rayOpac:Vector.<Number>;
      private var tileOpacity:Vector.<Number>;
      private var rayLoc:Location;
      private var rayWidth:int = 0;
      private var rayHeight:int = 0;
      private var rayBatch:Boolean = false;
      private var wallTopology:Vector.<Boolean>;
      private var wallGeometryDirty:Boolean = true;
      // 柔化前的单位可见性；提高记忆区亮度也不能使敌人显形。
      private var currentSight:BitmapData;
      private var currentSightWritten:Rectangle;
      private var currentSightData:Vector.<uint>;

      // FOV 门控
      private var fovVersion:int = 0;
      private var lastGX:Number = -99999;
      private var lastGY:Number = -99999;
      private var lastStructHash:int = 0;
      private var lastFovFrame:int = -100;   // classic 保留三帧节流
      private var fogBlurPending:Boolean = false; // current 本帧待显示，返回前清除
      private var eyeX:Number = 0;
      private var eyeY:Number = 0;
      private var locDist1:Number = 300;
      private var locDist2:Number = 1000;

      // 自建雾层：原版式瓦片掩膜（无空间模糊，边界为干脆瓦片线）
      private var fogVis:Sprite = null;
      private var fogRaw:BitmapData = null;   // classic 覆盖层/current 工作位图
      private var fogCache:BitmapData = null; // 两模式的雾场/单位裁剪取样缓存
      private var fogBmp:BitmapData = null;
      private var fogBitmap:Bitmap = null;
      // classic：原版光照在格角，FOV/记忆在格中心；分别插值后再合成。
      private var classicRaw:BitmapData = null;
      private var classicMemoryRaw:BitmapData = null;
      private var classicVisibilityRaw:BitmapData = null;
      private var classicVisibilityField:BitmapData = null;
      private var classicWallShade:BitmapData = null;
      private var classicWallShadeBmp:Bitmap = null;
      private var wallLayer:Sprite = null;
      private var fogShadow:Sprite = null;
      private var fogBase:Sprite = null;
      private var wallSurface:RVWallSurface = new RVWallSurface();
      private var classicCornerDeltas:Array = [];
      private var classicCells:Object;
      private var classicCellDim:Number=NaN;
      private var classicCellDark:Boolean;
      private var classicInputRegion:Rectangle;
      private var classicRenderedTiles:Rectangle;
      private var classicLightMatrix:Matrix = new Matrix(FOG_SUB,0,0,FOG_SUB,
         FOG_PAD-FOG_SUB/2,FOG_PAD-FOG_SUB*1.5);
      private var classicMemoryMatrix:Matrix = new Matrix(FOG_SUB,0,0,FOG_SUB,
         FOG_PAD,FOG_PAD-FOG_SUB);
      private var brightnessToFog:ColorTransform = new ColorTransform(-1,-1,-1,1,255,255,255,0);
      // v0.28.0：墙与地板用互补 mask 分区替换；墙保留原版位图的完整渐变。
      private var lastA:Array = null;   // 每瓦片上次写入 classicRaw 的 alpha（变化才写像素）
      private var memCur:Array = null;  // 每格记忆进度；classic按格中心显示，current墙按格角显示
      // 两种模式的墙使用同源原版角点；地板雾效各自保留。
      private var wallA:Array = null;
      private var wallTiles:Array = [];
      private var wallCorners:Array = [];
      private var wallRaw:BitmapData = null;
      private var wallBmp:Bitmap = null;
      private var wallClip:Shape = null;
      private var floorClip:Shape = null;
      // 跨房间记忆（v0.22）：loc.id → explored 数组（原版靠 tile.visi 缓存
      // 保留已探索常亮；模组自己的 explored[] 需随房间切换保存/恢复，否则
      // 回到房间时全部按未探索处理）
      private var roomMem:Object = {};
      private var fogDirty:Boolean = false;
      private var scenePaintLoc:Location = null;
      private var sceneLastPaintBounds:Rectangle = null;
      private var fogRect:Rectangle = null;
      private var fogCellRect:Rectangle = new Rectangle(0,0,FOG_SUB,FOG_SUB);
      private var fogPoint:Point = new Point(0,0);
      private var fogCellPoint:Point = new Point(0,0);
      private var fogBlur:BlurFilter = new BlurFilter(2.0,2.0,2);   // classic（仿原版）半影
      private var curBlur:BlurFilter = new BlurFilter(4.0,4.0,3);   // current：阴影渐变过渡（≈32px 世界）
      // 敌人掩膜模糊（v0.24.3）：按模式对齐各自雾层边界的模糊策略——
      // BlurFilter(bx,q) ≈ 盒模糊 bx px 应用 q 次，σ = bx·√(q/12) 子格：
      // classic 目标 40px（1px/瓦片双线性渐变）→ 6.0/q2（σ≈12px）；current
      // 目标 32px（雾层 curBlur）→ 4.0/q3（σ≈10px，与雾层同参）。0=硬边
      private var maskBlurClassic:BlurFilter = new BlurFilter(6.0,6.0,2);
      private var maskBlurCurrent:BlurFilter = new BlurFilter(4.0,4.0,3);

      private var defCT:ColorTransform = new ColorTransform();
      private var infraCT:ColorTransform = new ColorTransform(1,1,1,1,100);

      // 敌人显示状态：unit -> {state:int, m2:Shape, m3:Shape, m2d:BitmapData,
      // m2e:BitmapData, lastFov:int, lastBb:String}（m2d/m2e=掩膜二值场/模糊场）
      private var unitVis:Dictionary = new Dictionary(true);
      // 被我们强制隐藏血条的单位
      private var hpHidden:Dictionary = new Dictionary(true);
      // 显示树扫描：被我们隐藏的非单位子对象（狮鹫手臂等）
      private var managedHidden:Dictionary = new Dictionary(true);
      private var managedCount:int = 0;

      // 念力宽限倒计时
      private var teleGraceFrames:int = 0;
      private var teleLast:Object = null;

      // 看门狗
      private var errCount:int = 0;

      // 调试
      private var dbgTxt:TextField = null;
      private var dbgOn:Boolean = false;
      private var frameCount:int = 0;
      private var lastFrameMs:int = 0;
      private var normalApplied:Boolean = false;
      private var toastTxt:TextField = null;
      private var toastUntil:int = 0;

      // 自动化验证埋点（config autotest=1 启用；默认关，不影响正常游玩）。
      // 每 300 帧输出一行窗口统计 autoStats()，事件（进房/念力抓放/F 键/
      // 看门狗）即时输出——验证 v0.24.7 五处优化与 v0.24.6 修复的运行时证据
      private var cfgAutoTest:Boolean = false;
      private var atLastEmit:int = 0; // 上次统计输出的 frameCount（窗口差值触发）
      private var atFovM:int = 0;    // fov 重算：moved 触发（过 3 帧节流）
      private var atFovH:int = 0;    // fov 重算：结构哈希变化（墙破坏/门）
      private var atFovF:int = 0;    // fov 重算：30 帧兜底
      private var atMvThr:int = 0;   // moved 但被 3 帧节流跳过
      private var atBlurD:int = 0;   // current：新雾场显示次数（兼容旧统计字段名）
      private var atClsF:int = 0;    // classic：全图循环执行帧
      private var atClsS:int = 0;    // classic：30Hz 门控跳过帧
      private var atWsEx:int = 0;    // 武器扫描执行帧
      private var atWsSk:int = 0;    // 武器扫描门控跳过帧
      private var atMaskRaw:int = 0; // classic 掩膜缓存采样分支（零 raycast）
      private var atMaskRay:int = 0; // 掩膜 raycast 兜底分支
      private var atMsSum:int = 0;   // 窗口内模组帧耗时累计（ms）
      private var atMsMax:int = 0;   // 窗口内模组帧耗时峰值（ms）
      private var atE0:int = 0;      // 敌人三态计数（最近一帧快照：全隐）
      private var atE1:int = 0;      // 全显
      private var atE2:int = 0;      // 部分可见（挂掩膜）

      // 哔哔小马选项页的开关面板
      private var optPanel:Sprite = null;
      private var optTxt:TextField = null;
      // v0.25.0：注入选项页原生列表的模式行（克隆 visPipOptItem 实例，点击循环模式）
      private var optRow:Object = null;      // 注入的行实例
      private var optRowAnchor:Object = null; // 锚点行（id=="fullscreen"）——子选项卡检测用
      // v0.26.0：MSW 模组设置聚合页注册（MoreSkills&Weapons MSWSettingsHub 契约）
      private var mswRegistered:Boolean = false;
      private var mswRetryFrames:int = 0;
      private var mswFailLogged:Boolean = false;

      public function RealisticVisionMod()
      {
         super();
      }

      private function startup(main:*):void
      {
         // 文件日志（trace 在 release 构建被剥离，写 applicationStorageDirectory
         // 诊断启动卡点——RConnect 同款做法）
         var lg:String = "startup enter main=" + (main != null) + " stage=" + (main != null && main.stage != null);
         if(main == null || main.stage == null)
         {
            this.fileLog(lg + " -> NO STAGE, abort");
            trace("[RVision] init: no stage");
            return;
         }
         stageRef = main.stage;
         this.publishExploration(main as DisplayObjectContainer);
         this.loadConfig();
         this.fileLog(lg + " -> after loadConfig enabled=" + this.cfgEnabled);
         stageRef.addEventListener(Event.ENTER_FRAME,this.onFrame);
         stageRef.addEventListener(KeyboardEvent.KEY_DOWN,this.onKeyDown);
         stageRef.addEventListener(MouseEvent.RIGHT_MOUSE_DOWN,this.onRightDown);
         trace("[RVision] init ok enabled=" + this.cfgEnabled);
         this.fileLog("init ok " + VERSION + " settings=ModSettings-v1 enabled=" + this.cfgEnabled);
      }

      /** 诊断文件日志：%APPDATA%/<appid>/Local Store/RVision.log（trace 被 release 剥离）。 */
      private function fileLog(msg:String):void
      {
         try
         {
            var f:File = File.applicationStorageDirectory.resolvePath("RVision.log");
            var fs:FileStream = new FileStream();
            fs.open(f,FileMode.APPEND);
            fs.writeUTFBytes(msg + "\n");
            fs.close();
         }
         catch(err:Error)
         {
         }
      }

      // ==================== 配置 ====================

      private function loadConfig():void
      {
         try
         {
            var f:File = File.applicationStorageDirectory.resolvePath("RealisticVision_config.txt");
            if(!f.exists) f = File.applicationDirectory.resolvePath("mods/RealisticVision/release/config.txt");
            if(!f.exists)
            {
               return;
            }
            var fs:FileStream = new FileStream();
            fs.open(f,FileMode.READ);
            var s:String = fs.readUTFBytes(fs.bytesAvailable);
            fs.close();
            var lines:Array = s.split(/\r?\n/);
            for each(var line:String in lines)
            {
               var kv:Array = line.split("=",2);
               if(kv.length != 2)
               {
                  continue;
               }
               var key:String = kv[0];
               var val:String = kv[1];
               if(key == "enabled")
               {
                  this.cfgEnabled = val == "1";
               }
               else if(key == "wallbright")
               {
                  if(val == "1" || val == "0") this.cfgWallBright = val == "1";
               }
                else if(key == "dim")
                {
                   this.cfgDim = settingNumber(val,0,1,0.35);
                }
               else if(key == "viewscale") this.cfgViewScale = settingNumber(val,0.5,3,1);
               else if(key == "soft_current") this.cfgSoftCurrent = settingNumber(val,0,60,20);
               else if(key == "soft_classic") this.cfgSoftClassic = settingNumber(val,0,40,0);
                else if(key == "doordim")
                {
                   this.cfgDoorDim = Number(val);
                }
               else if(key == "litmin")
               {
                  this.cfgLitMin = Number(val);
               }
               else if(key == "fadestep")
               {
                  this.cfgFadeStep = Number(val);
               }
               else if(key == "maskblur_classic")
               {
                  this.cfgMaskBlurClassic = Number(val);
                  this.maskBlurClassic.blurX = this.maskBlurClassic.blurY = this.cfgMaskBlurClassic;
               }
               else if(key == "maskblur_current")
               {
                  this.cfgMaskBlurCurrent = Number(val);
                  this.maskBlurCurrent.blurX = this.maskBlurCurrent.blurY = this.cfgMaskBlurCurrent;
               }
               else if(key == "telegrace")
               {
                  this.cfgTeleGrace = Number(val);
               }
               else if(key == "base_rooms")
               {
                  var ids:Array = val.split(",");
                  for each(var id:String in ids)
                  {
                     if(id != "")
                     {
                        this.cfgBaseRooms[id] = true;
                     }
                  }
               }
               else if(key == "debug")
               {
                  this.cfgDebug = val == "1";
               }
               else if(key == "autotest")
               {
                  this.cfgAutoTest = val == "1";
               }
               else if(key == "mode")
               {
                  if(val == "vanilla" || val == "classic" || val == "current")
                  {
                     this.cfgMode = val;
                  }
               }
            }
         }
         catch(err:Error)
         {
            trace("[RVision] config read error: " + err);
         }
      }

      private static function settingNumber(v:*,lo:Number,hi:Number,fallback:Number):Number
      {
         if(v == null || String(v).replace(/\s/g,"") == "") return fallback;
         var n:Number = Number(v);
         return isFinite(n) ? Math.max(lo,Math.min(hi,n)) : fallback;
      }

      private function setVisualSetting(key:String,v:*):void
      {
         if(key == "dim") this.cfgDim = settingNumber(v,0,1,0.35);
         else if(key == "viewscale") this.cfgViewScale = settingNumber(v,0.5,3,1);
         else if(key == "soft_current") this.cfgSoftCurrent = settingNumber(v,0,60,20);
         else if(key == "soft_classic") this.cfgSoftClassic = settingNumber(v,0,40,0);
         else return;
         // Repaint in place: resetting the room would discard subcell memory.
         this.settingsDirty = true;
         this.saveConfig();
      }

      private function updateViewDistances(loc:Location):void
      {
         var d1:Number = (loc.lDist1 > 0 ? loc.lDist1 : 300)*this.cfgViewScale;
         var d2:Number = (loc.lDist2 > 0 ? loc.lDist2 : 1000)*this.cfgViewScale;
         if(d1 != this.locDist1 || d2 != this.locDist2) this.settingsDirty = true;
         this.locDist1 = d1; this.locDist2 = d2;
         this.curBlur.blurX = this.curBlur.blurY = this.cfgSoftCurrent/5;
      }

      /** Native corner light sampling, in a mod-owned field. No native writes.
       * Retain the native subtractive opacity and phase, including solid cores. */
      private function updateRangeLight(loc:Location):void
      {
         if(this.cfgViewScale == 1) return;
         if(this.rangeRoom !== loc || this.rangeLight == null || this.rangeLight.length != this.spaceX*this.spaceY)
         {
            this.rangeRoom = loc;
            var saved:Object=this.rangeMem[loc.id];
            if(saved == null || saved.width != this.spaceX || saved.height != this.spaceY)
            {saved={width:this.spaceX,height:this.spaceY,values:new Array(this.spaceX*this.spaceY)};this.rangeMem[loc.id]=saved;}
            this.rangeLight = saved.values;
         }
         var ex:Number = this.eyeX, ey:Number = this.eyeY;
         for(var y:int=1;y<this.spaceY;y++) for(var x:int=1;x<this.spaceX;x++)
         {
            var dx:Number=x*Tile.tileX-ex,dy:Number=y*Tile.tileY-ey;
            var value:Number=this.distFalloff(dx*dx+dy*dy);
            if(value>0)
            {
               if(Math.abs(dx)==Math.abs(dy)) dy++;
               var sx:Number,sy:Number,steps:int;
               if(Math.abs(dx)>=Math.abs(dy)) {sx=dx>0?Tile.tileX:-Tile.tileX;sy=dy/dx*sx;steps=int(dx/sx);}
               else {sy=dy>0?Tile.tileY:-Tile.tileY;sx=dx/dy*sy;steps=int(dy/sy);}
               for(var k:int=1;k<=steps;k++)
               {
                  var t:Tile=loc.getTile(Math.floor((ex+k*sx)/Tile.tileX),Math.floor((ey+k*sy)/Tile.tileY));
                  var opacity:Number=t.opac;
                  if(t.water>0 && loc.opacWater>opacity) opacity=loc.opacWater;
                  if(opacity>0) value-=opacity;
                  if(value<=0) {value=0;break;}
               }
            }
            var i:int=x+y*this.spaceX, previous:Number=Number(this.rangeLight[i]);
            this.rangeLight[i]=loc.retDark?value:Math.max(value,isNaN(previous)?0:previous);
         }
      }

      private function saveConfig():void
      {
         try
         {
            var f:File = File.applicationStorageDirectory.resolvePath("RealisticVision_config.txt");
            var fs:FileStream = new FileStream();
            fs.open(f,FileMode.WRITE);
            var ids:Array = [];
            for(var id:String in this.cfgBaseRooms)
            {
               ids.push(id);
            }
            var s:String = "enabled=" + (this.cfgEnabled ? "1" : "0") + "\n"
               + "mode=" + this.cfgMode + "\n"
               + "wallbright=" + (this.cfgWallBright ? "1" : "0") + "\n"
               + "dim=" + this.cfgDim + "\n"
               + "viewscale=" + this.cfgViewScale + "\n"
               + "soft_current=" + this.cfgSoftCurrent + "\n"
               + "soft_classic=" + this.cfgSoftClassic + "\n"
               + "doordim=" + this.cfgDoorDim + "\n"
               + "litmin=" + this.cfgLitMin + "\n"
               + "fadestep=" + this.cfgFadeStep + "\n"
               + "maskblur_classic=" + this.cfgMaskBlurClassic + "\n"
               + "maskblur_current=" + this.cfgMaskBlurCurrent + "\n"
               + "telegrace=" + this.cfgTeleGrace + "\n"
               + "base_rooms=" + ids.join(",") + "\n"
               + "debug=" + (this.cfgDebug ? "1" : "0") + "\n"
               + "autotest=" + (this.cfgAutoTest ? "1" : "0") + "\n";
            fs.writeUTFBytes(s);
            fs.close();
            if(this.cfgAutoTest)
            {
               this.fileLog("auto config saved (enabled=" + this.cfgEnabled
                  + " mode=" + this.cfgMode + ")");
            }
         }
         catch(err:Error)
         {
            trace("[RVision] config write error: " + err);
            this.fileLog("auto config write error: " + err + "\n" + err.getStackTrace());
         }
      }

      private function onKeyDown(e:KeyboardEvent):void
      {
         if(!this.keybinds.canAct()) return;
         if(this.keybinds.matches("debug",e))
         {
            e.stopImmediatePropagation(); e.preventDefault();
            this.dbgOn = !this.dbgOn;
            if(!this.dbgOn && this.dbgTxt)
            {
               this.dbgTxt.visible = false;
            }
         }
         else if(this.keybinds.matches("toggle",e))
         {
            e.stopImmediatePropagation(); e.preventDefault();
            this.cfgEnabled = !this.cfgEnabled;
            this.saveConfig();
            this.curLoc = null;
            this.errCount = 0;
            trace("[RVision] enabled=" + this.cfgEnabled);
            if(this.cfgAutoTest)
            {
               this.fileLog("auto key F11 enabled=" + this.cfgEnabled);
            }
         }
         else if(this.keybinds.matches("mode",e))
         {
            e.stopImmediatePropagation(); e.preventDefault();
            // 渲染模式轮换：vanilla（原版）→ classic（v0.7.2）→ current（当前）
            if(this.cfgAutoTest)
            {
               this.fileLog("auto key F12");
            }
            this.cycleMode();
         }
         else if(this.keybinds.nativeTeleKey(e))
         {
            // 念力键（默认 Q）：目标为不可见敌人时拦截，游戏 Ctr 收不到
            if(this.blockInvisibleGrab())
            {
               e.stopImmediatePropagation();
            }
         }
      }

      private function onRightDown(e:MouseEvent):void
      {
         if(!this.keybinds.canAct() || !this.keybinds.nativeTeleToken("rmb")) return;
         // 念力备用键（右键）：同上
         if(this.blockInvisibleGrab())
         {
            e.stopImmediatePropagation();
         }
      }

      /**
       * 复刻游戏抓取目标选择（光标 50px 内最近 levitPoss 且 massa<=maxTeleMassa 的对象）：
       * 若该对象是不可见的敌人 → 拦截输入（玩家不能隔墙选中敌人；物品不受限）。
       */
      private function blockInvisibleGrab():Boolean
      {
         var w:World = World.w;
         if(w == null || w.loc == null || w.gg == null || !this.cfgEnabled || !w.black)
         {
            return false;
         }
         var loc:Location = w.loc;
         if(loc !== this.curLoc || this.cfgMode == "vanilla" || loc.base || this.cfgBaseRooms[loc.id] == true)
         {
            return false;
         }
         var maxMassa:Number = w.pers != null ? (w.pers as Pers).maxTeleMassa : 1;
         var best:Object = null;
         var bestD:Number = 50 * 50;
         var obj:Pt = loc.firstObj;
         var guard:int = 0;
         while(obj != null && guard < 5000)
         {
            if(obj is Obj && (obj as Obj).levitPoss && (obj as Obj).massa <= maxMassa)
            {
               var dx:Number = w.celX - obj.X;
               var dy:Number = w.celY - (obj.Y - (obj as Obj).scY / 2);
               var d:Number = dx * dx + dy * dy;
               if(d < bestD)
               {
                  bestD = d;
                  best = obj;
               }
            }
            obj = obj.nobj;
            guard++;
         }
         if(best is Unit)
         {
            var bu:Unit = best as Unit;
            if(!bu.player && !bu.npc && bu.fraction != Unit.F_PLAYER)
            {
               if(this.enemyState(loc,bu) == 0)
               {
                  return true;
               }
            }
         }
         return false;
      }

      // ==================== 主循环（含看门狗） ====================

      private function onFrame(e:Event):void
      {
         this.keybinds.tick();
         var t0:int = getTimer();
         this.updateToast(t0);
         this.frameCount++;
         if(this.frameCount % 180 == 1)
         {
            // 心跳（诊断）：确认 onFrame 在跑（每 ~3 秒一行）
            this.fileLog("tick " + this.frameCount);
         }
         try
         {
            this.onFrameInner();
            this.lastFrameMs = getTimer() - t0;
            if(this.cfgAutoTest)
            {
               this.atMsSum += this.lastFrameMs;
               if(this.lastFrameMs > this.atMsMax)
               {
                  this.atMsMax = this.lastFrameMs;
               }
               // frameCount 被 debugStep 双递增（奇偶不稳），用窗口差值触发
               if(this.frameCount - this.atLastEmit >= 300)
               {
                  this.atLastEmit = this.frameCount;
                  this.autoStats();
               }
            }
            this.errCount = 0;
         }
         catch(err:Error)
         {
            this.lastFrameMs = getTimer() - t0;
            this.errCount++;
            if(this.errCount == 1)
            {
               trace("[RVision] ERROR: " + err + "\n" + err.getStackTrace());
               if(this.cfgAutoTest)
               {
                  this.fileLog("auto error #" + err + "\n" + err.getStackTrace());
                  try
                  {
                     var w:World = World.w;
                     if(w != null && w["verror"] != null)
                     {
                        this.fileLog("auto verror: " + w["verror"].txt.text);
                     }
                  }
                  catch(e2:Error)
                  {
                  }
               }
            }
            if(this.errCount > 30)
            {
               if(this.cfgEnabled)
               {
                  this.cfgEnabled = false;
                  this.saveConfig();
                  trace("[RVision] auto-disabled after repeated errors");
                  if(this.cfgAutoTest)
                  {
                     this.fileLog("auto watchdog disabled after " + this.errCount + " errors");
                  }
               }
               this.errCount = 0;
            }
         }
      }

      /** 自动化验证：每 300 帧输出一行窗口统计并复位计数器（autotest=1）。 */
      private function autoStats():void
      {
         this.fileLog("auto st f=" + this.frameCount
            + " mode=" + this.cfgMode
            + " fov=" + this.atFovM + "/" + this.atFovH + "/" + this.atFovF
            + " mvThr=" + this.atMvThr
            + " blurD=" + this.atBlurD
            + " cls=" + this.atClsF + "/" + this.atClsS
            + " ws=" + this.atWsEx + "/" + this.atWsSk
            + " mask=" + this.atMaskRaw + "/" + this.atMaskRay
            + " e=" + this.atE0 + "/" + this.atE1 + "/" + this.atE2
            + " mgr=" + this.managedCount
            + " ms=" + (this.atMsSum / 300).toFixed(2) + "/" + this.atMsMax
            + " err=" + this.errCount);
         this.atFovM = 0;
         this.atFovH = 0;
         this.atFovF = 0;
         this.atMvThr = 0;
         this.atBlurD = 0;
         this.atClsF = 0;
         this.atClsS = 0;
         this.atWsEx = 0;
         this.atWsSk = 0;
         this.atMaskRaw = 0;
         this.atMaskRay = 0;
         this.atMsSum = 0;
         this.atMsMax = 0;
      }

      private function onFrameInner():void
      {
         var w:World = World.w;
         if(w == null)
         {
            return;
         }
         if(!this.mswRegistered)
         {
            this.tryMswRegister(w);
         }
         if(w.allStat < 1)
         {
            if(this.curLoc != null)
            {
               this.resetOff();
            }
            return;
         }
         var loc:Location = w.loc;
         if(loc == null || !loc.active || w.gg == null)
         {
            return;
         }
         if(loc !== this.curLoc)
         {
            this.resetRoom(w,loc);
         }
         this.updateOptPanel(w);
         // 透传模式（vanilla / 总开关关 / 游戏黑暗关 / 安全基地）：游戏原生渲染，
         // 模组不碰 visi/visLight/lightBmp（原版效果原样恢复）
         if(!this.cfgEnabled || !w.black || this.cfgMode == "vanilla" || loc.base || this.cfgBaseRooms[loc.id] == true)
         {
            // v0.24.6：清除模组一切残留（掩膜/隐藏单位/隐藏武器/手臂）——
            // 否则 F12/F11 切回原版后，此前在暗处被隐藏的敌人保持隐身、
            // 过期掩膜继续裁剪单位
            this.restoreAll(w,loc);
            this.normalMode(w,loc);
            this.debugStep(w,loc,true);
            return;
         }
         this.updateViewDistances(loc);
         if(this.settingsDirty) {this.lastGX=-99999;this.fogDirty=true;this.settingsDirty=false;}
         // current 随每帧位移刷新；classic 保留既有节奏。
         var gg:UnitPlayer = loc.gg;
         var current:Boolean = this.cfgMode == "current";
         var threshold:Number = current ? 0.25 : 1.5;
         var moved:Boolean = Math.abs(gg.X-this.lastGX)>threshold || Math.abs(gg.Y-this.lastGY)>threshold;
         var opacityChanged:Boolean = current && this.prepareOcclusion(loc);
         var hash:int = !current && (this.frameCount & 1)==0 ? this.structHash(loc) : this.lastStructHash;
         var needFov:Boolean = (moved && (current || this.frameCount-this.lastFovFrame>=3))
            || opacityChanged || hash!=this.lastStructHash || this.frameCount%30==0;
         if(needFov)
         {
            if(this.cfgAutoTest)
            {
               if(opacityChanged || hash != this.lastStructHash)
               {
                  this.atFovH++;
               }
               else if(moved)
               {
                  this.atFovM++;
               }
               else
               {
                  this.atFovF++;
               }
            }
            this.lastFovFrame = this.frameCount;
            this.lastGX = gg.X;
            this.lastGY = gg.Y;
            this.lastStructHash = hash;
            this.computeFov(loc,current);
            this.fovVersion++;
            this.fogDirty = true;
         }
         else if(this.cfgAutoTest && moved)
         {
            this.atMvThr++;
         }
         if(this.cfgMode == "classic")
         {
            // classic（仿原版）：雾场复刻原版亮度 + 记忆区暗化（v4 自渲染）
            this.applyVisionClassic(w,loc,needFov);
         }
         else
         {
            // current（平滑阴影）：模组自建雾层全权接管
            this.applyVision(w,loc,needFov,true);
         }
         this.updateWallSurface(w,loc);
         this.hideEnemies(w,loc,needFov);
         if(this.frameCount % 10 == 0)
         {
            this.sweepMasks();
         }
         this.blockInvisibleHover(loc,gg);
         this.enforceTele(loc);
         this.debugStep(w,loc,false);
      }

      private function resetOff():void
      {
         this.classicRenderedTiles=null;
         this.classicCells=null;
         this.restoreWorldVisuals();
         this.restoreWeaponVisuals();
         this.releaseClassicLogic();
         this.wallSurface.reset();
         this.wallViewBounds = null; this.wallViewOwner = null;
         this.curLoc = null;
         this.classifiedSight = null; this.sightClasses = null;
         this.explored = [];
         this.explorationBits = null;this.memoryTileState=null;
         this.fov = [];
         this.visCur = [];
         this.rangeMem = {}; this.rangeRoom = null; this.rangeLight = null;
         this.roomMem = {};   // 世界重置（读档/加载）：跨房间记忆清空
         this.sharedRooms = new Dictionary(true);
         this.sharedLight = null;
         this.sharedSeen = this.sharedExplored = this.sharedFull = null;
         this.unitVis = new Dictionary(true);
         this.hpHidden = new Dictionary(true);
         this.managedHidden = new Dictionary(true);
         this.managedCount = 0;
         this.lastGX = this.lastGY = -99999;
         this.lastFovFrame = -100;
         this.fogBlurPending = false;
      }

      private function resetRoom(w:World, loc:Location):void
      {
         this.classicRenderedTiles=null;
         this.classicCells=null;
         this.restoreWorldVisuals();
         this.restoreWeaponVisuals();
         this.releaseClassicLogic();
         // 跨房间记忆（v0.22）：离开前保存当前房间的 explored（最后一次
         // FOV 重算后的状态），回到同 id 房间时恢复——原版靠 tile.visi 缓存
         // 保留已探索常亮，模组需自己保存 explored[]
         if(this.curLoc != null && this.explored != null && this.explored.length > 0)
         {
            this.roomMem[this.curLoc.id] = this.explored.concat();
         }
         this.rayLoc = null;
         this.rayBatch = false;
         this.currentSightData = null;
         this.currentSightWritten = null;
         this.wallViewBounds = null; this.wallViewOwner = null;
         this.classifiedSight = null; this.sightClasses = null;
         this.wallGeometryDirty = true;
         this.curLoc = loc;
         this.spaceX = loc.spaceX;
         this.spaceY = loc.spaceY;
         // classic v5：每瓦片 alpha 缓存随房间重置（同尺寸房间防残留）
         this.lastA = null;
         this.wallA = null;
         this.wallTiles = [];
         this.wallCorners = [];
         var n:int = this.spaceX * this.spaceY;
         this.fullySeen = new Array(n);
         this.explorationBits = new Array(n);this.memoryTileState=new Array(n);
         this.fov = new Array(n);
         this.visCur = new Array(n);
         this.br = new Array(n);
         this.litArr = new Array(n);
         this.subW = this.spaceX * FOG_SUB;
         this.seenSub = new Array(this.subW * this.spaceY * FOG_SUB);
         // 恢复跨房间记忆（存在且尺寸匹配时），否则新房间全未探索
         var mem:Array = this.roomMem[loc.id] as Array;
         var hasMem:Boolean = mem != null && mem.length == n;
         this.explored = hasMem ? mem.concat() : new Array(n);
         var i:int;
         for(i = 0; i < n; i++)
         {
            this.fov[i] = FOV_NONE;
            if(!hasMem)
            {
               this.explored[i] = 0;
            }
            this.visCur[i] = 0;
            this.br[i] = 0;
            this.litArr[i] = 0;
         }
         // v0.25.9 的 visi 场播种已回滚（回滚到 cfecf5a 语义）：
         // 记忆状态仅由本模组增量维护（computeFov/roomMem）
         if(hasMem)
         {
            // current 的记忆区填充按 seenSub 子格历史（fillMemoryTile）——
            // 恢复 explored 时把已探索瓦片的 seenSub 全部标记，首帧记忆区
            // 显示正确（瓦片级边界，随后 FOV 重算细化）
            var si:int;
            var sx:int;
            var sy:int;
            for(si = 0; si < n; si++)
            {
               if(this.explored[si] == 1)
               {
                  var tx0:int = si % this.spaceX;
                  var ty0:int = (si / this.spaceX) | 0;
                  var base:int = ty0 * FOG_SUB * this.subW + tx0 * FOG_SUB;
                  this.fullySeen[si] = true;
                  for(sx = 0; sx < FOG_SUB; sx++)
                  {
                     for(sy = 0; sy < FOG_SUB; sy++)
                     {
                        this.seenSub[base + sy * this.subW + sx] = 1;
                     }
                  }
               }
            }
         }
         // 透传/原版（vanilla/总开关关/黑暗关/安全基地）：visi 与掩膜完全交给游戏
         var pass:Boolean = !this.cfgEnabled || !w.black || this.cfgMode == "vanilla"
            || loc.base || this.cfgBaseRooms[loc.id] == true;
         if(!pass)
         {
            this.ensureFog(w);
            // classic合成借用fogRaw保存RGB；同尺寸切回current也须像新建图
            // 那样初始化三个缓冲，否则旧图/外围像素会留到淡入或模糊结束。
            this.fogRaw.fillRect(this.fogRect,0xFF000000);
            this.fogCache.fillRect(this.fogRect,0xFF000000);
            this.fogBmp.fillRect(this.fogRect,0xFF000000);
            this.fogBlurPending = false;
            if(this.cfgMode == "classic")
            {
               // classic（v4）：雾场自渲染，隐藏游戏掩膜（模式切换时一并隐藏，
               // 避免首帧露出）
               if(w.grafon != null)
               {
                  w.grafon.visLight.visible = false;
               }
            }
            // visi/t_visi 完全由原版维护。墙内插值也依赖邻接地板的角值，
            // 因而不能只保护墙格；地图/传送沿用原版的曾见判定（D22）。
         }
         this.fogDirty = true;
         this.fovVersion++;
         this.normalApplied = false;
         this.restoreSharedExploration();
         this.updateViewDistances(loc);
         // 置为不可能值：进房首帧强制 needFov（立即重算 fogCache，避免首帧全黑）
         this.lastGX = -99999;
         this.lastGY = -99999;
         trace("[RVision] room " + loc.id + " " + this.spaceX + "x" + this.spaceY + " lDist2=" + loc.lDist2 + " mode=" + this.cfgMode);
         if(this.cfgAutoTest)
         {
            this.fileLog("auto room id=" + loc.id + " " + this.spaceX + "x" + this.spaceY
               + " base=" + (loc.base || this.cfgBaseRooms[loc.id] == true)
               + " black=" + w.black + " mode=" + this.cfgMode
               + " enabled=" + this.cfgEnabled);
         }
      }

      /** 自建雾层插在visLight之后；应用各模式的视野时再隐藏原版显示。 */
      private function ensureFog(w:World):void
      {
         if(w.grafon == null)
         {
            return;
         }
         if(this.fogVis == null)
         {
            this.fogVis = new Sprite();
            this.fogVis.mouseEnabled = false;
            this.fogVis.mouseChildren = false;
         }
         var bw:int = this.spaceX * FOG_SUB + FOG_PAD * 2;
         var bh:int = this.spaceY * FOG_SUB + FOG_PAD * 2;
         if(this.fogBmp == null || this.fogBmp.width != bw || this.fogBmp.height != bh)
         {
            if(this.fogBmp != null)
            {
               this.fogBmp.dispose();
            }
            if(this.fogRaw != null)
            {
               this.fogRaw.dispose();
            }
            if(this.fogCache != null)
            {
               this.fogCache.dispose();
            }
            this.fogRaw = new BitmapData(bw,bh,true,0xFF000000);
            this.fogCache = new BitmapData(bw,bh,true,0xFF000000);
            this.fogBmp = new BitmapData(bw,bh,true,0xFF000000);
            if(this.classicVisibilityField != null) this.classicVisibilityField.dispose();
            if(this.classicWallShade != null) this.classicWallShade.dispose();
            this.classicVisibilityField = new BitmapData(bw,bh,false,0xFFFFFF);
            this.classicWallShade = new BitmapData(bw,bh,true,0);
            if(this.classicWallShadeBmp != null && this.classicWallShadeBmp.parent)
               this.classicWallShadeBmp.parent.removeChild(this.classicWallShadeBmp);
            this.classicWallShadeBmp = new Bitmap(this.classicWallShade,"auto",true);
            this.classicWallShadeBmp.scaleX = this.classicWallShadeBmp.scaleY = Tile.tileX / FOG_SUB;
            this.classicWallShadeBmp.x = this.classicWallShadeBmp.y = -FOG_PAD * Tile.tileX / FOG_SUB;
            this.fogRect = new Rectangle(0,0,bw,bh);
            if(this.fogBitmap != null && this.fogBitmap.parent)
            {
               this.fogBitmap.parent.removeChild(this.fogBitmap);
            }
            this.fogBitmap = new Bitmap(this.fogBmp);
            // v0.22.1：**smoothing=true**（参考原版"模糊墙壁单位格子"思路——
            // 原版 lightBmp 1px/瓦片 + 双线性插值产生 40px 渐变雾带）。current
            // 的 5px 子格值之间双线性插值（5px 渐变带），消除 5px 像素块锯齿；
            // 配合 curBlur（4.0 ≈32px）→ 阴影边缘平滑柔和。线状阴影几何
            // （子格 raycast）保留，仅显示层插值。
            this.fogBitmap.smoothing = true;
            this.fogBitmap.scaleX = this.fogBitmap.scaleY = Tile.tileX / FOG_SUB;
            this.fogBitmap.x = this.fogBitmap.y = -FOG_PAD * Tile.tileX / FOG_SUB;
            this.fogVis.addChild(this.fogBitmap);
            this.fogDirty = true;
         }
         // classic仍按每格1像素平滑插值，但格角光照与格中心记忆分别变换。
         // 富余1列2行保持黑色，覆盖两套相位下的房间边界。
         var cw:int = this.spaceX + 1;
         var ch:int = this.spaceY + 2;
         if(this.classicRaw == null || this.classicRaw.width != cw || this.classicRaw.height != ch)
         {
            if(this.classicRaw != null)
            {
               this.classicRaw.dispose();
               this.classicMemoryRaw.dispose();
               this.classicVisibilityRaw.dispose();
            }
            this.classicRaw = new BitmapData(cw,ch,true,0xFF000000); // 初始全黑
            this.classicMemoryRaw = new BitmapData(cw,ch,true,0xFF000000);
            this.classicVisibilityRaw = new BitmapData(cw,ch,false,0xFFFFFF);
            this.lastA = null;
         }
         if(this.lastA == null || this.lastA.length != this.spaceX * this.spaceY)
         {
            var nk:int = this.spaceX * this.spaceY;
            this.lastA = new Array(nk);
            this.memCur = new Array(nk);
            var k:int;
            for(k = 0; k < nk; k++)
            {
               this.lastA[k] = -1;
               this.memCur[k] = 0;
            }
         }
         if(this.wallRaw == null || this.wallRaw.width != cw || this.wallRaw.height != ch)
         {
            if(this.wallRaw != null) this.wallRaw.dispose();
            if(this.wallBmp != null && this.wallBmp.parent) this.wallBmp.parent.removeChild(this.wallBmp);
            this.wallRaw = new BitmapData(cw,ch,true,0xFF000000);
            this.wallBmp = new Bitmap(this.wallRaw,"auto",true);
            this.wallBmp.scaleX = Tile.tileX;
            this.wallBmp.scaleY = Tile.tileY;
            this.wallBmp.x = -Tile.tileX / 2;
            this.wallBmp.y = -Tile.tileY / 2 - Tile.tileY;
            this.fogVis.addChild(this.wallBmp);
         }
         if(this.wallClip == null)
         {
            this.wallClip = new Shape();
            this.floorClip = new Shape();
            this.fogVis.addChild(this.wallClip);
            this.fogVis.addChild(this.floorClip);
         }
         // 两模式的地板都输出到5px工作图；classic的原版1px场只作合成输入。
         if(this.fogBitmap != null)
         {
            this.fogBitmap.visible = true;
         }
         // 两张图按互补范围替换，绝不叠加：墙=原版原尺寸场，地板=各模式雾效。
         if(this.fogBitmap.mask != this.floorClip) this.fogBitmap.mask = this.floorClip;
         if(this.wallLayer == null)
         {
            this.wallLayer = new Sprite();
            this.fogVis.addChild(this.wallLayer);
         }
         if(this.wallBmp.parent != this.wallLayer) this.wallLayer.addChild(this.wallBmp);
         if(this.classicWallShadeBmp.parent != this.wallLayer) this.wallLayer.addChild(this.classicWallShadeBmp);
         this.classicWallShadeBmp.visible = this.cfgMode == "classic";
         this.wallBmp.mask = null;
         if(this.wallLayer.mask != this.wallClip) this.wallLayer.mask = this.wallClip;
         // Keep the native infrared fog transform separate from the bright surface.
         if(this.fogShadow == null)
         {
            this.fogShadow = new Sprite();
            this.fogShadow.mouseEnabled = this.fogShadow.mouseChildren = false;
            this.fogVis.addChild(this.fogShadow);
         }
         if(this.fogBase == null)
         {
            this.fogBase = new Sprite();
            this.fogBase.mouseEnabled = this.fogBase.mouseChildren = false;
            this.fogShadow.addChild(this.fogBase);
         }
         for each(var fogChild:DisplayObject in [this.fogBitmap,this.wallLayer,this.wallClip,this.floorClip])
            if(fogChild.parent != this.fogBase) this.fogBase.addChild(fogChild);
         var visual:Sprite = w.grafon.visual;
         if(this.fogVis.parent != visual)
         {
            var vi:int = visual.getChildIndex(w.grafon.visLight);
            visual.addChildAt(this.fogVis,vi + 1);
         }
         // Cropping the display also bounds AIR's masked-surface composition.
         // scrollRect translates its content; restore the same world-space origin.
         if(this.spaceX > 48 || this.spaceY > 25)
         {
            var sceneView:Rectangle = this.scenePaintBounds();
            sceneView.x *= Tile.tileX; sceneView.y *= Tile.tileY;
            sceneView.width *= Tile.tileX; sceneView.height *= Tile.tileY;
            this.fogVis.scrollRect = sceneView;
            this.fogVis.x = sceneView.x; this.fogVis.y = sceneView.y;
         }
         else
         {
            this.fogVis.scrollRect = null;
            this.fogVis.x = this.fogVis.y = 0;
         }
         this.fogShadow.scrollRect = this.fogVis.scrollRect;
         this.fogShadow.x = this.fogVis.x; this.fogShadow.y = this.fogVis.y;
         this.fogVis.visible = true;
         if(w.pers != null && (w.pers as Pers).infravis > 0)
         {
            this.fogShadow.transform.colorTransform = this.infraCT;
            this.fogShadow.blendMode = "multiply";
         }
         else
         {
            this.fogShadow.transform.colorTransform = this.defCT;
            this.fogShadow.blendMode = "normal";
         }
      }

      /** 透传模式（原版）：停用模组雾层，visi/visLight/lightBmp 完全交还游戏。
       *  进入透传瞬间用 setLight() 把掩膜恢复到当前 visi 状态（模式切换后
       *  lightBmp 可能残留模组活动期的旧值；房间进入时 drawLoc 已调过，
       *  重复调用无害）。 */
      private function normalMode(w:World, loc:Location):void
      {
         if(this.fogVis != null)
         {
            this.fogVis.visible = false;
         }
         if(!this.normalApplied)
         {
            this.normalApplied = true;
            if(w.grafon != null)
            {
               try
               {
                  w.grafon.setLight();
                  w.grafon.visLight.visible = loc.black && w.black;
               }
               catch(err:Error)
               {
               }
            }
         }
      }

      /** 透传路径（vanilla / 总开关关 / 安全基地）恢复全部残留（v0.24.6）：
       *  ① 摘除全部掩膜（含残留在显示树中的掩膜 Shape，过期掩膜会继续裁剪
       *     单位 → 原版"隐身敌人"）；② 恢复被隐藏单位的 vis/prior/hpbar；
       *  ③ 恢复敌方武器（visible + 摘 mask + 关 cacheAsBitmap）；④ 恢复
       *  显示树中被隐藏的附属对象（狮鹫手臂等）。门控：无残留时零开销。 */
      private function restoreAll(w:World, loc:Location):void
      {
         this.classicRenderedTiles=null;
         this.classicCells=null;
         this.restoreWorldVisuals();
         this.restoreWeaponVisuals();
         var any:Boolean = false;
         for(var k:Object in this.unitVis) { any = true; break; }
         if(!any)
         {
            for(var kh:Object in this.hpHidden) { any = true; break; }
         }
         if(!any)
         {
            for(var km:Object in this.managedHidden) { any = true; break; }
         }
         if(!any)
         {
            return;
         }
         for(var ku:Object in this.unitVis)
         {
            var u:Unit = ku as Unit;
            if(u != null)
            {
               this.clearMask(u);
            }
         }
         this.unitVis = new Dictionary(true);
         for(var khu:Object in this.hpHidden)
         {
            var uh:Unit = khu as Unit;
            if(uh != null)
            {
               this.showUnit(uh);
            }
         }
         this.hpHidden = new Dictionary(true);
         var obj:Pt = loc.firstObj;
         var guard:int = 0;
         while(obj != null && guard < 5000)
         {
            if(obj is Weapon)
            {
               this.setWeaponVis(obj as Weapon,true);
            }
            obj = obj.nobj;
            guard++;
         }
         for(var md:Object in this.managedHidden)
         {
            var c:DisplayObject = md as DisplayObject;
            if(c != null)
            {
               c.visible = true;
            }
         }
         this.managedHidden = new Dictionary(true);
         this.managedCount = 0;
      }

      /** 阻挡结构哈希：opac>0 / phis>0 逐瓦片累计（用于墙破坏/开门/关门的即时检测）。 */
      private function structHash(loc:Location):int
      {
         var h:int = 0;
         var tx:int;
         var ty:int;
         for(tx = 0; tx < this.spaceX; tx++)
         {
            for(ty = 0; ty < this.spaceY; ty++)
            {
               var t:Tile = loc.getTile(tx,ty);
               h = h * 31 + (t.opac > 0 ? 1 : 0) + (t.phis > 0 ? 2 : 0);
            }
         }
         return h;
      }

      /** 悬停在不可见敌人上时清除 celObj（杀名称标签，与游戏 getDist 同机制）。 */
      private function blockInvisibleHover(loc:Location, gg:UnitPlayer):void
      {
         var co:Object = loc.celObj;
         if(co == null || !(co is Unit))
         {
            return;
         }
         var cu:Unit = co as Unit;
         if(cu.player || cu.npc || cu.fraction == Unit.F_PLAYER)
         {
            return;
         }
         if(this.enemyState(loc,cu) == 0)
         {
            loc.celObj = null;
         }
      }

      // ==================== FOV ====================

      /** 比较实际遮光值；部分门和水变化也立即使视野失效。 */
      // ContinuousScene exact full-field fast paths (no temporal or viewport culling).
      private function scenePrepareOcclusionFast(loc:Location, space:Array, changed:Boolean):Boolean
      {
         var width:int = this.spaceX;
         var height:int = this.spaceY;
         var ray:Vector.<Number> = this.rayOpac;
         var raw:Vector.<Number> = this.tileOpacity;
         var topology:Vector.<Boolean> = this.wallTopology;
         var waterOpacity:Number = loc.opacWater;
         // Native getTile(x,y) is exactly space[x][y] for these in-bounds cells.
         // Re-read columns and Tiles each call so replacement/door/water changes
         // remain visible immediately, including changes outside the camera.
         for(var x:int = 0; x < width; ++x)
         {
            var column:Array = space[x] as Array;
            var index:int = x;
            for(var y:int = 0; y < height; ++y, index += width)
            {
               var tile:Tile = column[y] as Tile;
               var tileOpacity:Number = tile.opac;
               var opacity:Number = tileOpacity;
               if(waterOpacity > 0 && tile.water > 0 && waterOpacity > opacity)
                  opacity = waterOpacity;
               var solid:Boolean = tileOpacity >= 1;
               if(ray[index] !== opacity) { ray[index] = opacity; changed = true; }
               if(raw[index] !== tileOpacity) { raw[index] = tileOpacity; changed = true; }
               if(topology[index] != solid)
               {
                  topology[index] = solid;
                  this.wallGeometryDirty = true;
                  changed = true;
               }
            }
         }
         return changed;
      }

      private function sceneRefreshWallFieldFast(loc:Location, space:Array, changed:Boolean, advance:Boolean):Boolean
      {
         var width:int = this.spaceX;
         var corners:Array = this.wallCorners;
         var alpha:Array = this.wallA;
         var memory:Array = this.memCur;
         var sight:Array = this.fov;
         var shared:Array = this.sharedLight;
         var bitmap:BitmapData = this.wallRaw;
         var retDark:Boolean = loc.retDark;
         var fade:Number = this.cfgFadeStep;
         var dim:Number = this.cfgDim;
         // Preserve the original corner order and every advanceMemory write.
         // These are scalar reads of native public fields, with no callbacks.
         for each(var index:int in corners)
         {
            var x:int = index % width;
            var y:int = int(index / width);
            var cur:Number = memory[index];
            if(advance)
            {
               var target:Number = !retDark && sight[index] == FOV_NONE ? 1 : 0;
               if(cur < target) cur = Math.min(target,cur + fade);
               else if(cur > target) cur = Math.max(target,cur - fade);
               memory[index] = cur;
            }
            var light:Number = 0;
            if(x != 0 && y != 0)
            {
               var tile:Tile = space[x][y] as Tile;
               light = Math.max(0,Math.min(1,tile.visi));
               if(this.cfgViewScale != 1 && this.rangeRoom === loc && this.rangeLight != null)
                  light = Math.max(light,Number(this.rangeLight[index]) || 0);
               if(!retDark && shared != null)
                  light = Math.max(light,Number(shared[index]));
            }
            var gameA:int = Math.floor((1-light)*255);
            var a:int = Math.round(255 - (255-gameA)*(1-cur+cur*dim));
            if(alpha[index] !== a)
            {
               changed = true;
               alpha[index] = a;
               bitmap.setPixel32(x,y+1,a << 24);
            }
         }
         return changed;
      }

      private function prepareOcclusion(loc:Location):Boolean
      {
         var fresh:Boolean = this.rayLoc !== loc || this.rayWidth != this.spaceX || this.rayHeight != this.spaceY;
         var changed:Boolean = fresh;
         if(fresh)
         {
            this.rayLoc = loc; this.rayWidth = this.spaceX; this.rayHeight = this.spaceY;
            this.rayOpac = new Vector.<Number>(this.spaceX*this.spaceY,true);
            this.tileOpacity = new Vector.<Number>(this.spaceX*this.spaceY,true);
            this.wallTopology = new Vector.<Boolean>(this.spaceX*this.spaceY,true);
            this.wallGeometryDirty = true;
         }
         if(this.cfgMode == "current" && (this.spaceX > 48 || this.spaceY > 25))
         {
            // Object access avoids expanding the external game API stub.
            var sceneSpace:Array = Object(loc).space as Array;
            if(sceneSpace != null && loc.spaceX == this.spaceX && loc.spaceY == this.spaceY)
               return this.scenePrepareOcclusionFast(loc,sceneSpace,changed);
         }
         for(var y:int=0;y<this.spaceY;y++) for(var x:int=0;x<this.spaceX;x++)
         {
            var i:int=x+y*this.spaceX;
            var tile:Tile=loc.getTile(x,y);
            var opacity:Number=this.tileOpac(loc,tile);
            var solid:Boolean=tile.opac>=1;
            if(this.rayOpac[i]!==opacity) { this.rayOpac[i]=opacity; changed=true; }
            if(this.tileOpacity[i]!==tile.opac) { this.tileOpacity[i]=tile.opac; changed=true; }
            if(this.wallTopology[i]!=solid)
            {
               this.wallTopology[i]=solid; this.wallGeometryDirty=true; changed=true;
            }
         }
         return changed;
      }

      private function computeFov(loc:Location, prepared:Boolean = false):void
      {
         if(this.cfgMode == "current" && !prepared) this.prepareOcclusion(loc);
         this.rayBatch = this.cfgMode == "current";
         try
         {
            var gg:UnitPlayer = loc.gg;
            var ex:Number = gg.X;
            var ey:Number = gg.Y - gg.scY * 0.75;
            this.eyeX = ex;
            this.eyeY = ey;
            this.updateViewDistances(loc);
            this.updateRangeLight(loc);
            var r:Number = this.cfgViewScale == 1 ? loc.lDist2 : this.locDist2;
            if(r < Tile.tileX)
            {
               r = Tile.tileX;
            }
            var r2:Number = r * r;
            var fx0:int=Math.max(0,Math.floor((ex-r)/Tile.tileX-0.5));
            var fy0:int=Math.max(0,Math.floor((ey-r)/Tile.tileY-0.5));
            var fx1:int=Math.min(this.spaceX,Math.ceil((ex+r)/Tile.tileX+0.5));
            var fy1:int=Math.min(this.spaceY,Math.ceil((ey+r)/Tile.tileY+0.5));
            for(var clearIndex:int=0;clearIndex<this.spaceX*this.spaceY;clearIndex++)this.fov[clearIndex]=FOV_NONE;
            var tx:int;
            var ty:int;
            for(tx = fx0; tx < fx1; tx++)
            {
               for(ty = fy0; ty < fy1; ty++)
               {
                  var i:int = tx + ty * this.spaceX;
                  var cx:Number = (tx + 0.5) * Tile.tileX;
                  var cy:Number = (ty + 0.5) * Tile.tileY;
                  var dx:Number = cx - ex;
                  var dy:Number = cy - ey;
                  if(dx * dx + dy * dy > r2)
                  {
                     this.fov[i] = FOV_NONE;
                     continue;
                  }
                  var lit:Number = this.castRay(loc,ex,ey,cx,cy,tx,ty);
                  // 连续亮度（原版渐变）：LOS 亮度 × 距离衰减
                  var distF:Number = this.distFalloff(dx * dx + dy * dy);
                  var b:Number = lit < 0 ? 0 : lit * distF;
                  if(b > 1)
                  {
                     b = 1;
                  }
                  this.br[i] = b;
                  this.litArr[i] = lit < 0 ? 0 : (lit > 1 ? 1 : lit);
                  if(lit >= this.cfgLitMin)
                  {
                     this.fov[i] = FOV_VISIBLE;
                     this.explored[i] = 1;
                  }
                  else if(lit > 0.0001)
                  {
                     this.fov[i] = FOV_DIM;
                     this.explored[i] = 1;
                  }
                  else
                  {
                     this.fov[i] = FOV_NONE;
                  }
               }
            }
            // Only an immediate neighbour of a visible non-wall can be lit.
            fx0=Math.max(0,fx0-1);fy0=Math.max(0,fy0-1);
            fx1=Math.min(this.spaceX,fx1+1);fy1=Math.min(this.spaceY,fy1+1);
            // 墙可见性：只由"可见的非阻挡瓦片"点亮，不链式传播（厚墙内部保持暗）
            for(tx = fx0; tx < fx1; tx++)
            {
               for(ty = fy0; ty < fy1; ty++)
               {
                  var j:int = tx + ty * this.spaceX;
                  if(this.fov[j] == FOV_VISIBLE)
                  {
                     continue;
                  }
                  var t:Tile = loc.getTile(tx,ty);
                  if(t.opac <= 0)
                  {
                     continue;
                  }
                  for each(var nb:Array in WALL_NEIGHBORS)
                  {
                     var nx:int = tx + nb[0];
                     var ny:int = ty + nb[1];
                     if(nx >= 0 && nx < this.spaceX && ny >= 0 && ny < this.spaceY)
                     {
                        var ni:int = nx + ny * this.spaceX;
                        if(this.fov[ni] == FOV_VISIBLE && loc.getTile(nx,ny).opac <= 0)
                        {
                           this.fov[j] = FOV_VISIBLE;
                           this.explored[j] = 1;
                           // 墙瓦片按距离衰减取连续亮度（墙的亮面随光缘渐变）
                           var wdx:Number = (tx + 0.5) * Tile.tileX - ex;
                           var wdy:Number = (ty + 0.5) * Tile.tileY - ey;
                           this.br[j] = this.distFalloff(wdx * wdx + wdy * wdy);
                           this.litArr[j] = 1;
                           break;
                        }
                     }
                  }
               }
            }
         }
         finally { this.rayBatch = false; }
      }

   private function castRay(loc:Location, ex:Number, ey:Number, cx:Number, cy:Number, tx:int, ty:int):Number
      {
         var lit:Number = 1;
         var leaked:Boolean = false;
         var dx:Number = cx - ex;
         var dy:Number = cy - ey;
         var c0x:int = Math.floor(ex / Tile.tileX);
         var c0y:int = Math.floor(ey / Tile.tileY);
         var cached:Boolean = this.rayBatch && this.rayLoc === loc
            && c0x>=0 && c0y>=0 && c0x<this.rayWidth && c0y<this.rayHeight
            && tx>=0 && ty>=0 && tx<this.rayWidth && ty<this.rayHeight;
         var stepX:int;
         var stepY:int;
         var tMaxX:Number;
         var tMaxY:Number;
         var tDeltaX:Number;
         var tDeltaY:Number;
         if(dx > 0)
         {
            stepX = 1;
            tMaxX = ((c0x + 1) * Tile.tileX - ex) / dx;
            tDeltaX = Tile.tileX / dx;
         }
         else if(dx < 0)
         {
            stepX = -1;
            tMaxX = (c0x * Tile.tileX - ex) / dx;
            tDeltaX = -Tile.tileX / dx;
         }
         else
         {
            stepX = 0;
            tMaxX = Number.POSITIVE_INFINITY;
            tDeltaX = 0;
         }
         if(dy > 0)
         {
            stepY = 1;
            tMaxY = ((c0y + 1) * Tile.tileY - ey) / dy;
            tDeltaY = Tile.tileY / dy;
         }
         else if(dy < 0)
         {
            stepY = -1;
            tMaxY = (c0y * Tile.tileY - ey) / dy;
            tDeltaY = -Tile.tileY / dy;
         }
         else
         {
            stepY = 0;
            tMaxY = Number.POSITIVE_INFINITY;
            tDeltaY = 0;
         }
         var c1x:int = c0x;
         var c1y:int = c0y;
         var guard:int = 0;
         var op:Number;
         while(c1x != tx || c1y != ty)
         {
            if(++guard > 400)
            {
               break;
            }
            if(tMaxX < tMaxY)
            {
               tMaxX += tDeltaX;
               c1x += stepX;
            }
            else
            {
               tMaxY += tDeltaY;
               c1y += stepY;
            }
            op = cached ? this.rayOpac[c1x+c1y*this.rayWidth] : this.tileOpac(loc,loc.getTile(c1x,c1y));
            // 全实心（墙/金属门）→ 完全阻挡；部分透光（木门/栅格/水）→ 泄漏暗色视野
            if(op >= 1)
            {
               return -1;
            }
            if(op > 0)
            {
               leaked = true;
            }
            lit -= op;
         }
         op = cached ? this.rayOpac[tx+ty*this.rayWidth] : this.tileOpac(loc,loc.getTile(tx,ty));
         if(op >= 1)
         {
            return -1;
         }
         if(op > 0)
         {
            leaked = true;
         }
         lit -= op;
         if(lit < 0)
         {
            lit = 0;
         }
         if(lit > 1)
         {
            lit = 1;
         }
         // 多层部分透光叠加（斜穿双格宽木门等）仍提供暗色视野
         if(leaked && lit < 0.0001)
         {
            return 0.05;
         }
         return lit;
      }

      private function tileOpac(loc:Location, t:Tile):Number
      {
         var op:Number = t.opac;
         if(loc.opacWater > 0 && t.water > 0 && loc.opacWater > op)
         {
            op = loc.opacWater;
         }
         return op;
      }

      /** current 地板软雾；原版亮度只读，墙面独立更新。 */
      /**
       * current（真实线状 + 渐变过渡）：阴影边界由光线几何产生——对已探索瓦片
       * 的每个子格（5px）中心独立 castRay，亮度 = max(lit × 距离衰减, 记忆暗色)。
       * 边界瓦片内部不同子格光线路径不同 → 线状阴影；随后施加模糊
       * （5px 子格，4/q3 滤镜）得到地板软边，不回写探索或墙场。
       *
       * 性能（v0.17.1）：最终 alpha 场缓存在 fogCache，只在 FOV 重算时更新；
       * 重算时每瓦片先做 4 角采样分类——全暗（记忆区）整块 fillRect、全亮
       * （视野内）无 raycast 只算距离衰减、只有边界/泄漏瓦片（角点明暗混合或
       * FOV_DIM）才做完整 8×8 raycast。站立时（淡入帧）零 raycast。
       */
      /** Large scenes keep native FOV/AI coordinates. Only the visible fog pixels
       * are repainted; the margin covers blur and camera interpolation. Small rooms
       * retain their complete original paint extent. */
      private function scenePaintBounds():Rectangle
      {
         if(this.spaceX <= 48 && this.spaceY <= 25) return new Rectangle(0,0,this.spaceX,this.spaceY);
         var world:* = World.w;
         var camera:* = world.cam;
         var scale:Number = camera.scaleV > 0 ? camera.scaleV : 1;
         var left:int = Math.max(0,Math.floor(-camera.vx / scale / Tile.tileX) - 4);
         var top:int = Math.max(0,Math.floor(-camera.vy / scale / Tile.tileY) - 4);
         var right:int = Math.min(this.spaceX,Math.ceil((-camera.vx + camera.screenX) / scale / Tile.tileX) + 4);
         var bottom:int = Math.min(this.spaceY,Math.ceil((-camera.vy + camera.screenY) / scale / Tile.tileY) + 4);
         return new Rectangle(left,top,right-left,bottom-top);
      }

      private function applyVision(w:World, loc:Location, needFov:Boolean, occlusionPrepared:Boolean = false):void
      {
         var sceneBounds:Rectangle = this.scenePaintBounds();
         this.ensureFog(w);
         var sceneLarge:Boolean = this.spaceX > 48 || this.spaceY > 25;
         var sceneViewChanged:Boolean = sceneLarge && (this.scenePaintLoc !== loc || this.sceneLastPaintBounds == null || !this.sceneLastPaintBounds.equals(sceneBounds));
         if(sceneLarge)
         {
            this.scenePaintLoc = loc; this.sceneLastPaintBounds = sceneBounds;
            if(sceneViewChanged)
            {
               this.fogDirty = true; this.fogBlurPending = true;
               if(!needFov) ++this.fovVersion;
            }
         }
         var scenePixelBounds:Rectangle = sceneLarge ? new Rectangle(FOG_PAD + sceneBounds.x * FOG_SUB,
            FOG_PAD + sceneBounds.y * FOG_SUB,sceneBounds.width * FOG_SUB,sceneBounds.height * FOG_SUB) : this.fogRect;
         var scenePixelPoint:Point = sceneLarge ? new Point(scenePixelBounds.x,scenePixelBounds.y) : this.fogPoint;
         // 原版 lighting2 在站立时仍可更新角值；墙场不能只等玩家移动。
         if(needFov && !occlusionPrepared) this.prepareOcclusion(loc);
         if(this.currentSight == null || this.currentSight.width != this.fogCache.width || this.currentSight.height != this.fogCache.height)
         {
            if(this.currentSight != null) this.currentSight.dispose();
            this.currentSight = new BitmapData(this.fogCache.width,this.fogCache.height,true,0);
            this.currentSightWritten = null;
         }
         var wallChanged:Boolean = this.refreshWallField(loc,this.wallGeometryDirty);
         this.wallGeometryDirty = false;
         if(wallChanged && !needFov && !sceneViewChanged)
         {
            var maskChanged:Boolean = false;
            // Static native lighting can rewrite wall samples outside the view.
            this.currentSightWritten = null;
            for each(var wi:int in this.wallTiles)
            {
               if(this.fillWallTile(wi % this.spaceX,int(wi / this.spaceX),true)) maskChanged = true;
            }
            // 部分单位掩膜按此版本缓存；只在墙采样跨可见阈值时失效。
            if(maskChanged) this.fovVersion++;
            this.currentSightData = sceneLarge ? null : this.currentSight.getVector(this.currentSight.rect);
         }
         // 墙图随角值独立更新；不因远处地板的记忆渐变重跑整图模糊。
         // 重算和淡入均当帧显示；无变化时跳过地板绘制。
         if(this.fogBmp == null || (!this.fogDirty && !this.fogBlurPending))
         {
            return;
         }
         if(w.grafon != null)
         {
            w.grafon.visLight.visible = false;
         }
         if(needFov || sceneViewChanged)
         {
            this.fillFogCache(loc);
            this.currentSightData = sceneLarge ? null : this.currentSight.getVector(this.currentSight.rect);
            this.fogBlurPending = true;
            if(this.cfgAutoTest)
            {
               this.atBlurD++;
            }
         }
         var changed:Boolean = false;
         var fading:Boolean = false;
         var tx:int;
         var ty:int;
         if(this.fogDirty)
         {
            for(tx = int(sceneBounds.left); tx < sceneBounds.right; tx++)
            {
               for(ty = int(sceneBounds.top); ty < sceneBounds.bottom; ty++)
               {
                  var i:int = tx + ty * this.spaceX;
                  // 淡入进度（进房/开关时 0→1；收敛后子格值即最终亮度）
                  var cur:Number = this.visCur[i];
                  if(cur < 1)
                  {
                     cur += this.cfgFadeStep;
                     if(cur > 1)
                     {
                        cur = 1;
                     }
                     this.visCur[i] = cur;
                     changed = true;
                     if(cur < 1)
                     {
                        fading = true;
                     }
                  }
               }
            }
            if(fading)
            {
               // 淡入帧：fogRaw = 按每瓦片 cur 缩放缓存场（alpha = 255 - cur×(255-cacheA)）
               this.fogRaw.lock();
               for(tx = int(sceneBounds.left); tx < sceneBounds.right; tx++)
               {
                  for(ty = int(sceneBounds.top); ty < sceneBounds.bottom; ty++)
                  {
                     var cf:Number = this.visCur[tx + ty * this.spaceX];
                     var px0:int = FOG_PAD + tx * FOG_SUB;
                     var py0:int = FOG_PAD + ty * FOG_SUB;
                     if(cf >= 1)
                     {
                        this.fogCellRect.x = px0;
                        this.fogCellRect.y = py0;
                        this.fogCellPoint.x = px0;
                        this.fogCellPoint.y = py0;
                        this.fogRaw.copyPixels(this.fogCache,this.fogCellRect,this.fogCellPoint);
                     }
                     else
                     {
                        var sx:int;
                        var sy:int;
                        for(sx = 0; sx < FOG_SUB; sx++)
                        {
                           for(sy = 0; sy < FOG_SUB; sy++)
                           {
                              var ca:int = this.fogCache.getPixel32(px0 + sx,py0 + sy) >>> 24;
                              var a:int = 255 - cf * (255 - ca);
                              if(a < 0)
                              {
                                 a = 0;
                              }
                              else if(a > 255)
                              {
                                 a = 255;
                              }
                              this.fogRaw.setPixel32(px0 + sx,py0 + sy,a << 24);
                           }
                        }
                     }
                  }
               }
               this.fogRaw.unlock();
            }
            else
            {
               // 收敛后：缓存场直接拷贝（无逐像素循环）
               this.fogRaw.copyPixels(this.fogCache,scenePixelBounds,scenePixelPoint);
            }
         }
         if(this.fogBlurPending || this.fogDirty)
         {
            // 模糊 → 阴影边缘渐变过渡（source≠dest）
            this.fogBmp.applyFilter(this.fogRaw,scenePixelBounds,scenePixelPoint,this.curBlur);
            // 仅地板使用连续显示场；墙裁切与 currentSight 独立保护墙内和单位遮挡。
            this.fogBlurPending = false;
         }
         if(!changed)
         {
            this.fogDirty = false;
         }
      }

      /** current：最终 alpha 场写入 fogCache（仅 FOV 重算时调用）。 */
      private function fillFogCache(loc:Location):void
      {
         var sceneBounds:Rectangle = this.scenePaintBounds();
         this.rayBatch = true;
         // Every write in this pass lies in sceneBounds. Clear the previous
         // write extent, including camera jumps; all other pixels remain zero.
         // Room/allocation/static-wall changes invalidate the extent above.
         this.currentSight.fillRect(this.currentSightWritten==null?this.currentSight.rect:this.currentSightWritten,0);
         this.currentSightWritten=new Rectangle(FOG_PAD+sceneBounds.x*FOG_SUB,FOG_PAD+sceneBounds.y*FOG_SUB,
            sceneBounds.width*FOG_SUB,sceneBounds.height*FOG_SUB);
         try
         {
            var dimF:Number = this.cfgDim;
            var dimA:int = Math.round((1 - dimF) * 255);
            var doorF:Number = this.cfgDoorDim;
            var d2max:Number = this.locDist2 * this.locDist2;
            var cs:Number = Tile.tileX / FOG_SUB;
            this.fogCache.lock();
            var tx:int;
            var ty:int;
            for(tx = int(sceneBounds.left); tx < sceneBounds.right; tx++)
            {
               for(ty = int(sceneBounds.top); ty < sceneBounds.bottom; ty++)
               {
                  var i:int = tx + ty * this.spaceX;
                  var bx:Number = tx * Tile.tileX;
                  var by:Number = ty * Tile.tileY;
                  var f:int = this.fov[i];
                  var t:Tile = loc.getTile(tx,ty);
                  if(t.opac >= 1)
                  {
                     // 包括未见/记忆墙：黑芯与弱光不能落入地板的 dim 下限分支。
                     this.fillWallTile(tx,ty);
                     continue;
                  }
                  if(f == FOV_DIM)
                  {
                     // 透光门/水后：门景亮度（doordim，比记忆暗色亮），逐子格重算
                     this.recalcTile(loc,tx,ty,bx,by,doorF,dimA,cs,true);
                     continue;
                  }
                  // 4 角采样分类：全暗→记忆区/未探索整块；全亮→无 raycast 距离衰减；
                  // 明暗混合→边界瓦片完整 8×8 重算（线状阴影由这些瓦片产生）
                  var cLit:int = 0;
                  var sx:int;
                  var sy:int;
                  for(sx = 0; sx < 2; sx++)
                  {
                     for(sy = 0; sy < 2; sy++)
                     {
                        var subX:Number = bx + CORNER_OFFS_X[sx] * cs;
                        var subY:Number = by + CORNER_OFFS_Y[sy] * cs;
                        var dx:Number = subX - this.eyeX;
                        var dy:Number = subY - this.eyeY;
                        var lit:Number = dx * dx + dy * dy <= d2max
                           ? this.castRay(loc,this.eyeX,this.eyeY,subX,subY,
                              Math.floor(subX / Tile.tileX),Math.floor(subY / Tile.tileY))
                           : -1;
                        if(lit > 0.0001)
                        {
                           cLit++;
                           // 可见角 → 子格"曾见"历史（记忆区↔未探索边界 5px 粒度；
                           // 已探索瓦片同样标记，否则记忆区填充会出黑斑）
                           this.seenSub[(ty * FOG_SUB + (sy == 0 ? 0 : FOG_SUB-1)) * this.subW + (tx * FOG_SUB + (sx == 0 ? 0 : FOG_SUB-1))] = 1;
                           this.explorationBits[tx + ty * this.spaceX] = null;this.memoryTileState[tx+ty*this.spaceX]=null;
                        }
                     }
                  }
                  if(f == FOV_VISIBLE && cLit == 4)
                  {
                     // 全亮瓦片：无 raycast，逐子格距离衰减（含记忆暗色下限）
                     this.fillLitTile(tx,ty,bx,by,dimF,cs);
                  }
                  else if(cLit == 0)
                  {
                     // 全暗瓦片（记忆区/未探索）：按子格"曾见"历史填充——曾见→记忆
                     // 暗色，从未见→黑。已探索瓦片不再整块 166（v0.17.4 回归的
                     // 40px 阶梯）：记忆区边界由子格历史形状决定（5px 粒度）
                     this.fillMemoryTile(tx,ty,dimA);
                  }
                  else
                  {
                     // 边界瓦片（含阴影线/泄漏/曾见边缘）：完整 8×8 raycast
                     this.recalcTile(loc,tx,ty,bx,by,dimF,dimA,cs,false);
                  }
               }
            }
         }
         finally { this.fogCache.unlock(); this.rayBatch = false; }
      }

      /**
       * 边界瓦片完整 8×8 子格 raycast。
       * doorView=true：透光门/水后——所有子格用门景亮度（floor=doordim）；
       * 否则：亮子格 max(lit×falloff, floor)，暗子格=曾见→记忆暗色，否则黑。
       * 当前可见子格一律记入"曾见"历史（含 doorView 与已探索瓦片——记忆区
       * 填充按子格历史，漏标会出现黑斑）。
       */
      private function recalcTile(loc:Location, tx:int, ty:int, bx:Number, by:Number,
         floorF:Number, dimA:int, cs:Number, doorView:Boolean):void
      {
         var sx:int;
         var sy:int;
         for(sx = 0; sx < FOG_SUB; sx++)
         {
            for(sy = 0; sy < FOG_SUB; sy++)
            {
               var subX:Number = bx + (sx + 0.5) * cs;
               var subY:Number = by + (sy + 0.5) * cs;
               var sdx:Number = subX - this.eyeX;
               var sdy:Number = subY - this.eyeY;
               var lit:Number = this.castRay(loc,this.eyeX,this.eyeY,subX,subY,
                  Math.floor(subX / Tile.tileX),Math.floor(subY / Tile.tileY));
               if(lit < 0)
               {
                  lit = 0;
               }
               else if(lit > 1)
               {
                  lit = 1;
               }
               if(lit > 0.0001)
               {
                  this.seenSub[(ty * FOG_SUB + sy) * this.subW + (tx * FOG_SUB + sx)] = 1;
                  this.explorationBits[tx + ty * this.spaceX] = null;this.memoryTileState[tx+ty*this.spaceX]=null;
               }
               var a:int;
               if(doorView)
               {
                  var br:Number = lit * this.distFalloff(sdx * sdx + sdy * sdy);
                  var logicalBrightness:Number=br;
                  if(br < floorF)
                  {
                     br = floorF;
                  }
                  a = Math.round((1 - br) * 255);
               }
               else if(lit > 0.0001)
               {
                  br = lit * this.distFalloff(sdx * sdx + sdy * sdy);
                  logicalBrightness=br;
                  if(br < floorF)
                  {
                     br = floorF;
                  }
                  a = Math.round((1 - br) * 255);
               }
               else if(this.memorySeen((ty * FOG_SUB + sy) * this.subW + (tx * FOG_SUB + sx)))
               {
                  a = dimA;
               }
               else
               {
                  a = 255;
               }
               this.fogCache.setPixel32(FOG_PAD + tx * FOG_SUB + sx,FOG_PAD + ty * FOG_SUB + sy,a << 24);
               if(lit > 0.0001)
               {
                  var logicalA:int=Math.round((1-Math.max(logicalBrightness,doorView?floorF:0.35))*255);
                  if(logicalA < MASK_LIT_A && sdx*sdx+sdy*sdy <= this.locDist2*this.locDist2)
                     this.currentSight.setPixel32(FOG_PAD+tx*FOG_SUB+sx,FOG_PAD+ty*FOG_SUB+sy,0xFFFFFFFF);
               }
            }
         }
      }

      /** current：全亮瓦片无 raycast 填充——逐子格距离衰减（亮度 = max(falloff, dim)）。
       *  4 角已确认全在视野半径内（角是瓦片最远点）→ 整瓦片记入"曾见"历史
       *  （记忆区按子格历史填充，漏标会出现黑斑）。 */
      private function fillLitTile(tx:int, ty:int, bx:Number, by:Number, dimF:Number, cs:Number):void
      {
         var idxBase:int = ty * FOG_SUB * this.subW + tx * FOG_SUB;
         var tileIndex:int = tx+ty*this.spaceX;
         var sx:int;
         var sy:int;
         if(!this.fullySeen[tileIndex])
         {
            for(sx = 0; sx < FOG_SUB; sx++)
            {
               for(sy = 0; sy < FOG_SUB; sy++)
               {
                  this.seenSub[idxBase + sy * this.subW + sx] = 1;
               }
            }
            this.fullySeen[tileIndex] = true;
         }
         var farX:Number = Math.max(Math.abs(bx+0.5*cs-this.eyeX),Math.abs(bx+(FOG_SUB-0.5)*cs-this.eyeX));
         var farY:Number = Math.max(Math.abs(by+0.5*cs-this.eyeY),Math.abs(by+(FOG_SUB-0.5)*cs-this.eyeY));
         if(farX*farX+farY*farY <= this.locDist1*this.locDist1)
         {
            this.fogCellRect.x=FOG_PAD+tx*FOG_SUB; this.fogCellRect.y=FOG_PAD+ty*FOG_SUB;
            this.fogCache.fillRect(this.fogCellRect,0);
            this.currentSight.fillRect(this.fogCellRect,0xFFFFFFFF);
            return;
         }
         for(sx = 0; sx < FOG_SUB; sx++)
         {
            for(sy = 0; sy < FOG_SUB; sy++)
            {
               var subX:Number = bx + (sx + 0.5) * cs;
               var subY:Number = by + (sy + 0.5) * cs;
               var dx:Number = subX - this.eyeX;
               var dy:Number = subY - this.eyeY;
               var f:Number = this.distFalloff(dx * dx + dy * dy);
               var logicalF:Number = f;
               if(f < dimF)
               {
                  f = dimF;
               }
               this.fogCache.setPixel32(FOG_PAD + tx * FOG_SUB + sx,FOG_PAD + ty * FOG_SUB + sy,
                  Math.round((1 - f) * 255) << 24);
               if(Math.round((1-Math.max(logicalF,0.35))*255)<MASK_LIT_A) this.currentSight.setPixel32(FOG_PAD+tx*FOG_SUB+sx,FOG_PAD+ty*FOG_SUB+sy,0xFFFFFFFF);
            }
         }
      }

      /** 原版格角光照与门景，只读游戏亮度；中心采样的记忆另行插值。 */
      private function tileFogAlpha(loc:Location, tx:int, ty:int):int
      {
         var i:int = tx + ty * this.spaceX;
         // Grafon.setLight/Location.lighting 均从 (1,1) 开始；第零行列恒黑。
         if(tx == 0 || ty == 0)
         {
            return 255;
         }
         var t:Tile = loc.getTile(tx,ty);
         var gv:Number = this.explorationLight(loc,tx,ty);
         // 门景仅改变显示值，不再把 visi/t_visi 永久抬高。
         if(t.opac < 1 && this.fov[i] == FOV_DIM)
         {
            gv = Math.max(gv,this.cfgDoorDim);
         }
         return Math.floor((1 - gv) * 255);
      }

      private function advanceMemory(loc:Location, i:int):Number
      {
         var target:Number = !loc.retDark && this.fov[i] == FOV_NONE ? 1 : 0;
         var cur:Number = this.memCur[i];
         if(cur < target) cur = Math.min(target,cur + this.cfgFadeStep);
         else if(cur > target) cur = Math.max(target,cur - this.cfgFadeStep);
         this.memCur[i] = cur;
         return cur;
      }

      /** 保留原版墙光照角点；current在此衰减，classic在中心遮挡层衰减。 */
      private function refreshWallField(loc:Location, rebuild:Boolean, advance:Boolean = true):Boolean
      {
         var n:int = this.spaceX * this.spaceY;
         var fresh:Boolean = this.wallA == null || this.wallA.length != n;
         if(fresh || rebuild)
         {
            this.wallTiles = [];
            this.wallCorners = [];
            this.wallA = new Array(n);
            this.wallRaw.fillRect(this.wallRaw.rect,0xFF000000);
            var used:Array = new Array(n);
            this.wallClip.graphics.clear();
            this.floorClip.graphics.clear();
            this.wallClip.graphics.beginFill(0xFFFFFF);
            this.floorClip.graphics.beginFill(0xFFFFFF);
            var tw:int = Tile.tileX;
            var th:int = Tile.tileY;
            // 雾图富余边框归地板层，继续保持原有的全黑边界。
            this.floorClip.graphics.drawRect(-2*tw,-2*th,(this.spaceX+4)*tw,2*th);
            this.floorClip.graphics.drawRect(-2*tw,this.spaceY*th,(this.spaceX+4)*tw,2*th);
            this.floorClip.graphics.drawRect(-2*tw,0,2*tw,this.spaceY*th);
            this.floorClip.graphics.drawRect(this.spaceX*tw,0,2*tw,this.spaceY*th);
            for(var y:int = 0; y < this.spaceY; y++)
            {
               var runStart:int = 0;
               var runWall:Boolean = loc.getTile(0,y).opac >= 1;
               for(var x:int = 0; x <= this.spaceX; x++)
               {
                  var wall:Boolean = x < this.spaceX && loc.getTile(x,y).opac >= 1;
                  if(x == this.spaceX || wall != runWall)
                  {
                     var clip:Shape = runWall ? this.wallClip : this.floorClip;
                     clip.graphics.drawRect(runStart*tw,y*th,(x-runStart)*tw,th);
                     runStart = x;
                     runWall = wall;
                  }
                  if(x == this.spaceX || !wall) continue;
                  this.wallTiles.push(x + y * this.spaceX);
                  for(var dy:int = 0; dy <= 1; dy++)
                  {
                     for(var dx:int = 0; dx <= 1; dx++)
                     {
                        if(x+dx >= this.spaceX || y+dy >= this.spaceY) continue;
                        var ci:int = x+dx + (y+dy)*this.spaceX;
                        if(!used[ci])
                        {
                           used[ci] = true;
                           this.wallCorners.push(ci);
                        }
                     }
                  }
               }
            }
            this.wallClip.graphics.endFill();
            this.floorClip.graphics.endFill();
         }
         var changed:Boolean = fresh || rebuild;
         if(this.cfgMode == "current" && (this.spaceX > 48 || this.spaceY > 25))
         {
            var sceneSpace:Array = Object(loc).space as Array;
            if(sceneSpace != null && loc.spaceX == this.spaceX && loc.spaceY == this.spaceY)
               return this.sceneRefreshWallFieldFast(loc,sceneSpace,changed,advance);
         }
         for each(var i:int in this.wallCorners)
         {
            var tx:int = i % this.spaceX;
            var ty:int = int(i / this.spaceX);
            if(advance) this.advanceMemory(loc,i);
            var gv:Number = tx == 0 || ty == 0 ? 0 : this.explorationLight(loc,tx,ty);
            var gameA:int = Math.floor((1-gv)*255);
            var cur:Number = this.memCur[i];
            // classic的记忆在中心坐标统一叠加；不能再在格角预先压暗一次。
            var a:int = this.cfgMode == "classic" ? gameA
               : Math.round(255 - (255-gameA)*(1-cur+cur*this.cfgDim));
            if(this.wallA[i] !== a)
            {
               changed = true;
               this.wallA[i] = a;
               this.wallRaw.setPixel32(tx,ty+1,a << 24);
            }
         }
         return changed;
      }

      /** Surface protection changes only the displayed fog, never enemy sight. */
      private function updateWallSurface(w:World, loc:Location):void
      {
         if(this.fogShadow == null) return;
         var self:RealisticVisionMod = this;
         var view:Rectangle = this.scenePaintBounds();
         if(!this.cfgWallBright && (this.spaceX > 48 || this.spaceY > 25) && view.width > 0 && view.height > 0)
         {
            // The ordinary paint bounds already include four offscreen tiles.
            // A further two-tile gutter retains wall geometry while the camera
            // moves inside it. Terrain, exploration and light still refresh on
            // every call; the actual fog and logical sight keep their old bounds.
            // Constant-bright compositing retains its exact original extent:
            // changing that extent can alter its intermediate raster rounding.
            if(this.wallViewOwner !== loc || this.wallViewBounds == null || !this.wallViewBounds.containsRect(view))
            {
               var left:int = Math.max(0,int(view.left)-2);
               var top:int = Math.max(0,int(view.top)-2);
               this.wallViewBounds = new Rectangle(left,top,
                  Math.min(this.spaceX,view.right+2)-left,Math.min(this.spaceY,view.bottom+2)-top);
               this.wallViewOwner = loc;
            }
            view = this.wallViewBounds;
         }
         var sceneCarrier:*=w.main.getChildByName("ContinuousSceneCarrier");
         var sceneNative:*=sceneCarrier!=null?sceneCarrier["nativeAPI"]:null;
         this.wallSurface.nativeTerrainSources=sceneNative!=null && "terrainSources" in sceneNative?sceneNative["terrainSources"] as Function:null;
         this.wallSurface.update(this.fogShadow,this.fogBase,w.grafon,loc,view,
            function(tx:int,ty:int):Boolean { return self.memoryExplored(tx+ty*self.spaceX); },
            function(tx:int,ty:int,wx:Number,wy:Number,dir:int):Number { return self.wallEdgeLight(tx,ty,wx,wy,dir); },
            this.cfgWallBright);
      }

      /** Read light from the open side, never from the wall-centre shadow.
       * This is display-only; no ray result is added to sight or exploration. */
      private function wallEdgeLight(tx:int, ty:int, wx:Number, wy:Number, dir:int):Number
      {
         var tile:Tile = this.curLoc.getTile(tx,ty);
         if(this.cfgMode == "current" && tile.opac < 1 && this.fogRaw != null)
         {
            if(dir == 0) wy -= 2.5;
            else if(dir == 1) wy += 2.5;
            else if(dir == 2) wx -= 2.5;
            else wx += 2.5;
            return 1 - (this.fogRaw.getPixel32(FOG_PAD+Math.floor(wx/5),FOG_PAD+Math.floor(wy/5)) >>> 24)/255;
         }
         var i:int = tx+ty*this.spaceX;
         var memory:Number = this.memCur[i];
         var nativeLight:Number = this.explorationLight(this.curLoc,tx,ty);
         if(tile.opac < 1 && this.fov[i] == FOV_DIM) nativeLight = Math.max(nativeLight,this.cfgDoorDim);
         return Math.max(0,Math.min(1,nativeLight*(1-memory)+this.cfgDim*memory));
      }

      private function wallCornerAlpha(tx:int, ty:int):Number
      {
         // 对齐原版位图的富余黑行/列，不用边界角向外无限延伸。
         if(tx >= this.spaceX || ty >= this.spaceY) return 255;
         return this.wallA[tx + ty * this.spaceX];
      }

      private function personalWallAlpha(tx:int, ty:int):Number
      {
         if(tx <= 0 || ty <= 0 || tx >= this.spaceX || ty >= this.spaceY) return 255;
         var gv:Number = Math.max(0,Math.min(1,this.curLoc.getTile(tx,ty).visi));
         if(this.cfgViewScale != 1 && this.rangeRoom === this.curLoc && this.rangeLight != null)
            gv=Math.max(gv,Number(this.rangeLight[tx+ty*this.spaceX]) || 0);
         var cur:Number = this.memCur[tx+ty*this.spaceX];
         return Math.round(255-gv*255*(1-cur+cur*0.35));
      }

      /** 每格四角连续双线性插值，坐标相位等价于原版 (-20,-60)+(x,y+1)。 */
      private function fillWallTile(tx:int, ty:int, trackMask:Boolean = false):Boolean
      {
         var maskChanged:Boolean = false;
         var a00:Number = this.wallCornerAlpha(tx,ty);
         var a10:Number = this.wallCornerAlpha(tx+1,ty);
         var a01:Number = this.wallCornerAlpha(tx,ty+1);
         var a11:Number = this.wallCornerAlpha(tx+1,ty+1);
         // Shared wall brightness is visual memory, never additional unit sight.
         var p00:Number = this.sharedLight == null && this.cfgDim == 0.35 ? a00 : this.personalWallAlpha(tx,ty);
         var p10:Number = this.sharedLight == null && this.cfgDim == 0.35 ? a10 : this.personalWallAlpha(tx+1,ty);
         var p01:Number = this.sharedLight == null && this.cfgDim == 0.35 ? a01 : this.personalWallAlpha(tx,ty+1);
         var p11:Number = this.sharedLight == null && this.cfgDim == 0.35 ? a11 : this.personalWallAlpha(tx+1,ty+1);
         // Uniform corners interpolate to the same integer for every sample.
         // Preserve the tracking path, including its old threshold comparison.
         if(!trackMask && a00 == a10 && a00 == a01 && a00 == a11
            && (this.cfgMode != "current" || this.currentSight == null
               || this.fov[tx+ty*this.spaceX] == FOV_NONE
               || (p00 == p10 && p00 == p01 && p00 == p11)))
         {
            this.fogCellRect.x = FOG_PAD + tx * FOG_SUB;
            this.fogCellRect.y = FOG_PAD + ty * FOG_SUB;
            this.fogCache.fillRect(this.fogCellRect,uint(Math.round(a00))<<24);
            if(this.cfgMode == "current" && this.currentSight != null)
               this.currentSight.fillRect(this.fogCellRect,
                  p00 < MASK_LIT_A && this.fov[tx+ty*this.spaceX] != FOV_NONE ? 0xFFFFFFFF : 0);
            return false;
         }
         for(var sy:int = 0; sy < FOG_SUB; sy++)
         {
            var fy:Number = (sy + 0.5) / FOG_SUB;
            var left:Number = a00 + fy * (a01 - a00);
            var right:Number = a10 + fy * (a11 - a10);
            for(var sx:int = 0; sx < FOG_SUB; sx++)
            {
               var fx:Number = (sx + 0.5) / FOG_SUB;
               var a:int = Math.round(left + fx * (right - left));
               if(trackMask)
               {
                  var oldA:int = this.fogCache.getPixel32(FOG_PAD + tx * FOG_SUB + sx,
                     FOG_PAD + ty * FOG_SUB + sy) >>> 24;
                  if((oldA < MASK_LIT_A) != (a < MASK_LIT_A)) maskChanged = true;
               }
               this.fogCache.setPixel32(FOG_PAD + tx * FOG_SUB + sx,
                  FOG_PAD + ty * FOG_SUB + sy,a << 24);
               if(this.cfgMode == "current" && this.currentSight != null)
               {
                  var personalA:int = Math.round((1-fx)*((1-fy)*p00+fy*p01)+fx*((1-fy)*p10+fy*p11));
                  this.currentSight.setPixel32(FOG_PAD+tx*FOG_SUB+sx,FOG_PAD+ty*FOG_SUB+sy,
                     personalA < MASK_LIT_A && this.fov[tx+ty*this.spaceX]!=FOV_NONE ? 0xFFFFFFFF : 0);
               }
            }
         }
         return maskChanged;
      }

      /**
       * 全暗瓦片（记忆区/未探索）按子格"曾见"历史填充：曾见→记忆暗色 dimA，
       * 从未见→全黑。快路径：整块已见→fillRect(dimA)，整块未见→fillRect(黑)。
       * 记忆区边界由 seenSub 形状决定（5px 粒度），不再整块 40px 阶梯。
       */
      private function fillMemoryTile(tx:int, ty:int, dimA:int):void
      {
         if(this.fullySeen[tx+ty*this.spaceX] || (this.sharedFull != null && this.sharedFull[tx+ty*this.spaceX]))
         {
            this.fogCellRect.x=FOG_PAD+tx*FOG_SUB; this.fogCellRect.y=FOG_PAD+ty*FOG_SUB;
            this.fogCache.fillRect(this.fogCellRect,uint(dimA)<<24);
            return;
         }
         // Shared exploration is merged independently. Keep its existing scan;
         // local-only tiles reuse a classification until a seenSub write.
         var tileIndex:int=tx+ty*this.spaceX;
         var cached:*=this.sharedSeen==null && this.memoryTileState!=null?this.memoryTileState[tileIndex]:null;
         if(cached===0 || cached===2){
            this.fogCellRect.x=FOG_PAD+tx*FOG_SUB;this.fogCellRect.y=FOG_PAD+ty*FOG_SUB;
            this.fogCache.fillRect(this.fogCellRect,cached===0?0xFF000000:uint(dimA)<<24);return;
         }
         var idxBase:int = ty * FOG_SUB * this.subW + tx * FOG_SUB;
         var seenAll:Boolean = true;
         var seenAny:Boolean = false;
         var sx:int;
         var sy:int;
         if(cached!==1) for(sx = 0; sx < FOG_SUB; sx++)
         {
            for(sy = 0; sy < FOG_SUB; sy++)
            {
               if(this.memorySeen(idxBase + sy * this.subW + sx))
               {
                  seenAny = true;
               }
               else
               {
                  seenAll = false;
               }
            }
         }
         if(cached===1){seenAll=false;seenAny=true;}
         else if(this.sharedSeen==null && this.memoryTileState!=null)this.memoryTileState[tileIndex]=seenAll?2:(seenAny?1:0);
         this.fogCellRect.x = FOG_PAD + tx * FOG_SUB;
         this.fogCellRect.y = FOG_PAD + ty * FOG_SUB;
         if(seenAll)
         {
            // 整块都曾见（记忆区内部）：均匀暗色
            this.fogCache.fillRect(this.fogCellRect,dimA << 24);
            return;
         }
         if(!seenAny)
         {
            // 从未见过（未探索内部）：整块全黑
            this.fogCache.fillRect(this.fogCellRect,0xFF000000);
            return;
         }
         var px0:int = FOG_PAD + tx * FOG_SUB;
         var py0:int = FOG_PAD + ty * FOG_SUB;
         for(sx = 0; sx < FOG_SUB; sx++)
         {
            for(sy = 0; sy < FOG_SUB; sy++)
            {
               this.fogCache.setPixel32(px0 + sx,py0 + sy,
                  (this.memorySeen(idxBase + sy * this.subW + sx) ? dimA : 255) << 24);
            }
         }
      }

      /** classic：保留格角光照，中心FOV/记忆以自己的坐标合成，消除半格投影偏位。 */
      private function applyVisionClassic(w:World, loc:Location, needFov:Boolean, logicOnly:Boolean = false):void
      {
         // 交替渲染帧或 FOV 变化帧更新；实际频率取决于宿主帧率。
         if((this.frameCount & 1) != 0 && !needFov)
         {
            if(this.cfgAutoTest) this.atClsS++;
            if(this.classicRenderedTiles!=null && this.classicRaw!=null){
               var exposed:Rectangle=this.scenePaintBounds(),needed:Rectangle=exposed.clone();
               needed.inflate(-2,-2);
               if(!this.classicRenderedTiles.containsRect(needed))this.paintClassicDisplay(loc,exposed,logicOnly,true);
            }
            return;
         }
         if(this.cfgAutoTest) this.atClsF++;
         this.ensureFog(w);
         if(this.classicRaw == null) return;
         if(w.grafon != null) w.grafon.visLight.visible = false;
         var large:Boolean=this.spaceX>48 || this.spaceY>25;
         var paintTiles:Rectangle=large?this.scenePaintBounds():null;
         var separateLogic:Boolean = this.cfgDim != 0.35 || large;
         if(separateLogic && this.classicLogicMemorySamples == null)
         {
            this.classicLogicMemorySamples=new BitmapData(this.classicMemoryRaw.width,this.classicMemoryRaw.height,true,0xFF000000);
            this.classicLogicVisibilitySamples=new BitmapData(this.classicVisibilityRaw.width,this.classicVisibilityRaw.height,false,0xFFFFFF);
         }
         var changed:Boolean=needFov || separateLogic;
         var logicalChanged:Boolean=needFov;
         var displayGrey:int=Math.round(255*this.cfgDim);
         var canonicalGrey:int=Math.round(255*0.35);
         // Both fields share terrain, light and memory progress. Only their
         // grey values and deepest-neighbour choice may differ.
         for(var mi:int=0;mi<this.spaceX*this.spaceY;mi++) this.advanceMemory(loc,mi);
         this.prepareClassicCells(loc);
         for(var ty:int=0;ty<this.spaceY;ty++) for(var tx:int=0;tx<this.spaceX;tx++)
         {
            var i:int=tx+ty*this.spaceX;
            if(!this.classicCells.dirty[i])continue;
            var a:int=this.classicCells.alpha[i];
            if(a != this.lastA[i])
            {
               this.lastA[i]=a;this.classicRaw.setPixel32(tx,ty+1,a<<24);
               changed=logicalChanged=true;
            }
            var explored:Boolean=this.memoryExplored(i);
            var solid:Boolean=loc.getTile(tx,ty).opac>=1;
            var memory:Number=this.memCur[i], logicalMemory:Number=memory;
            var targetGrey:int=explored?displayGrey:0;
            var logicalTarget:int=explored?canonicalGrey:0;
            var grey:int=solid?Math.round((255-a)*this.cfgDim):targetGrey;
            var logicalGrey:int=solid?Math.round((255-a)*0.35):logicalTarget;
            if(!loc.retDark && solid)
            {
               var deepest:Number=0,logicalDeepest:Number=0;
               for(var dy:int=-1;dy<=1;dy++) for(var dx:int=-1;dx<=1;dx++)
               {
                  var nx:int=tx+dx,ny:int=ty+dy;
                  if(nx<=0 || ny<=0 || nx>=this.spaceX || ny>=this.spaceY || loc.getTile(nx,ny).opac>=1)continue;
                  var ni:int=nx+ny*this.spaceX;
                  var ne:Boolean=this.memoryExplored(ni);
                  var nm:Number=this.memCur[ni];
                  var ng:int=ne?displayGrey:0;
                  var depth:Number=nm*(255-ng);
                  if(depth>deepest){deepest=depth;memory=nm;grey=targetGrey=ng;}
                  if(separateLogic)
                  {
                     ng=ne?canonicalGrey:0;depth=nm*(255-ng);
                     if(depth>logicalDeepest){logicalDeepest=depth;logicalMemory=nm;logicalGrey=logicalTarget=ng;}
                  }
               }
            }
            var memoryAlpha:int=Math.round(memory*255);
            var pixel:uint=memoryAlpha==0?0:(memoryAlpha<<24)|(grey<<16)|(grey<<8)|grey;
            if(tx==0 || ty==0)pixel=0xFF000000;
            var visibility:int=Math.round(255-memory*(255-targetGrey));
            var visibilityPixel:uint=(visibility<<16)|(visibility<<8)|visibility;
            if(this.classicVisibilityRaw.getPixel(tx,ty+1)!=visibilityPixel)
            {this.classicVisibilityRaw.setPixel(tx,ty+1,visibilityPixel);changed=true;}
            if(this.classicMemoryRaw.getPixel32(tx,ty+1)!=pixel)
            {this.classicMemoryRaw.setPixel32(tx,ty+1,pixel);changed=true;}
            if(separateLogic)
            {
               memoryAlpha=Math.round(logicalMemory*255);
               pixel=memoryAlpha==0?0:(memoryAlpha<<24)|(logicalGrey<<16)|(logicalGrey<<8)|logicalGrey;
               if(tx==0 || ty==0)pixel=0xFF000000;
               visibility=Math.round(255-logicalMemory*(255-logicalTarget));
               visibilityPixel=(visibility<<16)|(visibility<<8)|visibility;
               if(this.classicLogicVisibilitySamples.getPixel(tx,ty+1)!=visibilityPixel)
               {this.classicLogicVisibilitySamples.setPixel(tx,ty+1,visibilityPixel);logicalChanged=true;}
               if(this.classicLogicMemorySamples.getPixel32(tx,ty+1)!=pixel)
               {this.classicLogicMemorySamples.setPixel32(tx,ty+1,pixel);logicalChanged=true;}
            }
         }
         if(this.refreshWallField(loc,this.wallGeometryDirty,false))changed=logicalChanged=true;
         this.wallGeometryDirty=false;
         if(separateLogic && (logicalChanged || this.classicLogicCache==null))
         {
            for(var ly:int=1;ly<=this.spaceY;ly++)
               this.classicLogicVisibilitySamples.setPixel(this.spaceX,ly,this.classicLogicVisibilitySamples.getPixel(this.spaceX-1,ly));
            for(var lx:int=0;lx<=this.spaceX;lx++)
            {
               this.classicLogicVisibilitySamples.setPixel(lx,0,this.classicLogicVisibilitySamples.getPixel(lx,1));
               this.classicLogicVisibilitySamples.setPixel(lx,this.spaceY+1,this.classicLogicVisibilitySamples.getPixel(lx,this.spaceY));
            }
            this.classicLogicCache=this.sizedScratch(this.classicLogicCache);
            this.classicLogicRaw=this.sizedScratch(this.classicLogicRaw);
            this.classicLogicVisibility=this.sizedScratch(this.classicLogicVisibility);
            this.classicLogicWalls=this.sizedScratch(this.classicLogicWalls);
            this.classicLogicCache.fillRect(this.fogRect,0xFF000000);
            this.classicLogicDeltas=new Array(this.spaceX*this.spaceY);
            this.classicLogicTiles=new Vector.<int>(this.spaceX*this.spaceY,true);
            if(logicalChanged)this.fovVersion++;
         }

         if(changed){this.paintClassicDisplay(loc,paintTiles,logicOnly,separateLogic);this.fovVersion++;}
      }

      /** Raster-only refresh: camera moves never advance the last sampled light,
       * exploration, memory fade or logical sight. */
      private function prepareClassicCells(loc:Location):void
      {
         var n:int=this.spaceX*this.spaceY;
         var fresh:Boolean=this.classicCells==null || this.classicCells.alpha.length!=n;
         if(fresh){
            this.classicCells={alpha:new Vector.<int>(n,true),memory:new Vector.<Number>(n,true),
               known:new Vector.<Boolean>(n,true),solid:new Vector.<Boolean>(n,true),dirty:new Vector.<Boolean>(n,true)};
            this.wallGeometryDirty=true;
         }
         var cells:Object=this.classicCells;
         var alphas:Vector.<int>=cells.alpha,memories:Vector.<Number>=cells.memory;
         var knowns:Vector.<Boolean>=cells.known,solids:Vector.<Boolean>=cells.solid,dirtyCells:Vector.<Boolean>=cells.dirty;
         var all:Boolean=fresh || this.classicCellDim!=this.cfgDim || this.classicCellDark!=loc.retDark;
         this.classicCellDim=this.cfgDim;this.classicCellDark=loc.retDark;
         for(var i:int=0;i<n;i++)dirtyCells[i]=all;
         for(var y:int=0;y<this.spaceY;y++)for(var x:int=0;x<this.spaceX;x++){
            i=x+y*this.spaceX;
            var alpha:int=this.tileFogAlpha(loc,x,y),memory:Number=this.memCur[i];
            var known:Boolean=this.memoryExplored(i),solid:Boolean=loc.getTile(x,y).opac>=1;
            if(solids[i]!=solid)this.wallGeometryDirty=true;
            if(!all && (alphas[i]!=alpha || memories[i]!=memory || knowns[i]!=known || solids[i]!=solid)){
               for(var yy:int=Math.max(0,y-1);yy<=Math.min(this.spaceY-1,y+1);yy++)
                  for(var xx:int=Math.max(0,x-1);xx<=Math.min(this.spaceX-1,x+1);xx++)dirtyCells[xx+yy*this.spaceX]=true;
            }
            alphas[i]=alpha;memories[i]=memory;knowns[i]=known;solids[i]=solid;
         }
         var x0:int=this.spaceX,y0:int=this.spaceY,x1:int=0,y1:int=0;
         for(y=0;y<this.spaceY;y++)for(x=0;x<this.spaceX;x++)if(dirtyCells[x+y*this.spaceX]){
            if(x<x0)x0=x;if(y<y0)y0=y;if(x+1>x1)x1=x+1;if(y+1>y1)y1=y+1;
         }
         this.classicInputRegion=x1>x0?new Rectangle(FOG_PAD+x0*FOG_SUB,FOG_PAD+y0*FOG_SUB,(x1-x0)*FOG_SUB,(y1-y0)*FOG_SUB):new Rectangle();
      }

      private function paintClassicDisplay(loc:Location,paintTiles:Rectangle,logicOnly:Boolean,separateLogic:Boolean):void
      {
         var paint:Rectangle=paintTiles==null?this.fogRect:new Rectangle(FOG_PAD+paintTiles.x*FOG_SUB,FOG_PAD+paintTiles.y*FOG_SUB,paintTiles.width*FOG_SUB,paintTiles.height*FOG_SUB);
         if(paintTiles!=null){paint.inflate(16,16);paint=paint.intersection(this.fogRect);}
         var paintPoint:Point=new Point(paint.x,paint.y);
            // 在白底上画原版黑雾，得到原版亮度；再以记忆进度为alpha混入
            // 格中心记忆亮度。不是叠加两层黑雾，弱光与地板记忆语义各自保留。
            this.fogRaw.fillRect(paint,0xFFFFFFFF);
            this.fogRaw.draw(this.classicRaw,this.classicLightMatrix,null,null,paint,true);
            this.fogRaw.draw(this.classicMemoryRaw,this.classicMemoryMatrix,null,null,paint,true);
            // 可见性系数在房间外沿延续最后一个样本；外侧黑色仍由原光照负责。
            for(var edgeY:int = 1; edgeY <= this.spaceY; edgeY++)
               this.classicVisibilityRaw.setPixel(this.spaceX,edgeY,this.classicVisibilityRaw.getPixel(this.spaceX-1,edgeY));
            for(var edgeX:int = 0; edgeX <= this.spaceX; edgeX++)
            {
               this.classicVisibilityRaw.setPixel(edgeX,0,this.classicVisibilityRaw.getPixel(edgeX,1));
               this.classicVisibilityRaw.setPixel(edgeX,this.spaceY+1,this.classicVisibilityRaw.getPixel(edgeX,this.spaceY));
            }
            this.classicVisibilityField.fillRect(paint,0xFFFFFF);
            this.classicVisibilityField.draw(this.classicVisibilityRaw,this.classicMemoryMatrix,null,null,paint,true);
            // 先在不透明RGB上反相，再复制到alpha。直接反转目标alpha时，
            // AIR会跳过alpha=0的像素，导致原本全黑的区域变成透明洞。
            this.fogRaw.colorTransform(paint,this.brightnessToFog);
            this.fogBmp.fillRect(paint,0);
            this.fogBmp.copyChannel(this.fogRaw,paint,paintPoint,
               BitmapDataChannel.RED,BitmapDataChannel.ALPHA);
            this.joinClassicWalls(loc,paintTiles);
            // 部分敌人按本次合成后的实际场取样，不再读错行/错相位的1px源图。
            this.fogCache.copyPixels(this.fogBmp,paint,paintPoint);
            if(!logicOnly && this.cfgSoftClassic > 0)
            {
               this.classicSoftInput=this.sizedScratch(this.classicSoftInput);
               this.classicSoftInput.copyPixels(this.fogBmp,paint,paintPoint);
               this.fogBlur.blurX=this.fogBlur.blurY=this.cfgSoftClassic/5;
               this.fogBmp.applyFilter(this.classicSoftInput,paint,paintPoint,this.fogBlur);
               // Reconnect the softened floor to the untouched native wall field.
               this.fogRaw.copyChannel(this.fogBmp,paint,paintPoint,BitmapDataChannel.ALPHA,BitmapDataChannel.BLUE);
               this.joinClassicWalls(loc,paintTiles);
               this.fogCache.copyPixels(this.classicSoftInput,paint,paintPoint);
            }
            if(separateLogic) this.fogCache.copyPixels(this.classicLogicCache,this.fogRect,this.fogPoint);
         this.classicRenderedTiles=paintTiles==null?null:paintTiles.clone();
      }

      /** 墙保留原版基底，仅叠加中心遮挡；地板在墙外一格内接到同一边界值。 */
      private function joinClassicWalls(loc:Location, bounds:Rectangle = null, prepared:Boolean = false, visited:Vector.<int> = null):void
      {
         var paint:Rectangle=bounds==null?this.fogRect:new Rectangle(FOG_PAD+bounds.x*FOG_SUB,FOG_PAD+bounds.y*FOG_SUB,bounds.width*FOG_SUB,bounds.height*FOG_SUB);
         if(bounds!=null){paint.inflate(16,16);paint=paint.intersection(this.fogRect);}
         var paintPoint:Point=new Point(paint.x,paint.y);
         if(!prepared)
         {
         this.classicWallShade.fillRect(paint,0);
         // 遮挡场延伸过裁切边界，平滑采样不会混入墙外透明像素而形成亮缝。
         this.fogCache.copyPixels(this.classicVisibilityField,paint,paintPoint);
         this.fogCache.colorTransform(paint,this.brightnessToFog);
         this.classicWallShade.copyChannel(this.fogCache,paint,paintPoint,
            BitmapDataChannel.RED,BitmapDataChannel.ALPHA);
         this.classicCornerDeltas = new Array(this.spaceX*this.spaceY);
         for each(var ci:int in this.wallCorners)
         {
            if(bounds!=null && (ci%this.spaceX<bounds.x || ci%this.spaceX>bounds.right || int(ci/this.spaceX)<bounds.y || int(ci/this.spaceX)>bounds.bottom))continue;
            this.classicCornerDeltas[ci] = this.classicWallDelta(this.wallA[ci],
               FOG_PAD+(ci%this.spaceX)*FOG_SUB-0.5,
               FOG_PAD+int(ci/this.spaceX)*FOG_SUB-0.5);
         }
         // 敌人取样缓存：让位图合成完成墙光×可见性，避免AS3逐子像素乘算。
         this.fogCache.fillRect(paint,0xFFFFFFFF);
         this.fogCache.draw(this.wallRaw,this.classicLightMatrix,null,null,paint,true);
         this.fogCache.draw(this.classicVisibilityField,null,null,"multiply",paint);
         this.fogCache.colorTransform(paint,this.brightnessToFog);
         }
         var x0:int=bounds == null ? 0 : Math.max(0,int(bounds.x));
         var y0:int=bounds == null ? 0 : Math.max(0,int(bounds.y));
         var x1:int=bounds == null ? this.spaceX : Math.min(this.spaceX,int(bounds.right));
         var y1:int=bounds == null ? this.spaceY : Math.min(this.spaceY,int(bounds.bottom));
         if(x1<=x0 || y1<=y0) return;
         var wallPoint:Point = new Point();
         var copyCount:int=bounds == null ? this.wallTiles.length : (x1-x0)*(y1-y0);
         for(var copyIndex:int=0;copyIndex<copyCount;copyIndex++)
         {
            var wi:int=bounds == null ? this.wallTiles[copyIndex] : x0+copyIndex%(x1-x0)+(y0+int(copyIndex/(x1-x0)))*this.spaceX;
            if(visited != null && visited[wi]) continue;
            if(bounds != null && loc.getTile(wi%this.spaceX,int(wi/this.spaceX)).opac<1) continue;
            wallPoint.x = this.fogCellRect.x = FOG_PAD+(wi%this.spaceX)*FOG_SUB;
            wallPoint.y = this.fogCellRect.y = FOG_PAD+int(wi/this.spaceX)*FOG_SUB;
            this.fogBmp.copyChannel(this.fogCache,this.fogCellRect,wallPoint,
               BitmapDataChannel.RED,BitmapDataChannel.ALPHA);
         }
         var westCurve:Array = [], eastCurve:Array = [], northCurve:Array = [], southCurve:Array = [];
         for(var ty:int = y0; ty < y1; ty++) for(var tx:int = x0; tx < x1; tx++)
         {
            if(visited != null)
            {
               var vi:int=tx+ty*this.spaceX;
               if(visited[vi]) continue;
               visited[vi]=1;
            }
            if(loc.getTile(tx,ty).opac >= 1) continue;
            var west:Boolean = tx > 0 && loc.getTile(tx-1,ty).opac >= 1;
            var east:Boolean = tx+1 < this.spaceX && loc.getTile(tx+1,ty).opac >= 1;
            var north:Boolean = ty > 0 && loc.getTile(tx,ty-1).opac >= 1;
            var south:Boolean = ty+1 < this.spaceY && loc.getTile(tx,ty+1).opac >= 1;
            var d00:Number = this.classicCornerDeltaAt(tx,ty), d10:Number = this.classicCornerDeltaAt(tx+1,ty);
            var d01:Number = this.classicCornerDeltaAt(tx,ty+1), d11:Number = this.classicCornerDeltaAt(tx+1,ty+1);
            if(!west && !east && !north && !south && d00 == 0 && d10 == 0 && d01 == 0 && d11 == 0) continue;
            var px0:int = FOG_PAD + tx*FOG_SUB, py0:int = FOG_PAD + ty*FOG_SUB;
            var a00:Number = this.wallCornerAlpha(tx,ty), a10:Number = this.wallCornerAlpha(tx+1,ty);
            var a01:Number = this.wallCornerAlpha(tx,ty+1), a11:Number = this.wallCornerAlpha(tx+1,ty+1);
            // 同一条边只采样一次，供整格复用，避免每个子像素重复读取位图。
            for(var q:int = 0; q < FOG_SUB; q++)
            {
               var fraction:Number = (q+0.5)/FOG_SUB;
               if(west) westCurve[q] = this.classicWallDelta(a00+(a01-a00)*fraction,px0-0.5,py0+q)-(d00+(d01-d00)*fraction);
               if(east) eastCurve[q] = this.classicWallDelta(a10+(a11-a10)*fraction,px0+FOG_SUB-0.5,py0+q)-(d10+(d11-d10)*fraction);
               if(north) northCurve[q] = this.classicWallDelta(a00+(a10-a00)*fraction,px0+q,py0-0.5)-(d00+(d10-d00)*fraction);
               if(south) southCurve[q] = this.classicWallDelta(a01+(a11-a01)*fraction,px0+q,py0+FOG_SUB-0.5)-(d01+(d11-d01)*fraction);
            }
            // fogBmp already contains fogRaw's integer red channel here.
            // When every correction is zero, the old 64-pixel loop merely
            // writes those same bytes back. Keep the exact existing image.
            var noCorrection:Boolean=d00==0 && d10==0 && d01==0 && d11==0;
            if(noCorrection){
               for(q=0;q<FOG_SUB;q++){
                  if((west && westCurve[q]!=0) || (east && eastCurve[q]!=0)
                     || (north && northCurve[q]!=0) || (south && southCurve[q]!=0)){
                     noCorrection=false;break;
                  }
               }
               if(noCorrection)continue;
            }
            for(var sy:int = 0; sy < FOG_SUB; sy++) for(var sx:int = 0; sx < FOG_SUB; sx++)
            {
               var fx:Number = (sx+0.5)/FOG_SUB, fy:Number = (sy+0.5)/FOG_SUB;
               var px:int = px0+sx, py:int = py0+sy;
               var a:Number = this.fogRaw.getPixel(px,py)&255;
               // 先共享四角差值，再补墙边的曲线残差。对角相邻地板也参与，
               // 不把墙边的断层搬到一格之外；内角的共用角不会叠加两次。
               a += (d00+(d10-d00)*fx)*(1-fy)+(d01+(d11-d01)*fx)*fy;
               if(west) a += (1-fx)*westCurve[sy];
               if(east) a += fx*eastCurve[sy];
               if(north) a += (1-fy)*northCurve[sx];
               if(south) a += fy*southCurve[sx];
               this.fogBmp.setPixel32(px,py,Math.max(0,Math.min(255,Math.round(a))) << 24);
            }
         }
      }

      /** Materialize each requested canonical tile once per refreshed field.
       * New units and changed bounds can query additional tiles in the same frame.
       * All arithmetic and raster inputs are those of the original full pass. */
      private function classicLogicRegion(bounds:Rectangle):void
      {
         if(this.cfgMode != "classic" || this.classicLogicTiles == null) return;
         var region:Rectangle=new Rectangle(FOG_PAD+bounds.x*FOG_SUB,FOG_PAD+bounds.y*FOG_SUB,bounds.width*FOG_SUB,bounds.height*FOG_SUB);
         var fresh:Boolean=false;
         var tx:int,ty:int;
         var freshLeft:int=this.spaceX,freshTop:int=this.spaceY,freshRight:int=0,freshBottom:int=0;
         for(ty=bounds.y;ty<bounds.bottom;ty++) for(tx=bounds.x;tx<bounds.right;tx++)
            if(!this.classicLogicTiles[tx+ty*this.spaceX]){
               fresh=true;
               if(tx<freshLeft)freshLeft=tx;if(ty<freshTop)freshTop=ty;
               if(tx+1>freshRight)freshRight=tx+1;if(ty+1>freshBottom)freshBottom=ty+1;
            }
         if(fresh)
         {
            // Adjacent masks share canonical samples. Batch a small tile block
            // without changing the samples, support gutter, or queried sight.
            var bx:int=Math.max(0,int(freshLeft/4)*4),by:int=Math.max(0,int(freshTop/4)*4);
            var br:int=Math.min(this.spaceX,Math.ceil(freshRight/4)*4);
            var bb:int=Math.min(this.spaceY,Math.ceil(freshBottom/4)*4);
            bounds=new Rectangle(bx,by,br-bx,bb-by);
            region=new Rectangle(FOG_PAD+bx*FOG_SUB,FOG_PAD+by*FOG_SUB,bounds.width*FOG_SUB,bounds.height*FOG_SUB);
            var raw:BitmapData=this.fogRaw,bmp:BitmapData=this.fogBmp,cache:BitmapData=this.fogCache;
            var visibility:BitmapData=this.classicVisibilityField;
            var deltas:Array=this.classicCornerDeltas;
            try
            {
               this.fogRaw=this.classicLogicRaw;this.fogBmp=this.classicLogicCache;this.fogCache=this.classicLogicWalls;
               this.classicVisibilityField=this.classicLogicVisibility;this.classicCornerDeltas=this.classicLogicDeltas;
               // AIR's clipped smooth raster adds edge rounding with a one-pixel
               // gutter. Two tiles of support match the full raster exactly.
               var sample:Rectangle=region.clone();sample.inflate(16,16);sample=sample.intersection(this.fogRect);
               this.fogRaw.fillRect(sample,0xFFFFFFFF);
               this.fogRaw.draw(this.classicRaw,this.classicLightMatrix,null,null,sample,true);
               this.fogRaw.draw(this.classicLogicMemorySamples,this.classicMemoryMatrix,null,null,sample,true);
               this.fogRaw.colorTransform(sample,this.brightnessToFog);
               this.classicVisibilityField.fillRect(sample,0xFFFFFFFF);
               this.classicVisibilityField.draw(this.classicLogicVisibilitySamples,this.classicMemoryMatrix,null,null,sample,true);
               this.fogCache.fillRect(region,0xFFFFFFFF);
               this.fogCache.draw(this.wallRaw,this.classicLightMatrix,null,null,region,true);
               this.fogCache.draw(this.classicVisibilityField,null,null,"multiply",region);
               this.fogCache.colorTransform(region,this.brightnessToFog);
               var cell:Rectangle=new Rectangle(0,0,FOG_SUB,FOG_SUB),point:Point=new Point();
               for(ty=bounds.y;ty<bounds.bottom;ty++) for(tx=bounds.x;tx<bounds.right;tx++)
               {
                  if(this.classicLogicTiles[tx+ty*this.spaceX]) continue;
                  cell.x=point.x=FOG_PAD+tx*FOG_SUB;cell.y=point.y=FOG_PAD+ty*FOG_SUB;
                  this.fogBmp.fillRect(cell,0);
                  this.fogBmp.copyChannel(this.fogRaw,cell,point,BitmapDataChannel.RED,BitmapDataChannel.ALPHA);
               }
               for(ty=bounds.y;ty<=bounds.bottom && ty<this.spaceY;ty++) for(tx=bounds.x;tx<=bounds.right && tx<this.spaceX;tx++)
               {
                  var ci:int=tx+ty*this.spaceX;
                  if(this.classicCornerDeltas[ci] !== undefined) continue;
                  this.classicCornerDeltas[ci]=this.wallA[ci] === undefined ? 0 :
                     this.classicWallDelta(this.wallA[ci],FOG_PAD+tx*FOG_SUB-0.5,FOG_PAD+ty*FOG_SUB-0.5);
               }
               this.joinClassicWalls(this.curLoc,bounds,true,this.classicLogicTiles);
            }
            finally
            {
               this.fogRaw=raw;this.fogBmp=bmp;this.fogCache=cache;
               this.classicVisibilityField=visibility;this.classicCornerDeltas=deltas;
            }
            // Only the newly materialized rectangle needs publishing. Every
            // previously valid tile was already copied in this field generation.
            this.fogCache.copyPixels(this.classicLogicCache,region,new Point(region.x,region.y));
         }
      }

      private function releaseClassicLogic():void
      {
         if(this.classicLogicMemorySamples != null) this.classicLogicMemorySamples.dispose();
         if(this.classicLogicVisibilitySamples != null) this.classicLogicVisibilitySamples.dispose();
         this.classicLogicMemorySamples=this.classicLogicVisibilitySamples=null;
         if(this.classicLogicCache != null) this.classicLogicCache.dispose();
         if(this.classicLogicRaw != null) this.classicLogicRaw.dispose();
         if(this.classicLogicVisibility != null) this.classicLogicVisibility.dispose();
         if(this.classicLogicWalls != null) this.classicLogicWalls.dispose();
         this.classicLogicCache=this.classicLogicRaw=this.classicLogicVisibility=this.classicLogicWalls=null;
         this.classicLogicDeltas=null;this.classicLogicTiles=null;
      }

      private function sizedScratch(b:BitmapData):BitmapData
      {
         if(b == null || b.width != this.fogBmp.width || b.height != this.fogBmp.height)
         {if(b != null)b.dispose();b=new BitmapData(this.fogBmp.width,this.fogBmp.height,true,0);}
         return b;
      }

      private function classicCornerDeltaAt(tx:int, ty:int):Number
      {
         if(tx >= this.spaceX || ty >= this.spaceY) return 0;
         return this.classicCornerDeltas[tx+ty*this.spaceX] || 0;
      }

      private function classicWallDelta(wallAlpha:Number, px:Number, py:Number):Number
      {
         var visibility:Number = this.classicFieldAt(this.classicVisibilityField,px,py);
         var target:Number = 255-(255-wallAlpha)*visibility/255;
         return target-this.classicFieldAt(this.fogRaw,px,py);
      }

      private function classicFieldAt(field:BitmapData, px:Number, py:Number):Number
      {
         var x:int = int(px), y:int = int(py);
         var fx:Number = px-x, fy:Number = py-y;
         var a:Number = field.getPixel(x,y)&255;
         if(fx == 0 && fy == 0) return a;
         if(fx == 0) return a+((field.getPixel(x,y+1)&255)-a)*fy;
         var b:Number = field.getPixel(x+1,y)&255;
         if(fy == 0) return a+(b-a)*fx;
         var c:Number = field.getPixel(x,y+1)&255, d:Number = field.getPixel(x+1,y+1)&255;
         return (a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy;
      }

      /** 距离衰减因子：全亮半径内 1，向外到视野半径线性降到 0（原版 lDist1→lDist2）。 */
      private function distFalloff(d2:Number):Number
      {
         var d:Number = Math.sqrt(d2);
         if(d <= this.locDist1)
         {
            return 1;
         }
         if(d >= this.locDist2)
         {
            return 0;
         }
         return (this.locDist2 - d) / (this.locDist2 - this.locDist1);
      }

      // ==================== 敌人显示 ====================

      private function unitBBox(loc:Location, u:Unit):Array
      {
         // 外扩 1 瓦片（v0.21）：小体型敌人（如炮塔 phis 38×38 < 40px 瓦片）
         // 包围盒只有 1 个瓦片 → 明暗边界处瓦片级二值判定 → 全出现-全消失
         // 二分。外扩后跨边界时进入部分可见态（state=2），由子格掩膜精确
         // 裁剪（掩膜内容按子格 raycast，外扩圈只扩大候选区域，不改变可见
         // 语义）
         var x0:int = Math.floor((u.X - u.scX / 2) / Tile.tileX) - 1;
         var x1:int = Math.floor((u.X + u.scX / 2) / Tile.tileX) + 1;
         var y0:int = Math.floor((u.Y - u.scY) / Tile.tileY) - 1;
         var y1:int = Math.floor(u.Y / Tile.tileY) + 1;
         if(x0 < 0)
         {
            x0 = 0;
         }
         if(y0 < 0)
         {
            y0 = 0;
         }
         if(x1 >= this.spaceX)
         {
            x1 = this.spaceX - 1;
         }
         if(y1 >= this.spaceY)
         {
            y1 = this.spaceY - 1;
         }
         if(x1 < x0)
         {
            x1 = x0;
         }
         if(y1 < y0)
         {
            y1 = y0;
         }
         return [x0,y0,x1,y1];
      }

      private function bboxFovCount(bb:Array):int
      {
         var n:int = 0;
         var tx:int;
         var ty:int;
         for(tx = bb[0]; tx <= bb[2]; tx++)
         {
            for(ty = bb[1]; ty <= bb[3]; ty++)
            {
               // 明亮视野 + 部分透光（木门/栅格/水后）都算"可见"（暗色显示、可抓取）
               if(this.fov[tx + ty * this.spaceX] != FOV_NONE)
               {
                  n++;
               }
            }
         }
         return n;
      }

      private function bboxTotal(bb:Array):int
      {
         return (bb[2] - bb[0] + 1) * (bb[3] - bb[1] + 1);
      }

      private function enemyState(loc:Location, u:Unit):int
      {
         var bb:Array = this.unitBBox(loc,u);
         var total:int = this.bboxTotal(bb);
         var n:int = this.bboxFovCount(bb);
         if(n <= 0)
         {
            return 0;
         }
         // Start a sight generation only when a visible unit needs it.
         // Small rooms keep the existing full snapshot; large rooms classify
         // exact queried tiles lazily. Fog/wall writes invalidate both paths.
         if(this.cfgMode == "current" && this.currentSightData == null && this.currentSight != null
            && (this.spaceX > 48 || this.spaceY > 25))
            // Large maps need only the tiles actually touched by unit bounds.
            // An empty vector identifies this unchanged logical field. Every
            // write to currentSight above invalidates it before hideEnemies;
            // classification and masks run synchronously against that field.
            this.currentSightData = new Vector.<uint>();
         if(this.cfgMode == "current" && this.currentSightData != null)
         {
            // Bounding boxes are tile aligned. Reusing each tile's exact
            // all-dark/all-visible/mixed summary avoids rescanning overlapping
            // unit bounds (including multiple units sharing a visual).
            if(bb[0]>=0 && bb[1]>=0 && bb[2]<this.spaceX && bb[3]<this.spaceY)
            {
               if(this.classifiedSight !== this.currentSightData)
               {
                  this.classifiedSight = this.currentSightData;
                  this.sightClasses = new Vector.<int>(this.spaceX*this.spaceY,true);
               }
               var combined:int = 0;
               var data:Vector.<uint> = this.currentSightData;
               var width:int = this.currentSight.width;
               for(var ty:int=bb[1];ty<=bb[3];ty++) for(var tx:int=bb[0];tx<=bb[2];tx++)
               {
                  var ti:int=tx+ty*this.spaceX;
                  var kind:int=this.sightClasses[ti];
                  if(kind==0)
                  {
                     var tileData:Vector.<uint> = data;
                     var tileStride:int = width;
                     var start:int=(FOG_PAD+ty*MASK_SUB)*width+FOG_PAD+tx*MASK_SUB;
                     if(data.length==0)
                     {
                        tileData=this.currentSight.getVector(new Rectangle(
                           FOG_PAD+tx*MASK_SUB,FOG_PAD+ty*MASK_SUB,MASK_SUB,MASK_SUB));
                        tileStride=MASK_SUB;start=0;
                     }
                     kind=tileData[start]!=0?2:1;
                     for(var row:int=0;row<MASK_SUB && kind!=3;row++)
                        for(var col:int=0;col<MASK_SUB;col++)
                           if((tileData[start+row*tileStride+col]!=0?2:1)!=kind){kind=3;break;}
                     this.sightClasses[ti]=kind;
                  }
                  if(kind==3 || (combined!=0 && kind!=combined))return 2;
                  combined=kind;
               }
               return combined==2?1:0;
            }
            // Preserve the original fallback for unusual out-of-room bounds.
            if(this.currentSightData.length==0)
               this.currentSightData=this.currentSight.getVector(this.currentSight.rect);
            var first:int=-1;
            var stride:int=this.currentSight.width;
            for(var sy:int=bb[1]*MASK_SUB;sy<(bb[3]+1)*MASK_SUB;sy++)
               for(var sx:int=bb[0]*MASK_SUB;sx<(bb[2]+1)*MASK_SUB;sx++)
               {
                  var visible:int=this.currentSightData[(FOG_PAD+sy)*stride+FOG_PAD+sx]!=0?1:0;
                  if(first<0) first=visible;
                  else if(first!=visible) return 2;
               }
            return first==1?1:0;
         }
         if(n >= total)
         {
            return 1;
         }
         return 2;
      }

            /**
       * FOV 掩膜（只在部分可见时）：矢量 Shape + 模糊位图填充 + cacheAsBitmap
       * （v0.24.4——v0.24.3 补上 alpha 掩膜缺失的 cacheAsBitmap：Flash 文档
       * 明确，掩膜与被掩膜对象都须 cacheAsBitmap=true，掩膜才尊重 alpha 通道，
       * 否则按二值覆盖光栅化、位图填充内容甚至不渲染 → 二分）。
       *
       * 内容：子格二值场写入小位图 m2d、按模式模糊到 m2e（classic 6/q2≈40px
       * / current 4/q3≈32px，对齐各自雾层边界宽度），beginBitmapFill(smooth)
       * 放大绘制进 Shape → 敌人明暗交界渐变淡出，无 5px 硬阶梯颗粒。
       * 子格级 raycast + castRay 返回 -1（墙瓦片）回退 fov（墙炮塔不消失）；
       * 区域覆盖包围盒并向上/左右外扩（血条/动画）；按 FOV 版本+区域签名门控。
       */
      private function applyMask(w:World, u:Unit, bb:Array):void
      {
         var rec:Object = this.unitVis[u];
         if(rec == null)
         {
            rec = {state:1,m2:null,m3:null,m2d:null,m2e:null,lastFov:-1,lastBb:""};
            this.unitVis[u] = rec;
         }
         this.refreshMask(rec,bb);
         var s2:Shape=rec.m2 as Shape,s3:Shape=rec.m3 as Shape;
         if(!s2.cacheAsBitmap)s2.cacheAsBitmap=true;if(!s3.cacheAsBitmap)s3.cacheAsBitmap=true;
         if(u.vis != null && u.vis.parent != null) {
            if(s2.parent !== u.vis.parent)u.vis.parent.addChild(s2);
            if(!u.vis.cacheAsBitmap)u.vis.cacheAsBitmap=true;if(u.vis.mask!==s2)u.vis.mask=s2;
         } else if(s2.parent != null)s2.parent.removeChild(s2);
         if(u.hpbar != null && u.hpbar.parent != null) {
            if(s3.parent !== u.hpbar.parent)u.hpbar.parent.addChild(s3);
            if(!u.hpbar.cacheAsBitmap)u.hpbar.cacheAsBitmap=true;if(u.hpbar.mask!==s3)u.hpbar.mask=s3;
         } else if(s3.parent != null)s3.parent.removeChild(s3);
      }

      private function refreshMask(rec:Object,bb:Array):void
      {
         var x0:int = bb[0] - MASK_PAD_X;
         var y0:int = bb[1] - MASK_PAD_TOP;
         var x1:int = bb[2] + MASK_PAD_X;
         var y1:int = bb[3] + MASK_PAD_BOTTOM;
         if(x0 < 0)
         {
            x0 = 0;
         }
         if(y0 < 0)
         {
            y0 = 0;
         }
         if(x1 >= this.spaceX)
         {
            x1 = this.spaceX - 1;
         }
         if(y1 >= this.spaceY)
         {
            y1 = this.spaceY - 1;
         }
         var sig:String = x0 + "," + y0 + "," + x1 + "," + y1;
         if(rec.lastFov == this.fovVersion && rec.lastBb == sig)
         {
            return;
         }
         rec.lastFov = this.fovVersion;
         rec.lastBb = sig;
         var totx:int = (x1 - x0 + 1) * MASK_SUB;
         var toty:int = (y1 - y0 + 1) * MASK_SUB;
         var bd:BitmapData = rec.m2d as BitmapData;   // 子格二值场
         var bdb:BitmapData = rec.m2e as BitmapData;  // 模糊后显示源
         if(bd == null || bd.width != totx || bd.height != toty)
         {
            if(bd != null)
            {
               bd.dispose();
            }
            if(bdb != null)
            {
               bdb.dispose();
            }
            bd = new BitmapData(totx,toty,true,0);
            bdb = null;
            rec.m2d = bd;
            rec.m2e = bdb;
         }
         else
         {
            bd.fillRect(bd.rect,0);   // 清透明（复用）
         }
         // 子格级判定（5px）：castRay -1（墙）回退 fov（墙炮塔不消失）
         var cs:Number = Tile.tileX / MASK_SUB;
         var scx:int;
         var scy:int;
         var matches:int=-1;
         bd.lock();
         if(this.cfgMode == "current" && this.currentSight != null)
         {
            bd.copyPixels(this.currentSight,new Rectangle(FOG_PAD+x0*MASK_SUB,FOG_PAD+y0*MASK_SUB,totx,toty),this.fogPoint);
         }
         else if((this.cfgMode == "current" || this.cfgMode == "classic") && this.fogCache != null)
         {
            if(this.cfgMode == "classic" && this.cfgAutoTest) this.atMaskRaw++;
            // v0.24.5（current）：直接采样最终雾场 fogCache（已含距离衰减/
            // 墙亮面/门景/记忆区）——零 raycast（敌人掩膜从每 FOV 变化数千
            // 次 castRay 降到数千次 getPixel32），且掩膜与雾层**像素级对齐**
            // （敌人按雾的实际渲染淡出，含衰减环/门景边界）。fogCache 与
            // 掩膜同为 8×8 子格/瓦片（FOG_SUB==MASK_SUB），索引直接换算；
            // 该路径只在 fovVersion 变化帧运行（fogCache 恰为本帧刷新）。
            // The old world -> tile -> subcell arithmetic resolves exactly
            // to this in-bounds integer rectangle (MASK_SUB == FOG_SUB).
            this.classicLogicRegion(new Rectangle(x0,y0,x1-x0+1,y1-y0+1));
            matches=bd.threshold(this.fogCache,
               new Rectangle(FOG_PAD+x0*MASK_SUB,FOG_PAD+y0*MASK_SUB,totx,toty),
               this.fogPoint,"<",uint(MASK_LIT_A)<<24,0xFFFFFFFF,0xFF000000,false);
         }
         else
         {
            if(this.cfgAutoTest)
            {
               this.atMaskRay++;
            }
            var d2max:Number = this.locDist2 * this.locDist2;
            for(scx = 0; scx < totx; scx++)
            {
               for(scy = 0; scy < toty; scy++)
               {
                  var swx:Number = (x0 * MASK_SUB + scx + 0.5) * cs;
                  var swy:Number = (y0 * MASK_SUB + scy + 0.5) * cs;
                  var dddx:Number = swx - this.eyeX;
                  var dddy:Number = swy - this.eyeY;
                  var lit:Number = dddx * dddx + dddy * dddy <= d2max
                     ? this.castRay(this.curLoc,this.eyeX,this.eyeY,swx,swy,
                        Math.floor(swx / Tile.tileX),Math.floor(swy / Tile.tileY))
                     : -1;
                  if(lit < 0)
                  {
                     lit = this.fov[Math.floor(swx / Tile.tileX) + Math.floor(swy / Tile.tileY) * this.spaceX] != FOV_NONE ? 1 : 0;
                  }
                  if(lit > 0.0001)
                  {
                     bd.setPixel32(scx,scy,0xFFFFFFFF);
                  }
               }
            }
         }
         bd.unlock();
         // 按模式模糊（classic/current 各自对齐雾层边界宽度）；0=关闭（硬边）
         var blur:BlurFilter = this.cfgMode == "classic" ? this.maskBlurClassic : this.maskBlurCurrent;
         // Independent visuals can use native drawing / an empty shape when
         // the complete support field is uniform. Classify the samples already
         // written above; mixed fields never repeat classicLogicRegion/threshold.
         if(rec.worldRaster === true)
         {
            var dark:Boolean,uniformLit:Boolean;
            if(matches>=0){dark=matches==0;uniformLit=matches==totx*toty;}
            else {
               var first:uint=bd.getPixel32(0,0)>>>24;
               dark=first==0 && !bd.hitTest(this.fogPoint,1,bd.rect);
               uniformLit=first==255 && bd.getColorBoundsRect(0xff000000,0xff000000,false).isEmpty();
            }
            if(uniformLit && (bb[0]-x0<MASK_PAD_X || bb[1]-y0<MASK_PAD_TOP || x1-bb[2]<MASK_PAD_X || y1-bb[3]<MASK_PAD_BOTTOM
               || blur.blurX*blur.quality/2+2>MASK_PAD_X*MASK_SUB
               || blur.blurY*blur.quality/2+2>MASK_PAD_BOTTOM*MASK_SUB))uniformLit=false;
            if(dark || uniformLit){
               rec.fullyDark=dark;rec.fullyLit=uniformLit;rec.coverageFov=this.fovVersion;
               rec.maskValid=false;
               return;
            }
         }
         if(bdb==null){bdb=new BitmapData(totx,toty,true,0);rec.m2e=bdb;}
         var s2:Shape = rec.m2 as Shape;
         var s3:Shape = rec.m3 as Shape;
         if(s2 == null)
         {
            s2 = new Shape();
            rec.m2 = s2;
         }
         if(s3 == null)
         {
            s3 = new Shape();
            rec.m3 = s3;
         }
         // Every eligible sample is still refreshed above. Reuse the rendered
         // mask only when its complete input, world rectangle and filter match.
         // Display attachment/restoration above always runs, even on a hit.
         var previousInput:BitmapData = rec.maskInput as BitmapData;
         if(rec.maskValid === true && previousInput != null
            && previousInput.width == bd.width && previousInput.height == bd.height
            && rec.maskBounds == sig && rec.maskMode == this.cfgMode
            && rec.maskBlurX == blur.blurX && rec.maskBlurY == blur.blurY && rec.maskQuality == blur.quality)
         {
            var maskDelta:Object = bd.compare(previousInput);
            if(maskDelta is uint && uint(maskDelta) == 0) return;
            if(maskDelta is BitmapData) BitmapData(maskDelta).dispose();
         }
         rec.maskValid = false;
         if(blur.blurX > 0)
         {
            bdb.applyFilter(bd,bd.rect,this.fogPoint,blur);
         }
         else
         {
            bdb.copyPixels(bd,bd.rect,this.fogPoint);
         }
         if(this.cfgMode == "current")
         {
            // 只在可见侧淡出；地板的柔化不能揭露被挡住的敌人。
            this.finishCurrentMask(bd,bdb);
         }
         // 位图填充绘制进矢量 Shape（smoothing → 双线性放大），alpha 渐变即软边
         // 注：beginBitmapFill 的 matrix 不跨调用复用（可能持引用，复用会串改
         // 前一个敌人的填充）——每次新建，成本可忽略（仅 FOV 变化时调用）
         // Bitmap fill keeps the raster reference. Updating its pixels does not
         // change the fill geometry; retain body/bar/weapon shapes until the
         // world rectangle or raster allocation changes.
         if(rec.maskDrawBitmap !== bdb || rec.maskBounds != sig)
         {
         var g:flash.display.Graphics = s2.graphics;
         g.clear();
         var m:Matrix = new Matrix(cs,0,0,cs,x0 * Tile.tileX,y0 * Tile.tileY);
         g.beginBitmapFill(bdb,m,false,true);
         g.drawRect(x0 * Tile.tileX,y0 * Tile.tileY,totx * cs,toty * cs);
         g.endFill();
         s3.graphics.clear();
         s3.graphics.copyFrom(g);
         rec.maskRevision = int(rec.maskRevision)+1;
            rec.maskDrawBitmap=bdb;
         }
         if(previousInput == null || previousInput.width != bd.width || previousInput.height != bd.height)
         {
            if(previousInput != null) previousInput.dispose();
            previousInput = new BitmapData(bd.width,bd.height,true,0);
            rec.maskInput = previousInput;
         }
         previousInput.copyPixels(bd,bd.rect,this.fogPoint);
         rec.maskBounds = sig; rec.maskMode = this.cfgMode;
         rec.maskBlurX = blur.blurX; rec.maskBlurY = blur.blurY; rec.maskQuality = blur.quality;
         rec.maskValid = true;
      }

      /** Same alpha arithmetic as the pixel loop, without two temporary vectors. */
      private function finishCurrentMask(eligible:BitmapData, soft:BitmapData):void
      {
         if(this.maskAlphaMap == null)
         {
            this.maskAlphaMap=[];this.maskZeroMap=[];
            for(var i:int=0;i<256;i++)
            {
               var alpha:int=Math.max(0,2*i-255);
               this.maskAlphaMap[i]=alpha==0?0:uint((alpha<<24)|0xFFFFFF);
               this.maskZeroMap[i]=0;
            }
         }
         soft.paletteMap(soft,soft.rect,this.fogPoint,this.maskZeroMap,this.maskZeroMap,this.maskZeroMap,this.maskAlphaMap);
         soft.threshold(eligible,eligible.rect,this.fogPoint,"==",0,0,0xFFFFFFFF,false);
      }

      private function clearMask(u:Unit):void
      {
         var rec:Object = this.unitVis[u];
         if(rec == null)
         {
            return;
         }
         try
         {
            if(u.vis)
            {
               if(u.vis.mask != null)u.vis.mask = null;
               if(u.vis.cacheAsBitmap)u.vis.cacheAsBitmap = false;
            }
            if(u.hpbar)
            {
               if(u.hpbar.mask != null)u.hpbar.mask = null;
               if(u.hpbar.cacheAsBitmap)u.hpbar.cacheAsBitmap = false;
            }
         }
         catch(err:Error)
         {
         }
         // 掩膜必须移出图层：不被 mask 引用时会被当普通内容渲染（白块）
         var s2:Shape = rec.m2 as Shape;
         var s3:Shape = rec.m3 as Shape;
         if(s2 != null && s2.parent != null) { s2.parent.removeChild(s2); }
         if(s3 != null && s3.parent != null) { s3.parent.removeChild(s3); }
         rec.lastFov = -1;
      }

      /** 定期清扫：掩膜所属单位已死亡/摘除（vis 不再挂载）时移除残留掩膜位图。 */
      private function sweepMasks():void
      {
         for(var k:Object in this.unitVis)
         {
            var rec:Object = this.unitVis[k];
            if(rec == null)
            {
               continue;
            }
            var u:Unit = k as Unit;
            if(u == null)
            {
               continue;
            }
            if(rec.state == 2 && (u.vis == null || u.vis.parent == null))
            {
               this.clearMask(u);
               delete this.unitVis[k];   // 摘除条目：Shape+掩膜位图随回收
            }
         }
      }

      /** 敌人全隐：每帧强制压暗 vis 与 hpbar；prior 置 0 使游戏下一帧不再把
       *  其设为 celObj（名称标签/交互目标的上游来源）。 */
      private function hideUnit(u:Unit):void
      {
         this.hpHidden[u] = true;
         try
         {
            if(u.vis)
            {
               if(u.vis.visible)u.vis.visible = false;
            }
            if(u.hpbar)
            {
               if(u.hpbar.visible)u.hpbar.visible = false;
            }
            u.prior = 0;
         }
         catch(err:Error)
         {
         }
      }

      /** 恢复显示：hpbar 状态交给游戏 visDetails() 重算；恢复 prior 选择权重。 */
      private function showUnit(u:Unit):void
      {
         try
         {
            if(u.vis)
            {
               if(!u.vis.visible)u.vis.visible = true;
            }
            u.prior = 1;
         }
         catch(err:Error)
         {
         }
         if(this.hpHidden[u] == true)
         {
            delete this.hpHidden[u];
            try
            {
               u.visDetails();
            }
            catch(err:Error)
            {
            }
         }
      }

      private function hideEnemies(w:World, loc:Location, needFov:Boolean):void
      {
         var gg:UnitPlayer = loc.gg;
         var hiddenPos:Array = [];
         var visiblePos:Array = [];
         var exempt:Dictionary = new Dictionary(true);
         var units:Array = loc.units;
         this.weaponPass++;
         var k:int;
         if(this.cfgAutoTest)
         {
            this.atE0 = 0;
            this.atE1 = 0;
            this.atE2 = 0;
         }
         if(units != null)
         {
            for(k = 0; k < units.length; k++)
            {
               var u:Unit = units[k] as Unit;
               if(u == null)
               {
                  continue;
               }
               if(u.vis)
               {
                  exempt[u.vis] = true;
               }
               if(u.player || u.npc || u.fraction == Unit.F_PLAYER || u.invis)
               {
                  this.applyUnitWeapons(u,1,exempt);
                  visiblePos.push([u.X,u.Y]);
                  continue;
               }
               var st:int = this.enemyState(loc,u);
               if(this.cfgAutoTest)
               {
                  if(st == 0)
                  {
                     this.atE0++;
                  }
                  else if(st == 1)
                  {
                     this.atE1++;
                  }
                  else
                  {
                     this.atE2++;
                  }
               }
               if(u.sost == 4)
               {
                  this.clearMask(u);
                  this.showUnit(u);
                  this.applyUnitWeapons(u,1,exempt);
                  visiblePos.push([u.X,u.Y]);
                  continue;
               }
               // 被抓取的敌人同样遵循视野规则：拖入暗处即不可见（宽限倒计时仍在
               // enforceTele 里独立运行）
               var rec:Object = this.unitVis[u];
               if(rec == null)
               {
                  rec = {state:1,m2:null,m3:null,m2d:null,m2e:null,lastFov:-1,lastBb:""};
                  this.unitVis[u] = rec;
               }
               rec.state = st;
               if(st == 0)
               {
                  this.clearMask(u);
                  this.hideUnit(u);
                  hiddenPos.push([u.X,u.Y]);
               }
               else if(st == 1)
               {
                  this.clearMask(u);
                  this.showUnit(u);
                  visiblePos.push([u.X,u.Y]);
               }
               else
               {
                  this.showUnit(u);
                  this.applyMask(w,u,this.unitBBox(loc,u));
                  visiblePos.push([u.X,u.Y]);
               }
               this.applyUnitWeapons(u,st,exempt);
            }
         }
         // 敌方手持武器：跟随所属敌人的显示状态。
         // v0.24.7：扫描门控——fov 变化帧或每 3 帧（敌人在明暗边界移动时
         // 武器状态滞后 ≤3 帧 ≈50ms，不可察觉；省去每帧遍历整条对象链）
         if(needFov || this.frameCount % 3 == 0)
         {
            if(this.cfgAutoTest)
            {
               this.atWsEx++;
            }
            var obj:Pt = loc.firstObj;
            var guard:int = 0;
            while(obj != null && guard < 5000)
            {
               if(obj is Weapon)
               {
                  var wpn:Weapon = obj as Weapon;
                  if(wpn.vis)
                  {
                     exempt[wpn.vis] = true;
                  }
                  var owner:Unit = wpn.owner;
                  var wr:Object = wpn.vis ? this.weaponVisuals[wpn.vis] : null;
                  if(wr == null || wr.pass != this.weaponPass)
                  {
                     var wst:int = owner != null && owner != gg && !owner.player && !owner.npc && owner.fraction != Unit.F_PLAYER && !owner.invis && owner.sost < 3
                        ? this.enemyState(loc,owner) : 1;
                     this.applyWeaponVisual(wpn,owner,wst);
                  }
               }
               obj = obj.nobj;
               guard++;
            }
         }
         else if(this.cfgAutoTest)
         {
            this.atWsSk++;
         }
         // Rebuilt/removed native visuals must not retain a detached mask.
         for(var oldVisual:Object in this.weaponVisuals)
         {
            var oldRecord:Object=this.weaponVisuals[oldVisual];
            if(oldRecord.weapon.vis !== oldVisual || oldRecord.owner != oldRecord.weapon.owner || DisplayObject(oldVisual).parent == null)
               this.releaseWeaponVisual(oldVisual as DisplayObject,oldRecord);
         }
         this.applyWorldVisuals(w,loc);
      }

      private function applyUnitWeapons(u:Unit, state:int, exempt:Dictionary):void
      {
         var children:Array=Object(u)["childObjs"] as Array;
         if(children == null) return;
         for each(var child:Object in children)
         {
            var weapon:Weapon=child as Weapon;
            if(weapon == null || weapon.owner !== u) continue;
            if(weapon.vis) exempt[weapon.vis]=true;
            this.applyWeaponVisual(weapon,u,u.sost >= 3 ? 1 : state);
         }
      }

      private function applyWeaponVisual(weapon:Weapon, owner:Unit, state:int):void
      {
         var visual:DisplayObject=weapon.vis;
         if(visual == null) return;
         var record:Object=this.weaponVisuals[visual];
         if(state == 1)
         {
            if(record != null) this.releaseWeaponVisual(visual,record);
            return;
         }
         if(record == null)
         {
            record={weapon:weapon,owner:owner,visible:visual.visible,cache:visual.cacheAsBitmap,mask:visual.mask,shape:null,revision:-1,hidden:false};
            this.weaponVisuals[visual]=record;
         }
         record.pass=this.weaponPass;
         var shape:Shape=record.shape as Shape;
         if(state == 0)
         {
            if(visual.visible)visual.visible=false;record.hidden=true;
            visual.mask=record.mask;visual.cacheAsBitmap=record.cache;
            if(shape != null && shape.parent != null) shape.parent.removeChild(shape);
            return;
         }
         var unitRecord:Object=this.unitVis[owner];
         if(unitRecord == null || unitRecord.m2 == null || visual.parent == null) return;
         if(record.hidden) {visual.visible=record.visible;record.hidden=false;}
         if(shape == null) {shape=new Shape();shape.cacheAsBitmap=true;record.shape=shape;}
         if(record.revision != unitRecord.maskRevision)
         {
            shape.graphics.copyFrom(Shape(unitRecord.m2).graphics);
            record.revision=unitRecord.maskRevision;
         }
         if(shape.parent !== visual.parent) visual.parent.addChild(shape);
         // Each display object owns a mask. Only the immutable raster is shared.
         if(!visual.cacheAsBitmap)visual.cacheAsBitmap=true;if(visual.mask!==shape)visual.mask=shape;
      }

      private function releaseWeaponVisual(visual:DisplayObject, record:Object):void
      {
         if(record.hidden && (record.owner == null || record.owner.sost < 3)) visual.visible=record.visible;
         if(visual.mask === record.shape || record.hidden) visual.mask=record.mask;
         visual.cacheAsBitmap=record.cache;
         var shape:Shape=record.shape as Shape;
         if(shape != null && shape.parent != null) shape.parent.removeChild(shape);
         delete this.weaponVisuals[visual];
      }

      private function restoreWeaponVisuals():void
      {
         for(var visual:Object in this.weaponVisuals)
            this.releaseWeaponVisual(visual as DisplayObject,this.weaponVisuals[visual]);
      }

      private function setWeaponVis(wpn:Weapon, visB:Boolean):void
      {
         try
         {
            if(wpn.vis)
            {
               wpn.vis.mask = null;
               wpn.vis.cacheAsBitmap = false;   // v0.24.6：无掩膜即关缓存（防残留开销）
               if(wpn.vis.visible != visB)wpn.vis.visible = visB;
            }
         }
         catch(err:Error)
         {
         }
      }

      /** Native transient visuals are independent of their shooter. Never change
       * visible/alpha or reparent content: native animation and lifetime own them. */
      private function applyWorldVisuals(w:World,loc:Location):void
      {
         this.worldPass++;
         var obj:Pt=loc.firstObj,guard:int=0;
         while(obj != null && guard++<5000)
         {
            var cls:Object=Object(obj).constructor;
            var kind:*=this.worldTypes[cls];
            if(kind === undefined)
            {
               var name:String=getQualifiedClassName(obj);
               kind=name=="fe.graph::Part" || name=="fe.weapon::Bullet" || name=="fe.weapon::PhisBullet" || name=="fe.weapon::SmartBullet";
               this.worldTypes[cls]=kind;
            }
            if(kind && obj.vis != null)this.applyWorldVisual(obj.vis);
            obj=obj.nobj;
         }
         // UnitMerc.arm is package-internal, but its native display class is
         // unambiguous. Spatial clipping also works with overlapping mercenaries.
         if(w.grafon != null) for(var layerIndex:int=0;layerIndex<w.grafon.visObjs.length;layerIndex++)
         {
            var layer:DisplayObjectContainer=w.grafon.visObjs[layerIndex];
            // Releasing a now-fully-lit mask removes a sibling. Walk backwards
            // so that native reattachment and mask removal cannot stale length.
            for(var i:int=layer.numChildren-1;i>=0;i--)
            {
               var child:DisplayObject=layer.getChildAt(i);
               if(child is Shape)continue;
               cls=Object(child).constructor;kind=this.worldTypes[cls];
               if(kind === undefined){kind=getQualifiedClassName(child).indexOf("visualGrifArm")==0;this.worldTypes[cls]=kind;}
               if(kind)this.applyWorldVisual(child);
            }
         }
         // A fully visible body can carry a long gun beyond its own bounds.
         for each(var unit:Unit in loc.units)
         {
            if(unit == null || unit.player || unit.npc || unit.invis || unit.fraction==Unit.F_PLAYER || unit.sost>=3)continue;
            var ur:Object=this.unitVis[unit];
            if(ur == null || ur.state!=1)continue;
            var children:Array=Object(unit)["childObjs"] as Array;
            if(children == null)continue;
            for each(var entry:Object in children)
            {
               var weapon:Weapon=entry as Weapon;
               if(weapon != null && weapon.owner===unit && weapon.vis != null)this.applyWorldVisual(weapon.vis);
            }
         }
         for(var visual:Object in this.worldVisuals)
         {
            var record:Object=this.worldVisuals[visual];
            if(record.pass!=this.worldPass || DisplayObject(visual).parent==null)this.releaseWorldVisual(visual as DisplayObject,record);
         }
         if(this.worldPass%60==0)for(var key:String in this.worldMasks)
         {
            var raster:Object=this.worldMasks[key];
            if(this.worldPass-int(raster.used)>120)
            {
               this.disposeWorldMask(raster);delete this.worldMasks[key];
            }
         }
      }

      private function applyWorldVisual(visual:DisplayObject):void
      {
         if(visual.parent==null)return;
         var record:Object=this.worldVisuals[visual];
         if(record != null && visual.mask !== record.shape && visual.mask !== record.baseMask)
         {
            this.releaseWorldVisual(visual,record);record=null;
         }
         // Respect masks owned by the game or another mod. Existing native
         // projectile/particle/griffon visuals have none; unit masks stay separate.
         if(record==null && visual.mask!=null)return;
         if(!visual.visible && record==null)return;
         var bounds:Rectangle=visual.getBounds(visual.parent);
         var x0:int=Math.max(0,Math.floor(bounds.left/Tile.tileX));
         var y0:int=Math.max(0,Math.floor(bounds.top/Tile.tileY));
         var x1:int=Math.min(this.spaceX-1,Math.floor(bounds.right/Tile.tileX));
         var y1:int=Math.min(this.spaceY-1,Math.floor(bounds.bottom/Tile.tileY));
         if(x0>x1 || y0>y1)return;
         var key:String=x0+","+y0+","+x1+","+y1;
         var raster:Object=this.worldMasks[key];
         if(raster==null){raster={worldRaster:true,lastFov:-1,lastBb:"",m2:null,m3:null,m2d:null,m2e:null};this.worldMasks[key]=raster;}
         raster.used=this.worldPass;
         this.refreshMask(raster,[x0,y0,x1,y1]);
         // Leave fully lit native visuals untouched. Besides avoiding needless
         // caches, this preserves subpixel animation rendering exactly.
         if(raster.coverageFov!==this.fovVersion)
         {
            var rx:int=(x0-Math.max(0,x0-MASK_PAD_X))*MASK_SUB;
            var ry:int=(y0-Math.max(0,y0-MASK_PAD_TOP))*MASK_SUB;
            var pixels:Vector.<uint>=BitmapData(raster.m2e).getVector(new Rectangle(rx,ry,(x1-x0+1)*MASK_SUB,(y1-y0+1)*MASK_SUB));
            var lit:Boolean=true;
            for each(var pixel:uint in pixels)if((pixel>>>24)!=255){lit=false;break;}
            // Include the full support region, including any native glow, in
            // the empty-mask fast path; it is exactly zero everywhere.
            var dark:Boolean=BitmapData(raster.m2e).getColorBoundsRect(0xff000000,0,false).isEmpty();
            raster.fullyLit=lit;raster.fullyDark=dark;raster.coverageFov=this.fovVersion;
         }
         if(raster.fullyLit)
         {
            if(record!=null)this.releaseWorldVisual(visual,record);
            return;
         }
         var drawDark:Boolean=raster.fullyDark;
         if(!drawDark){
            var supportData:BitmapData=raster.m2e as BitmapData;
            var supportX:int=(x0-Math.max(0,x0-MASK_PAD_X))*MASK_SUB;
            var supportY:int=(y0-Math.max(0,y0-MASK_PAD_TOP))*MASK_SUB;
            // Keep bilinear neighbours, reusing one synchronous scratch rect.
            this.worldSupportRect.x=Math.max(0,supportX-1);
            this.worldSupportRect.y=Math.max(0,supportY-1);
            this.worldSupportRect.width=Math.min(supportData.width,supportX+(x1-x0+1)*MASK_SUB+1)-this.worldSupportRect.x;
            this.worldSupportRect.height=Math.min(supportData.height,supportY+(y1-y0+1)*MASK_SUB+1)-this.worldSupportRect.y;
            // Reading filters clones their array. Inspect that tree only when
            // the alpha test has established a possible transparent shortcut.
            if(!supportData.hitTest(this.fogPoint,1,this.worldSupportRect) && !this.worldVisualHasFilters(visual))drawDark=true;
         }
         if(record==null)
         {
            record={shape:new Shape(),baseMask:visual.mask,cache:visual.cacheAsBitmap,raster:null,revision:-1};
            this.worldVisuals[visual]=record;
         }
         record.pass=this.worldPass;
         var shape:Shape=record.shape as Shape;
         if(record.raster!==raster || record.revision!=raster.maskRevision || record.dark!==drawDark)
         {
            if(drawDark)shape.graphics.clear();
            else shape.graphics.copyFrom(Shape(raster.m2).graphics);
            record.raster=raster;record.revision=raster.maskRevision;record.dark=drawDark;
         }
         if(shape.parent!==visual.parent)visual.parent.addChild(shape);
         if(shape.cacheAsBitmap!==!drawDark)shape.cacheAsBitmap=!drawDark;
         var useCache:Boolean=drawDark?record.cache:true;
         if(visual.cacheAsBitmap!==useCache)visual.cacheAsBitmap=useCache;
         if(visual.mask!==shape)visual.mask=shape;
      }

      private function worldVisualHasFilters(visual:DisplayObject):Boolean
      {
         if(visual.filters.length>0)return true;
         var container:DisplayObjectContainer=visual as DisplayObjectContainer;
         if(container!=null)for(var i:int=0;i<container.numChildren;i++)
            if(this.worldVisualHasFilters(container.getChildAt(i)))return true;
         return false;
      }

      private function releaseWorldVisual(visual:DisplayObject,record:Object):void
      {
         if(visual.mask===record.shape){visual.mask=record.baseMask;visual.cacheAsBitmap=record.cache;}
         var shape:Shape=record.shape as Shape;
         if(shape.parent!=null)shape.parent.removeChild(shape);
         delete this.worldVisuals[visual];
      }
      private function disposeWorldMask(record:Object):void
      {
         for each(var key:String in ["m2d","m2e","maskInput"])
            if(record[key] != null)BitmapData(record[key]).dispose();
      }
      private function restoreWorldVisuals():void
      {
         for(var visual:Object in this.worldVisuals)this.releaseWorldVisual(visual as DisplayObject,this.worldVisuals[visual]);
         for each(var raster:Object in this.worldMasks)this.disposeWorldMask(raster);
         this.worldMasks={};this.worldPass=0;
      }

      // ==================== 念力规则 ====================

      private function enforceTele(loc:Location):void
      {
         var gg:UnitPlayer = loc.gg;
         if(gg == null)
         {
            return;
         }
         var t:* = gg.teleObj;
         if(t == null || !(t is Unit) || t === gg)
         {
            this.teleGraceFrames = 0;
            this.teleLast = null;
            return;
         }
         if(t !== this.teleLast)
         {
            this.teleLast = t;
            this.teleGraceFrames = 0;
            if(this.cfgAutoTest)
            {
               this.fileLog("auto tele grab id=" + (t as Unit).id
                  + " st=" + this.enemyState(loc,t as Unit));
            }
         }
         var u:Unit = t as Unit;
         if(u.fraction == Unit.F_PLAYER)
         {
            return;
         }
         if(this.enemyState(loc,u) == 0)
         {
            this.teleGraceFrames++;
            var max:int = this.cfgTeleGrace * World.fps;
            if(max < 1)
            {
               max = 1;
            }
            if(this.teleGraceFrames >= max)
            {
               this.teleGraceFrames = 0;
               if(this.cfgAutoTest)
               {
                  this.fileLog("auto tele expire id=" + u.id
                     + " after " + max + "f -> dropTeleObj");
               }
               gg.dropTeleObj();
            }
         }
         else
         {
            if(this.cfgAutoTest && this.teleGraceFrames > 0)
            {
               this.fileLog("auto tele release id=" + u.id
                  + " graceFrames=" + this.teleGraceFrames);
            }
            this.teleGraceFrames = 0;
         }
      }

      // ==================== 设置界面（哔哔小马选项页） ====================

      /** 渲染模式轮换（F12 与选项页注入行共用）：vanilla → classic → current。 */
      private function cycleMode():void
      {
         this.cfgMode = this.cfgMode == "vanilla" ? "classic"
            : (this.cfgMode == "classic" ? "current" : "vanilla");
         this.saveConfig();
         this.curLoc = null;
         this.errCount = 0;
         this.showToast();
         trace("[RVision] mode=" + this.cfgMode);
         if(this.cfgAutoTest)
         {
            this.fileLog("auto mode -> " + this.cfgMode);
         }
      }

      /** 模式显示名。 */
      private function modeName():String
      {
         return this.cfgMode == "vanilla" ? "原版"
            : (this.cfgMode == "classic" ? "仿原版" : "平滑阴影");
      }

      /** 实际切换模式时，在左上角提示3秒；菜单/无房间时同样会到期。 */
      private function showToast():void
      {
         var w:World = World.w;
         if(w == null || w.main == null)
         {
            return;
         }
         if(this.toastTxt == null)
         {
            this.toastTxt = new TextField();
            this.toastTxt.autoSize = TextFieldAutoSize.LEFT;
            this.toastTxt.background = true;
            this.toastTxt.backgroundColor = 0;
            this.toastTxt.textColor = 0xFFFFFF;
            this.toastTxt.selectable = false;
            this.toastTxt.mouseEnabled = false;
            w.main.addChild(this.toastTxt);
         }
         RVLocale.bind(this.toastTxt,"视野渲染模式: " + this.modeName()
            + (this.cfgEnabled ? "" : "（已停用）"));
         this.toastTxt.x = 16;
         this.toastTxt.y = 16;
         this.toastTxt.visible = true;
         this.toastUntil = getTimer() + 3000;
      }

      private function updateToast(now:int):void
      {
         if(this.toastTxt != null && this.toastTxt.visible && now >= this.toastUntil)
         {
            this.toastTxt.visible = false;
         }
      }

      /**
       * 哔哔小马选项页（fe.inter::PipPageOpt）打开时，在界面左下角显示本模组
       * 开关面板（F11 切换，与页面自身按键导航不冲突）。
       */
      private function updateOptPanel(w:World):void
      {
         var onOpt:Boolean = false;
         try
         {
            if(w.pip != null && w.pip.active && w.pip.currentPage != null
               && getQualifiedClassName(w.pip.currentPage) == "fe.inter::PipPageOpt")
            {
               onOpt = true;
            }
         }
         catch(err:Error)
         {
         }
         if(onOpt)
         {
            this.ensureOptPanel(w);
            var txt:String = "RealisticVision 视野系统: " + (this.cfgEnabled ? "开启" : "关闭")
               + "  模式: " + this.modeName()
               + (this.cfgEnabled && !w.black ? "\n（游戏黑暗选项已关闭，模组暂不生效）" : "")
               + "\nF11 开关 / F12 或点击上方列表行换模式";
            if(this.optTxt.text != txt)
            {
               RVLocale.bind(this.optTxt,this.keybinds.hint(txt),true);
            }
            this.optPanel.visible = true;
            // v0.25.0：向选项页原生列表注入"视野渲染模式"行（点击循环）
            this.ensureOptRow(w);
            if(this.optRow != null)
            {
               // 锚点行 id=="fullscreen" 仅在系统选项子卡存在——其余子卡隐藏本行
               var tab:Boolean = this.optRowAnchor != null
                  && this.optRowAnchor.hasOwnProperty("parent")
                  && this.optRowAnchor["parent"] != null
                  && this.optRowAnchor["id"] is TextField
                  && this.optRowAnchor["id"].text == "fullscreen";
               this.optRow.visible = tab;
               if(tab)
               {
                  var numTxt:String = this.modeName() + (this.cfgEnabled ? "" : "（停用）");
                  if(this.optRow["numb"].text != numTxt)
                  {
                     RVLocale.bind(this.optRow["numb"] as TextField,numTxt,true);
                  }
               }
            }
         }
         else if(this.optPanel != null && this.optPanel.visible)
         {
            this.optPanel.visible = false;
            if(this.optRow != null)
            {
               this.optRow.visible = false;
            }
         }
      }

      /**
       * v0.25.0：向哔哔小马选项页（PipPageOpt）的原生选项列表注入一行
       * "视野渲染模式"，点击循环 vanilla → classic → current。
       * 做法：DFS 找到原生行（id 文本 == "fullscreen"，选项子卡的锚点行），
       * 用 Object(row).constructor 实例化同类行（原生 visPipOptItem，观感
       * 与导航样式一致），按 setStatItem(page2==3) 的填充规则隐藏 check/scr/
       * key 等子件，放到列表最后一条已填充行的下一格。任何失败静默降级
       * （左下面板与 F12 仍可用）。行不参与原生键盘导航/滚动（选项子卡
       * 15 条 < 18 行容量，无滚动），仅鼠标点击。
       */
      private function ensureOptRow(w:World):void
      {
         if(this.optRow != null && this.optRow["parent"] != null)
         {
            return;
         }
         try
         {
            var anchor:Object = this.findRowById(w.main,"fullscreen",0);
            if(anchor == null)
            {
               return;
            }
            var host:DisplayObjectContainer = anchor["parent"] as DisplayObjectContainer;
            if(host == null)
            {
               return;
            }
            var cls:Class = anchor["constructor"] as Class;
            var row:Object = new cls();
            // 填充规则照抄 PipPageOpt.setStatItem(page2==3) 的行初始化
            row["id"].visible = false;
            row["scr"].visible = false;
            row["check"].visible = false;
            row["key1"].visible = false;
            row["key2"].visible = false;
            row["ramka"].visible = false;
            row["land"].text = "";
            row["ggName"].text = "";
            RVLocale.bind(row["nazv"] as TextField,"视野渲染模式",true);
            RVLocale.bind(row["numb"] as TextField,this.modeName(),true);
            // 放到列表最后一条已填充行（id 文本非空）的下一格（行距 30）
            var lastY:Number = anchor["y"];
            var cnt:int = host.numChildren;
            var ci:int;
            for(ci = 0; ci < cnt; ci++)
            {
               var sib:DisplayObject = host.getChildAt(ci);
               if(sib.hasOwnProperty("id") && sib.hasOwnProperty("nazv")
                  && sib["id"] is TextField && sib["id"].text != "")
               {
                  if(sib["y"] > lastY)
                  {
                     lastY = sib["y"];
                  }
               }
            }
            row["x"] = anchor["x"];
            row["y"] = lastY + 30;
            row["buttonMode"] = true;
            row.addEventListener(MouseEvent.CLICK,this.onOptRowClick);
            host.addChild(row as DisplayObject);
            this.optRow = row;
            this.optRowAnchor = anchor;
            this.fileLog("optRow injected y=" + row["y"]);
         }
         catch(err:Error)
         {
            this.fileLog("optRow inject failed: " + err);
            this.optRow = null;
            this.optRowAnchor = null;
         }
      }

      /** 深度优先在显示树中找带 id 文本框且文本==idStr 的行（哔哔小马行是动态 MovieClip）。 */
      private function findRowById(node:DisplayObject,idStr:String,depth:int):Object
      {
         if(node == null || depth > 10)
         {
            return null;
         }
         try
         {
            if(node.hasOwnProperty("id") && node.hasOwnProperty("nazv")
               && node["id"] is TextField && node["id"].text == idStr && node.visible)
            {
               return node;
            }
         }
         catch(err:Error)
         {
         }
         if(node is DisplayObjectContainer)
         {
            var c:int = (node as DisplayObjectContainer).numChildren;
            var i:int;
            for(i = 0; i < c; i++)
            {
               var r:Object = this.findRowById((node as DisplayObjectContainer).getChildAt(i),idStr,depth + 1);
               if(r != null)
               {
                  return r;
               }
            }
         }
         return null;
      }

      /** 点击注入行：循环渲染模式（行内文本随 updateOptPanel 刷新）。 */
      private function onOptRowClick(e:MouseEvent):void
      {
         this.cycleMode();
         if(this.optRow != null)
         {
            RVLocale.bind(this.optRow["numb"] as TextField,this.modeName() + (this.cfgEnabled ? "" : "（停用）"),true);
         }
      }

      // ==================== MSW 模组设置聚合页（v0.26.0） ====================

      private static const MODES:Array = ["vanilla", "classic", "current"];

      /** Register with independent ModSettings. Config and existing hotkeys stay local.
       * Poll every 30 frames until the host is available, irrespective of loader order.
       */
      private function tryMswRegister(w:World):void
      {
         this.mswRetryFrames++;
         if(this.mswRetryFrames % 30 != 0)
         {
            return;
         }
         try
         {
            var mainC:DisplayObjectContainer = w.main;
            if(mainC == null)
            {
               return;
            }
            var carrier:DisplayObject = mainC.getChildByName("ModSettingsCarrier");
            if(carrier == null)
            {
               return;
            }
            var api:Object = carrier["modAPI"];
            if(api == null)
            {
               return;
            }
            var pageArgs:Array = ["realisticvision", "RealisticVision 视野系统",
               this.buildMswItems(), this.mswPageClose, "视野渲染：三态视野/记忆暗色/念力宽限"];
            if("localizationVersion" in api) pageArgs.push({translate:RVLocale.render});
            api["registerPage"].apply(api, pageArgs);
            this.mswRegistered = true;
            this.fileLog("ModSettings settings registered");
         }
         catch(err:Error)
         {
            if(!this.mswFailLogged)
            {
               this.mswFailLogged = true;
               this.fileLog("ModSettings register failed (will retry): " + err);
            }
         }
      }

      private function buildMswItems():Array
      {
         var self:RealisticVisionMod = this;
         var items:Array = [];
         items[items.length] = {"key":"enabled","label":"视野系统","kind":"check",
            "min":0,"max":1,"step":1,"hint":"总开关；快捷键可在本模组的快捷键页修改","def":true,
            "get":function():* { return self.cfgEnabled; },
            "set":function(v:*):void { self.setEnabled(v == true); }};
         items[items.length] = {"key":"mode","label":"渲染模式","kind":"slider",
            "min":0,"max":2,"step":1,"hint":"0=原版 1=仿原版 2=平滑阴影","def":2,
            "get":function():* { return self.modeIndex(); },
            "set":function(v:*):void { self.setModeIndex(int(v)); }};
         items[items.length] = {"key":"wallbright","label":"已探索墙边常亮","kind":"check",
            "min":0,"max":1,"step":1,"hint":"关闭后墙面随视野变暗；两种模式始终修正墙边阴影","def":false,
            "get":function():* { return self.cfgWallBright; },
            "set":function(v:*):void { self.setWallBright(v == true); }};
         items[items.length] = {"key":"dim","label":"已探索区域亮度","kind":"slider",
            "min":0,"max":1,"step":0.05,"hint":"视野外已探索区域：0=全黑，1=最亮；不会显示隐藏敌人","def":0.35,
            "get":function():* { return self.cfgDim; },
            "set":function(v:*):void { self.setVisualSetting("dim",v); }};
         items[items.length] = {"key":"viewscale","label":"最大视距倍率","kind":"slider",
            "min":0.5,"max":3,"step":0.25,"hint":"1=房间默认；仍受墙门遮挡；扩大视距会保留探索记忆","def":1,
            "get":function():* { return self.cfgViewScale; },
            "set":function(v:*):void { self.setVisualSetting("viewscale",v); }};
         items[items.length] = {"key":"soft_current","label":"平滑阴影渐变宽度","kind":"slider",
            "min":0,"max":60,"step":5,"hint":"仅平滑阴影：0=硬边，20=原效果；数值为柔化尺度（像素）","def":20,
            "get":function():* { return self.cfgSoftCurrent; },
            "set":function(v:*):void { self.setVisualSetting("soft_current",v); }};
         items[items.length] = {"key":"soft_classic","label":"仿原版额外柔化","kind":"slider",
            "min":0,"max":40,"step":5,"hint":"仅仿原版：0=原效果；保留墙内渐变，不扩大可见范围","def":0,
            "get":function():* { return self.cfgSoftClassic; },
            "set":function(v:*):void { self.setVisualSetting("soft_classic",v); }};
         items[items.length] = {"key":"doordim","label":"透光门亮度","kind":"slider",
            "min":0,"max":1,"step":0.05,"hint":"门/水后的视野亮度","def":0.5,
            "get":function():* { return self.cfgDoorDim; },
            "set":function(v:*):void { self.cfgDoorDim = Number(v); }};
         items[items.length] = {"key":"litmin","label":"可见阈值","kind":"slider",
            "min":0,"max":1,"step":0.05,"hint":"低于此亮度视为暗区","def":0.6,
            "get":function():* { return self.cfgLitMin; },
            "set":function(v:*):void { self.cfgLitMin = Number(v); }};
         items[items.length] = {"key":"fadestep","label":"淡入速度","kind":"slider",
            "min":0,"max":1,"step":0.05,"hint":"进视野渐亮速度","def":0.1,
            "get":function():* { return self.cfgFadeStep; },
            "set":function(v:*):void { self.cfgFadeStep = Number(v); }};
         items[items.length] = {"key":"telegrace","label":"念力宽限(秒)","kind":"slider",
            "min":0,"max":10,"step":1,"hint":"拖敌出视野后多久脱手","def":3,
            "get":function():* { return self.cfgTeleGrace; },
            "set":function(v:*):void { self.cfgTeleGrace = Number(v); }};
         return items;
      }

      private function setWallBright(v:Boolean):void
      {
         if(this.cfgWallBright == v) return;
         this.cfgWallBright = v;
         this.saveConfig();
      }

      /** 总开关（与 F11 同路径：落盘 + 重建视野状态）。 */
      private function setEnabled(v:Boolean):void
      {
         this.cfgEnabled = v;
         this.saveConfig();
         this.curLoc = null;
         this.errCount = 0;
      }

      /** 渲染模式索引：0=vanilla 1=classic 2=current。 */
      private function modeIndex():int
      {
         if(this.cfgMode == "classic")
         {
            return 1;
         }
         if(this.cfgMode == "current")
         {
            return 2;
         }
         return 0;
      }

      private function setModeIndex(v:int):void
      {
         if(v < 0 || v > 2)
         {
            return;
         }
         if(this.cfgMode == MODES[v])
         {
            return;
         }
         this.cfgMode = MODES[v];
         this.saveConfig();
         this.curLoc = null;
         this.errCount = 0;
         this.showToast();
         if(this.cfgAutoTest)
         {
            this.fileLog("auto msw mode -> " + this.cfgMode);
         }
      }

      /** 聚合页收起：滑块改动统一落盘（MSW 契约 onPageClose）。 */
      private function mswPageClose():void
      {
         this.saveConfig();
      }

      private function ensureOptPanel(w:World):void
      {
         if(this.optPanel != null)
         {
            return;
         }
         if(w.main == null)
         {
            return;
         }
         this.optPanel = new Sprite();
         this.optPanel.mouseEnabled = false;
         this.optPanel.mouseChildren = false;
         this.optPanel.graphics.beginFill(0x000000,0.78);
         this.optPanel.graphics.drawRect(0,0,340,52);
         this.optPanel.graphics.endFill();
         this.optTxt = new TextField();
         this.optTxt.textColor = 0xEEEEEE;
         this.optTxt.x = 10;
         this.optTxt.y = 6;
         this.optTxt.width = 320;
         this.optTxt.height = 44;
         this.optTxt.wordWrap = true;
         this.optTxt.selectable = false;
         this.optPanel.addChild(this.optTxt);
         w.main.addChild(this.optPanel);
         this.optPanel.x = 16;
         this.optPanel.y = (this.stageRef != null ? this.stageRef.stageHeight : 800) - 68;
      }

      // ==================== 调试 ====================

      private function debugStep(w:World, loc:Location, normal:Boolean):void
      {
         // v0.24.8：移除本函数原有的 frameCount++（与 onFrame 的 ++ 形成双
         // 递增）——双递增使 frameCount 每渲染帧 +2、奇偶恒定，classic 的
         // 30Hz 门控（fc&1）因此恒全开或恒全关（自动化验证实测 cls=150/0，
         // 优化失效），fov 30 帧兜底退化为每 15 帧。移除后各 %N 门槛恢复
         // 设计语义（门控真 30Hz、兜底真 30 帧、tick 真 3 秒）
         if(!this.dbgOn)
         {
            if(this.dbgTxt)
            {
               this.dbgTxt.visible = false;
            }
            return;
         }
         if(this.frameCount % 15 != 0)
         {
            return;
         }
         if(this.dbgTxt == null)
         {
            if(w.main == null)
            {
               return;
            }
            this.dbgTxt = new TextField();
            this.dbgTxt.autoSize = TextFieldAutoSize.LEFT;
            this.dbgTxt.background = true;
            this.dbgTxt.backgroundColor = 0;
            this.dbgTxt.textColor = 0xEEEEEE;
            this.dbgTxt.x = 8;
            this.dbgTxt.y = 8;
            w.main.addChild(this.dbgTxt);
         }
         var msg:String = "RVision " + loc.id + " mode=" + this.modeName();
         if(normal)
         {
            msg += "\nmode=NORMAL (F11 开关 / F12 换模式)";
         }
         else
         {
            var nVis:int = 0;
            var nDim:int = 0;
            var nUnex:int = 0;
            var n:int = this.fov.length;
            var i:int;
            for(i = 0; i < n; i++)
            {
               if(this.fov[i] == FOV_VISIBLE)
               {
                  nVis++;
               }
               else if(this.explored[i] == 1)
               {
                  nDim++;
               }
               else
               {
                  nUnex++;
               }
            }
            msg += "\nvisible=" + nVis + " dim=" + nDim + " unex=" + nUnex
               + "\ngrace=" + (this.teleGraceFrames / World.fps).toFixed(1) + "s"
               + " frame=" + this.lastFrameMs + "ms"
               + "\nF10 面板 / F11 开关";
         }
         this.dbgTxt.visible = true;
         RVLocale.bind(this.dbgTxt,this.keybinds.hint(msg));
      }
   }
}
