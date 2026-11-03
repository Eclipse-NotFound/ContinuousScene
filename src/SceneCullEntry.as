package {
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Sprite;
    internal final class SceneCullEntry {
        public var child:DisplayObject,wrapper:Sprite,layer:DisplayObjectContainer;
        public var index:int=-1;
        public var x:Number,y:Number,sx:Number,sy:Number,rotation:Number;
        public var left:Number,right:Number,top:Number,bottom:Number;
        public var empty:Boolean=false,hidden:Boolean=false,checked:Boolean=false,pending:Boolean=false;
    }
}
