"""Pure, fail-closed transform for one frozen atlas size experiment."""

from hashlib import sha256

SOURCE_SHA256 = "C0E40368FD8BF6FE1413EC4C8D533C7034B18297AEB35119FBFEC4ADD5D93175"
VERSION = "camera-atlas-pow2-transform-1"


def transform(source: str) -> str:
    """Change physical allocation size only; perform no filesystem operations."""
    if not isinstance(source, str):
        raise TypeError("source must be the frozen UTF-8 source decoded as str")
    actual = sha256(source.encode("utf-8")).hexdigest().upper()
    if actual != SOURCE_SHA256:
        raise ValueError(f"Unexpected SceneRasterPresentation source: {actual}")
    before = "                var old:Rectangle=bounds;\n                for(i=0;i<4;++i){"
    after = (
        "                var old:Rectangle=bounds;\n"
        "                var atlasPixelWidth:int=1;\n"
        "                var atlasPixelHeight:int=1;\n"
        "                while(atlasPixelWidth<next.width)atlasPixelWidth*=2;\n"
        "                while(atlasPixelHeight<next.height)atlasPixelHeight*=2;\n"
        "                for(i=0;i<4;++i){"
    )
    allocation = "new BitmapData(next.width,next.height,true,0)"
    replacement = "new BitmapData(atlasPixelWidth,atlasPixelHeight,true,0)"
    if source.count(before) != 1 or source.count(allocation) != 1:
        raise ValueError("Frozen allocation anchors are not unique")
    result = source.replace(before, after).replace(allocation, replacement)
    if result.replace(after, before).replace(replacement, allocation) != source:
        raise AssertionError("Transform changed unrelated source")
    return result
