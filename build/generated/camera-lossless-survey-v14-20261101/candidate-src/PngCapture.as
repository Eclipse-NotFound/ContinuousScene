package {
 import flash.display.BitmapData;
 import flash.utils.ByteArray;
 /** 兼容旧 AIR 的测试截图编码；不依赖不同 SDK 的 BitmapData.encode 实现。 */
 public class PngCapture {
  public static function encode(b:BitmapData):ByteArray {
   var png:ByteArray=new ByteArray();png.writeUnsignedInt(0x89504e47);png.writeUnsignedInt(0x0d0a1a0a);
   var h:ByteArray=new ByteArray();h.writeUnsignedInt(b.width);h.writeUnsignedInt(b.height);h.writeByte(8);h.writeByte(2);h.writeByte(0);h.writeByte(0);h.writeByte(0);chunk(png,"IHDR",h);
   var raw:ByteArray=new ByteArray();
   for(var y:int=0;y<b.height;y++){raw.writeByte(0);for(var x:int=0;x<b.width;x++){var c:uint=b.getPixel(x,y);raw.writeByte(c>>16);raw.writeByte(c>>8);raw.writeByte(c);}}
   raw.compress();chunk(png,"IDAT",raw);chunk(png,"IEND",new ByteArray());png.position=0;return png;
  }
  private static function chunk(out:ByteArray,kind:String,data:ByteArray):void {
   out.writeUnsignedInt(data.length);var block:ByteArray=new ByteArray();block.writeUTFBytes(kind);block.writeBytes(data);
   var crc:uint=0xffffffff;for(var i:int=0;i<block.length;i++){crc^=block[i];for(var j:int=0;j<8;j++)crc=(crc&1)?0xedb88320^(crc>>>1):crc>>>1;}
   out.writeBytes(block);out.writeUnsignedInt(crc^0xffffffff);
  }
 }
}
