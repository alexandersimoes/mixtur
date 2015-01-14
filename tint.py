import random
from PIL import Image
from PIL import ImageColor
from PIL import ImageOps

def image_tint(src, tint=None):
    r = lambda: random.randint(0,255)
    tint = tint or '#{:02X}{:02X}{:02X}'.format(r(), r(), r())
    if Image.isStringType(src):  # file path?
        src = Image.open(src)
    if src.mode not in ['RGB', 'RGBA']:
        raise TypeError('Unsupported source image mode: {}'.format(src.mode))
    src.load()

    tr, tg, tb = ImageColor.getrgb(tint)
    tl = ImageColor.getcolor(tint, "L")  # tint color's overall luminosity
    if not tl: tl = 1  # avoid division by zero
    tl = float(tl)  # compute luminosity preserving tint factors
    sr, sg, sb = map(lambda tv: tv/tl, (tr, tg, tb))  # per component adjustments

    # create look-up tables to map luminosity to adjusted tint
    # (using floating-point math only to compute table)
    luts = (map(lambda lr: int(lr*sr + 0.5), range(256)) +
            map(lambda lg: int(lg*sg + 0.5), range(256)) +
            map(lambda lb: int(lb*sb + 0.5), range(256)))
    l = ImageOps.grayscale(src)  # 8-bit luminosity version of whole image
    if Image.getmodebands(src.mode) < 4:
        merge_args = (src.mode, (l, l, l))  # for RGB verion of grayscale
    else:  # include copy of src image's alpha layer
        a = Image.new("L", src.size)
        a.putdata(src.getdata(3))
        merge_args = (src.mode, (l, l, l, a))  # for RGBA verion of grayscale
        luts += range(256)  # for 1:1 mapping of copied alpha values

    return Image.merge(*merge_args).point(luts)
