from math import ceil
from typing import List, Union

def pt2px(pt: Union[float, int]) -> float:
    return round(float(pt) * 4 / 3, 5)

def scale(px: int, peak: int) -> float:
    return round(px * peak / 1000, 5)

def bbox_pt2px(bbox: List[Union[float, int]]):

    if len(bbox) != 4:
        raise ValueError('bbox format invalid, only support 4 value list')

    x0, y0, x1, y1 = bbox

    to_px = lambda pt, up: int(ceil(pt2px(pt)) if up else pt2px(pt))

    return [
        to_px(x0, False), to_px(y0, False),
        to_px(x1, True), to_px(y1, True)
    ]

def bbox_scale(bbox: List[int], w: int, h: int):

    if len(bbox) != 4:
        raise ValueError('bbox format invalid, only support 4 value list')

    x0, y0, x1, y1 = bbox

    scale_x = lambda x: int(scale(x, w))
    scale_y = lambda y: int(ceil(scale(y, h)))

    return [ scale_x(x0), scale_y(y0), scale_x(x1), scale_y(y1) ]
