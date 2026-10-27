// Replacement for the original byCell key expression; all original guards and
// the environment-copy tail remain byte-identical apart from branch relocation.
var cellX:int=int(Math.max(0,x)/1920);
var cellY:int=int(Math.max(0,y)/1000);
var minX:*=value.land.minLocX;
var minY:*=value.land.minLocY;
var key:String;
if(cellX<0 || cellX>255 || cellY<0 || cellY>255) {
    key=(minX+cellX)+":"+(minY+cellY);
} else {
    var cache:Array=state._csEnvironmentCellKeysV1 as Array;
    if(cache==null || cache[0]!==minX || cache[1]!==minY || !(cache[2] is Array)) {
        cache=[minX,minY,[]];state._csEnvironmentCellKeysV1=cache;
    }
    var columns:Array=cache[2] as Array;
    var column:Array=columns[cellX] as Array;
    if(column==null) {column=[];columns[cellX]=column;}
    key=column[cellY] as String;
    if(key==null) {key=(minX+cellX)+":"+(minY+cellY);column[cellY]=key;}
}
// The original state.byCell read precedes key evaluation; its receiver remains
// on the stack throughout this block, then the original runtime lookup resumes.
