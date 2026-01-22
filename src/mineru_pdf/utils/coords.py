from math import ceil
from typing import Union

type Axis = Union[float, int]
type BBoxAxes = tuple[Axis, Axis, Axis, Axis]
type PageSize = tuple[int, int]


def scale(pt: int, pk: int) -> float:
    return round(pt * pk / 1000, 5)

def bbox_scale(bbox: BBoxAxes, page: PageSize):

    if len(bbox) != 4:
        raise ValueError('bbox format invalid, only support 4 value list')

    x0, y0, x1, y1 = bbox

    scale_x = lambda x: int(scale(x, page[0]))
    scale_y = lambda y: int(ceil(scale(y, page[1])))

    return [ scale_x(x0), scale_y(y0), scale_x(x1), scale_y(y1) ]
