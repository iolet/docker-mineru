from math import ceil
from typing import Union

type Axis = Union[float, int]
type BBoxAxes = tuple[Axis, Axis, Axis, Axis]
type PageSize = tuple[int, int]

def pt2px(pt: Axis) -> float:
    return round(float(pt) * 4 / 3, 5)

def scale(px: int, peak: int) -> float:
    return round(px * peak / 1000, 5)

def bbox_pt2px(bbox: BBoxAxes):

    if len(bbox) != 4:
        raise ValueError('bbox format invalid, only support 4 value list')

    x0, y0, x1, y1 = bbox

    to_px = lambda pt, up: int(ceil(pt2px(pt)) if up else pt2px(pt))

    return [
        to_px(x0, False), to_px(y0, False),
        to_px(x1, True), to_px(y1, True)
    ]

def bbox_scale(bbox: BBoxAxes, page: PageSize):

    if len(bbox) != 4:
        raise ValueError('bbox format invalid, only support 4 value list')

    x0, y0, x1, y1 = bbox

    scale_x = lambda x: int(scale(x, page[0]))
    scale_y = lambda y: int(ceil(scale(y, page[1])))

    return [ scale_x(x0), scale_y(y0), scale_x(x1), scale_y(y1) ]
