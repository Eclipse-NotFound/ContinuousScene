package fe.unit
{
   import fe.*;
   import fe.loc.Location;
   import fe.loc.Tile;
   import fe.serv.Interact;
   import fe.weapon.Bullet;
   import fe.weapon.Weapon;
   
   public class UnitTurret extends Unit
   {
      
      public var tr:int;
      
      internal var osnova:Tile;
      
      internal var turrettip:int = 0;
      
      internal var hidden:int = 0;
      
      internal var sleep:Boolean = false;
      
      internal var reprog:Boolean = false;
      
      internal var actDrot:Number = 0.1;
      
      internal var noTurn:Boolean = false;
      
      internal var absVis:Boolean = false;
      
      internal var watchDrot:Number = 0.015;
      
      internal var period:int = 120;
      
      internal var aRot:Array;
      
      internal var nRot:int = 0;
      
      internal var mxml:XML;
      
      internal var angle:String;
      
      public function UnitTurret(param1:String = null, param2:Number = 100, param3:XML = null, param4:Object = null)
      {
         super(param1,param2,param3,param4);
         if(Boolean(param4) && Boolean(param4.tr))
         {
            this.tr = param4.tr;
         }
         else if(Boolean(param3) && Boolean(param3.@tr.length()))
         {
            this.tr = param3.@tr;
         }
         else if(param2 < 10)
         {
            this.tr = Math.floor(Math.random() * 3 + 1);
         }
         else if(param2 < 15)
         {
            this.tr = Math.floor(Math.random() * 5 + 1);
         }
         else
         {
            this.tr = Math.floor(Math.random() * 7 + 1);
         }
         if(param1 == "land")
         {
            this.turrettip = 1;
         }
         if(param1 == "arm")
         {
            this.turrettip = 3;
         }
         if(param1 == "wall")
         {
            this.turrettip = 2;
         }
         if(param1 == "hidden")
         {
            this.hidden = 1;
         }
         if(param1 == "hidden2")
         {
            this.hidden = 2;
         }
         if(param1 == "combat")
         {
            this.turrettip = 4;
         }
         if(param1 == "boss")
         {
            this.turrettip = 5;
         }
         id = "turret" + this.turrettip;
         if(this.turrettip == 0)
         {
            vis = new visualTurret0();
         }
         else if(this.turrettip == 1)
         {
            vis = new visualTurret1();
         }
         else if(this.turrettip == 2)
         {
            vis = new visualTurret2();
         }
         else if(this.turrettip == 3)
         {
            vis = new visualTurret3();
         }
         else if(this.turrettip == 4)
         {
            vis = new visualTurret4();
         }
         else if(this.turrettip == 5)
         {
            vis = new visualTurret5();
         }
         vis.stop();
         getXmlParam();
         if(this.turrettip == 5)
         {
            invulner = true;
            this.absVis = true;
         }
         currentWeapon = new Weapon(this,"turret" + this.tr);
         childObjs = new Array(currentWeapon);
         mat = 1;
         currentWeapon.rot = currentWeapon.forceRot;
         currentWeapon.auto = true;
         currentWeapon.hold = currentWeapon.holder;
         if(Boolean(param3) && Boolean(param3.move.length()))
         {
            this.mxml = param3;
         }
         if(Boolean(param3) && Boolean(param3.@vis.length()))
         {
            this.angle = param3.@vis;
         }
         if(Boolean(param3) && Boolean(param3.@fraction.length()))
         {
            fraction = param3.@fraction;
         }
         if(Boolean(param3) && Boolean(param3.@hidden.length()))
         {
            this.hidden = param3.@hidden;
         }
         if(this.turrettip != 3)
         {
            acidDey = 1;
         }
         if(fraction == F_PLAYER)
         {
            warn = 0;
         }
         if(Boolean(param4) && Boolean(param4.off))
         {
            this.hack(0);
         }
         if(Boolean(param4) && Boolean(param4.reprog))
         {
            this.hack(1);
         }
      }
      
      override public function save() : Object
      {
         var _loc1_:Object = super.save();
         if(_loc1_ == null)
         {
            _loc1_ = new Object();
         }
         _loc1_.tr = this.tr;
         _loc1_.off = this.sleep;
         _loc1_.reprog = this.reprog;
         return _loc1_;
      }
      
      override public function putLoc(param1:Location, param2:Number, param3:Number) : *
      {
         super.putLoc(param1,param2,param3);
         if(this.mxml)
         {
            inter = new Interact(this,null,this.mxml,null);
         }
         if(this.turrettip == 0 || this.turrettip == 4)
         {
            currentWeapon.fixRot = 1;
            this.aRot = [30,150];
            if(this.turrettip == 4)
            {
               this.period = 80;
               this.watchDrot = 0.05;
            }
         }
         else if(this.turrettip == 1)
         {
            this.aRot = [-15,-165];
            this.watchDrot = 0.1;
         }
         else if(this.turrettip == 2 || this.turrettip == 5)
         {
            this.aRot = [45,135,-135,-45];
            vKonus = Math.PI / 2;
            if(loc.mirror)
            {
               if(this.angle == "left")
               {
                  this.angle = "right";
               }
               else if(this.angle == "right")
               {
                  this.angle = "left";
               }
            }
            if(this.angle == "down")
            {
               this.aRot = [45,135];
            }
            if(this.angle == "up")
            {
               this.aRot = [-45,-135];
            }
            if(this.angle == "left")
            {
               this.aRot = [135,-135];
            }
            if(this.angle == "right")
            {
               this.aRot = [45,-45];
            }
         }
         else if(this.turrettip == 3)
         {
            if(storona > 0)
            {
               this.aRot = [-15,15];
               currentWeapon.fixRot = 2;
               vAngle = 0;
            }
            else
            {
               this.aRot = [-165,165];
               currentWeapon.fixRot = 3;
               vAngle = Math.PI;
            }
            this.watchDrot = 0.01;
            vKonus = Math.PI / 4;
            this.noTurn = true;
            vis.osn.t1.scaleX = vis.osn.t2.scaleX = vis.osn.t3.scaleX = storona;
         }
         this.nRot = Math.floor(Math.random() * this.aRot.length);
         currentWeapon.rot = currentWeapon.forceRot = this.aRot[this.nRot];
         currentWeapon.findCel = false;
         aiState = 1;
         if(this.hidden > 0)
         {
            currentWeapon.rot = currentWeapon.forceRot = Math.PI / 2;
            aiState = 0;
            vis.osn.gotoAndStop(6);
         }
         try
         {
            vis.osn.puha.gotoAndStop(this.tr);
         }
         catch(err:*)
         {
         }
      }
      
      override public function setLevel(param1:int = 0) : *
      {
         level += param1;
         if(level < 0)
         {
            level = 0;
         }
         hp = maxhp = hp * (1 + level * 0.2);
         critCh = level * 0.01;
         armor *= 1 + level * 0.1;
         marmor *= 1 + level * 0.1;
         skin *= 1 + level * 0.1;
         armor_hp = armor_maxhp = armor_hp * (1 + level * 0.2);
         observ += Math.min(param1,20) * (0.8 + Math.random() * 0.4);
         currentWeapon.damage *= 1 + level * 0.12;
      }
      
      override public function setVisPos() : *
      {
         vis.x = X;
         vis.y = Y;
      }
      
      override public function animate() : *
      {
         try
         {
            if(vis.osn.puha.currentFrame != this.tr)vis.osn.puha.gotoAndStop(this.tr);
            if(fixed && Boolean(levit))
            {
               vis.osn.rotation = Math.random() * 6 - 3;
            }
            else if(vis.osn.rotation != 0)
            {
               vis.osn.rotation = 0;
            }
            if(vis.osn.currentFrame == 1)
            {
               vis.osn.puha.rotation = currentWeapon.rot * 180 / Math.PI;
               if(vis.osn.light.currentFrame != aiState + 1)
               {
                  vis.osn.light.gotoAndStop(aiState + 1);
               }
               if(isShoot)
               {
                  isShoot = false;
                  vis.osn.puha.puha.gotoAndPlay(2);
               }
               if(Boolean(aiState == 0) && Boolean(this.hidden) && fixed)
               {
                  vis.osn.gotoAndPlay(2);
               }
            }
            else if(vis.osn.currentFrame == 6 && aiState > 0)
            {
               vis.osn.gotoAndPlay(7);
            }
         }
         catch(err:*)
         {
         }
      }
      
      override public function setPos(param1:Number, param2:Number) : *
      {
         super.setPos(param1,param2);
         if((Boolean(this.turrettip == 0 || this.turrettip == 4)) && Boolean(loc) && !loc.active)
         {
            this.osnova = loc.getAbsTile(X,Y - 50);
         }
      }
      
      override public function alarma(param1:Number = -1, param2:Number = -1) : *
      {
         var _loc3_:* = undefined;
         super.alarma(param1,param2);
         if(this.turrettip == 3)
         {
            return;
         }
         if(sost == 1 && !this.sleep)
         {
            ear = 10;
            _loc3_ = vKonus;
            vKonus = 0;
            this.findCel();
            vKonus = _loc3_;
            ear = 0;
            aiSpok = maxSpok + 10;
            aiState = 3;
         }
      }
      
      override public function setNull(param1:Boolean = false) : *
      {
         super.setNull(param1);
         if(param1 && !this.sleep)
         {
            if(this.hidden)
            {
               aiState = 0;
            }
            else
            {
               aiState = 1;
            }
            if(aiState == 0)
            {
               vis.osn.gotoAndStop(6);
            }
            aiTCh = Math.floor(Math.random() * 10) + 5;
         }
      }
      
      override public function hack(param1:int = 0) : *
      {
         if(param1 == 0)
         {
            this.sleep = true;
            aiState = 0;
            currentWeapon.forceRot = Math.PI / 2;
            currentWeapon.findCel = false;
         }
         else if(param1 == 1)
         {
            this.reprog = true;
            if(fraction != Unit.F_PLAYER && xp > 0 && Boolean(loc))
            {
               loc.takeXP(xp,X,Y,true);
            }
            fraction = Unit.F_PLAYER;
            xp = 0;
            aiState = 1;
            aiSpok = 0;
            celUnit = null;
         }
         else if(param1 == 2)
         {
            this.reprog = true;
            fraction = Unit.F_PLAYER;
            xp = 0;
         }
         warn = 0;
      }
      
      override public function expl() : *
      {
         newPart("metal",4);
         newPart("miniexpl");
      }
      
      override public function setWeaponPos(param1:int = 0) : *
      {
         weaponX = X;
         if(this.turrettip == 0 || this.turrettip == 4)
         {
            weaponY = Y - 12;
         }
         else if(this.turrettip == 1)
         {
            weaponY = Y - 60;
         }
         else if(this.turrettip == 2 || this.turrettip == 5)
         {
            weaponY = Y - 20;
         }
         else if(this.turrettip == 3)
         {
            weaponY = Y - 55;
         }
      }
      
      override public function otryv() : *
      {
         if(this.turrettip == 5)
         {
            return;
         }
         if(this.turrettip == 0 || this.turrettip == 2 || this.turrettip == 4)
         {
            newPart("iskr_bul",20);
            this.sleep = true;
            aiState = 0;
            currentWeapon.findCel = false;
            warn = 0;
            if(xp > 0)
            {
               loc.takeXP(xp,X,Y,true);
            }
            xp = 0;
         }
         fixed = false;
      }
      
      override public function command(param1:String, param2:String = null) : *
      {
         var _loc3_:Array = null;
         var _loc4_:* = undefined;
         var _loc5_:* = undefined;
         if(param1 == "shoot")
         {
            currentWeapon.attack();
         }
         if(param1 == "alarma")
         {
            this.alarma();
         }
         if(param1 == "hack")
         {
            this.hack();
         }
         if(param1 == "port")
         {
            _loc3_ = param2.split(":");
            _loc4_ = (int(_loc3_[0]) + 0.5) * World.tileX;
            _loc5_ = (int(_loc3_[1]) + 1) * World.tileY;
            teleport(_loc4_,_loc5_,1);
            aiState = 2;
            aiTCh = 60;
         }
      }
      
      override public function damage(param1:Number, param2:int, param3:Bullet = null, param4:Boolean = false) : Number
      {
         var _loc6_:Weapon = null;
         if(this.turrettip == 3)
         {
            shithp = 1000;
            shitArmor = 25;
            if(param3)
            {
               if(param3.weap != null && param3.weap.tip == 1)
               {
                  _loc6_ = param3.weap;
                  if((X - _loc6_.X) * storona > 25)
                  {
                     shitArmor = 0;
                  }
               }
               else if(param3.dx * storona > 0)
               {
                  shitArmor = 0;
               }
            }
         }
         var _loc5_:Number = super.damage(param1,param2,param3,param4);
         if(this.turrettip == 3)
         {
            shithp = 0;
            shitArmor = 0;
         }
         return _loc5_;
      }
      
      override public function findCel(param1:Boolean = false) : Boolean
      {
         var _loc2_:Unit = null;
         var _loc3_:Unit = null;
         if(this.absVis && loc == World.w.loc && !this.reprog && !this.sleep)
         {
            setCel(World.w.gg);
            return true;
         }
         if(!this.reprog)
         {
            return super.findCel(param1);
         }
         if(oduplenie > 0)
         {
            return false;
         }
         if(Boolean(priorUnit && isMeet(priorUnit) && priorUnit.sost < 3) && Boolean(priorUnit.hp > 0) && !priorUnit.doop)
         {
            setCel(priorUnit);
            return true;
         }
         for each(_loc3_ in loc.units)
         {
            if(!(_loc3_.disabled || _loc3_.sost >= 3 || _loc3_.fraction == fraction || _loc3_.doop || _loc3_.invis))
            {
               if(look(_loc3_))
               {
                  setCel(_loc3_);
                  return true;
               }
            }
         }
         celUnit = priorUnit = null;
         return false;
      }
      
      override public function control() : *
      {
         if(Boolean(levit) && Boolean(!this.reprog) || !stay && !fixed && oduplenie <= 0)
         {
            if(aiState <= 1 && !this.sleep)
            {
               aiState = 3;
            }
         }
         levitPoss = !this.hidden;
         if(World.w.enemyAct <= 0 || this.sleep)
         {
            return;
         }
         if(aiTCh > 0)
         {
            --aiTCh;
         }
         else if(aiState == 2)
         {
            if(celUnit)
            {
               aiSpok = maxSpok + 10;
               aiState = 3;
               budilo(750);
            }
            else
            {
               aiState = 1;
            }
         }
         else
         {
            if(aiSpok <= 0)
            {
               if(aiState == 1 && Boolean(this.hidden))
               {
                  aiState = 0;
                  currentWeapon.forceRot = Math.PI / 2;
               }
               else if(aiState > 0)
               {
                  aiState = 1;
               }
               if(aiState == 1)
               {
                  ++this.nRot;
                  if(this.nRot >= this.aRot.length)
                  {
                     this.nRot = 0;
                  }
                  currentWeapon.forceRot = this.aRot[this.nRot] * Math.PI / 180;
               }
               aiTCh = this.period;
            }
            else
            {
               aiTCh = Math.floor(Math.random() * 50) + 40;
            }
            if(aiSpok > 0)
            {
               aiState = 4;
            }
            if(aiSpok >= maxSpok)
            {
               aiState = 3;
            }
         }
         if(Boolean(!this.reprog && aiTCh % 15 == 1) && Boolean(findLevit()) && celUnit != loc.gg)
         {
            if(Boolean(loc.gg.teleObj) && loc.gg.teleObj is Mine)
            {
               priorUnit = loc.gg.teleObj as Mine;
               aiSpok = maxSpok + 10;
            }
         }
         if(World.w.enemyAct > 1 && aiTCh % 10 == 1)
         {
            if(!this.noTurn)
            {
               vAngle = currentWeapon.rot;
            }
            if(Boolean(this.osnova) && this.osnova.phis == 0)
            {
               die();
            }
            if(!stun && this.findCel())
            {
               if(aiState <= 1)
               {
                  aiState = 2;
                  if(Boolean(celUnit) && celUnit is Mine)
                  {
                     aiTCh = 5;
                  }
                  else
                  {
                     aiTCh = Math.floor(Math.random() * 10) + 30;
                  }
               }
               else if(aiState >= 3)
               {
                  aiState = 3;
               }
            }
            else
            {
               setCel(null,celX + Math.random() * 80 - 40,celY + Math.random() * 80 - 40);
               if(aiSpok > 0)
               {
                  --aiSpok;
               }
            }
            if(inter)
            {
               if(aiState <= 1)
               {
                  inter.moveSt = 3;
               }
               else
               {
                  inter.moveSt = 0;
               }
            }
            if(aiState == 0)
            {
               if(!this.noTurn)
               {
                  storona = currentWeapon.rot > -Math.PI / 2 && currentWeapon.rot <= Math.PI / 2 ? 1 : -1;
               }
               currentWeapon.findCel = false;
               overLook = true;
               currentWeapon.drot = 0.5;
               vision = 0.35;
               if(this.hidden == 2)
               {
                  vision = 0;
               }
               isVis = isSats = false;
               dexter = 10;
            }
            else if(aiState == 1)
            {
               if(!this.noTurn)
               {
                  storona = currentWeapon.rot > -Math.PI / 2 && currentWeapon.rot <= Math.PI / 2 ? 1 : -1;
               }
               currentWeapon.findCel = false;
               currentWeapon.drot = this.watchDrot;
               overLook = false;
               vision = 1;
               isVis = isSats = true;
               dexter = 1;
            }
            else if(aiState > 1)
            {
               if(!this.noTurn)
               {
                  storona = celDX > 0 ? 1 : -1;
               }
               currentWeapon.findCel = true;
               if(aiState == 4)
               {
                  currentWeapon.drot = this.watchDrot;
               }
               else
               {
                  currentWeapon.drot = this.actDrot;
               }
               overLook = true;
               vision = 1;
               isVis = isSats = true;
               dexter = 1;
            }
         }
         if(World.w.enemyAct >= 3 && aiState == 3 && !stun)
         {
            currentWeapon.attack();
         }
         if(Boolean(World.w.enemyAct >= 3 && celUnit) && Boolean(dam > 0) && oduplenie <= 0)
         {
            attKorp(celUnit,1);
         }
      }
   }
}

