import copy
import os
import hashlib
import json
import logging
import zipfile
from base64 import b64encode
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Dict, List, Optional, Union

import arrow
import filetype
from dateutil import tz
from flask import current_app
from filesizelib import FileSize, StorageUnit
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox, draw_line_sort_bbox
from mineru.utils.enum_class import MakeMode
from pypdfium2 import PdfDocument, PdfPage, PdfiumError, raw as pdfium2_raw
from pypdfium2.internal.consts import ErrorToStr

from ..models import Task
from ..tasks.exceptions import (
    FileEncryptionFoundError, FileMIMEUnsupportedError,
    FileTooLargeSizeError, FileTooManyPagesError,
    FilePageRatioInvalidError,
)

type Axis = Union[float, int]
type BBoxAxes = tuple[Axis, Axis, Axis, Axis]
type PageSize = tuple[int, int]

logger = logging.getLogger(__name__)


def as_semantic(task: Task) -> str:

    if not isinstance(task.started_at, datetime):
        raise RuntimeError('started_at does not exists or empty')

    moment: str = arrow.get(
        task.started_at, tz.gettz(current_app.config.get('TIMEZONE')) # type: ignore
    ) # type: ignore

    return '_'.join([
        f'taskid.{task.uuid}',
        f'moment.{moment.format("YYYYMMDDHHmm")}'
    ])

def calc_sha256sum(file_path: Path, prefix_algo: bool = True) -> str:

    hash_func = hashlib.new('sha256')

    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)

    algo_prefix: str = 'sha256:' if prefix_algo else ''

    return algo_prefix + hash_func.hexdigest()

def create_savedir(moment: arrow.Arrow) -> Path:

    save_dir: Path = Path(
        current_app.instance_path
    ).joinpath(
        'archives', moment.format('YYYY-MM-DD')
    ).resolve()

    if not save_dir.exists():
        save_dir.mkdir(parents=True, exist_ok=True)

    return save_dir

def create_workdir(folder_name: str) -> Path:

    workdir: Path = Path(
        current_app.instance_path
    ).joinpath(
        'cache', folder_name
    ).resolve()

    if not workdir.exists():
        workdir.mkdir(parents=True, exist_ok=True)

    return workdir

def create_zipfile(zip_file: Path, target_dir: Path) -> Path:

    if not zip_file.parent.is_dir() or zip_file.exists():
        raise ValueError(f"The provided zip_file {zip_file} is not a valid file path or exists")

    if not target_dir.is_dir():
        raise ValueError(f"The provided path {target_dir} is not a valid directory.")

    with zipfile.ZipFile(zip_file, 'x', zipfile.ZIP_DEFLATED) as tar:
        for file in target_dir.rglob('*'):
            tar.write(file, file.relative_to(target_dir))

    return zip_file

def file_check(input_file: Path, **kwargs) -> None:

    if not input_file.is_file():
        raise ValueError('not a regular file')

    # only support pdf file
    mime = filetype.guess_extension(input_file)
    if 'pdf' != mime:
        raise FileMIMEUnsupportedError(f'mine type {mime} is unsupported')

    # file should not be too large
    actual_size = FileSize(input_file.stat().st_size, StorageUnit.BYTES)
    limits_size = FileSize(current_app.config.get('PDF_MAX_SIZE') or '0')
    if actual_size > limits_size:
        raise FileTooLargeSizeError(
            f'expected filesize is equal or less then '
            f'{int(limits_size.convert_to_bytes())} bytes, '
            f'{int(actual_size.convert_to_bytes())} bytes given'
        )

    # file should not have any encrypted
    try:
        document: PdfDocument = PdfDocument(input_file)
    except PdfiumError as e:
        if ErrorToStr.get(pdfium2_raw.FPDF_ERR_PASSWORD) in str(e):
            raise FileEncryptionFoundError('unsupported encrypted file')
        else:
            raise e

    # file should not be too many pages
    maximum_pages = int(
        kwargs.get('max_page') or current_app.config.get('PDF_MAX_PAGE') or '0'
    )
    actual_pages = len(document)
    if actual_pages > maximum_pages:
        raise FileTooManyPagesError(
            f'expected pages is equal or less then {maximum_pages}, '
            f'{actual_pages} given'
        )

    # page should be common, avoid too height or width
    maximum_ratio = kwargs.get('max_ratio') or 3.141592
    try:
        page: PdfPage = document.get_page(0)
        width, height = page.get_size()

        if width < height:
            longer = height
            shorter = width
        else:
            longer = width
            shorter = height

        first_ratio = round(longer / shorter, 5)

        if first_ratio > maximum_ratio:
            raise FilePageRatioInvalidError(
                f'unsupported page ratio {first_ratio}, it greater then threshold',
            )

    finally:
        document.close()

def load_json_file(file: Path):
    return json.loads(read_text_file(file) or '{}')

def read_text_file(file: Path) -> Optional[str]:
    with file.open('r') as f:
        return f.read()

def _b64_imagefile(image: Path) -> Optional[str]:
    with image.open('rb') as f:
        return f'data:image/jpeg;base64,{b64encode(f.read()).decode()}'

def pickup_images(image_dir: Path) -> dict:
    return {
        image.name : _b64_imagefile(image) for image in image_dir.glob('*.jpg')
    }

def fix_content_list(content_list: List[Dict], page_sizes: Dict[int, PageSize]):

    def scale(pt: int, pk: int) -> float:
        return round(pt * pk / 1000, 5)

    def bbox_scale(bbox: BBoxAxes, page: PageSize):

        if len(bbox) != 4:
            raise ValueError('bbox format invalid, only support 4 value list')

        x0, y0, x1, y1 = bbox

        scale_x = lambda x: int(scale(x, page[0]))
        scale_y = lambda y: int(ceil(scale(y, page[1])))

        return [ scale_x(x0), scale_y(y0), scale_x(x1), scale_y(y1) ]

    items = copy.deepcopy(content_list)

    for item in items:
        if 'bbox' in item:
            item['bbox'] = bbox_scale(tuple(item['bbox']), page_sizes[item['page_idx']])

    return items

def fix_model_json(model_json: Optional[List[Union[Dict, List[Dict]]]], page_sizes: Dict[int, PageSize]):

    if model_json is None:
        return model_json

    items = copy.deepcopy(model_json)

    for idx, item in enumerate(items):

        # for pipeline output
        if isinstance(item, dict):

            ori = page_sizes[item['page_info']['page_no']]
            wid = item['page_info']['width']
            hei = item['page_info']['height']

            factors = (round(wid / ori[0], 5), round(hei / ori[1], 5))

            def oct_scale(poly: List[float], factors: tuple[float, float]) -> List[float]:
                return [
                    round(poly[0] / factors[0], 5), round(poly[1] / factors[1], 5),
                    round(poly[2] / factors[0], 5), round(poly[3] / factors[1], 5),
                    round(poly[4] / factors[0], 5), round(poly[5] / factors[1], 5),
                    round(poly[6] / factors[0], 5), round(poly[7] / factors[1], 5),
                ]

            for det in item['layout_dets']:
                det['poly'] = oct_scale(det['poly'], factors)

        # for vlm output
        elif isinstance(item, list):

            page_size = page_sizes[idx]

            def quad_scale(bbox: List[float], page_size) -> List[float]:
                return [
                    round(bbox[0] * page_size[0], 5), round(bbox[1] * page_size[1], 5),
                    round(bbox[2] * page_size[0], 5), round(bbox[3] * page_size[1], 5),
                ]

            for pice in item:
                pice['bbox'] = quad_scale(pice['bbox'], page_size)

        else:
            raise ValueError(f'expected dict or list, {type(item)} given')

    return items

def output_dirs_handler(output_dir, pdf_file_name, parse_method):
    txt_dir = Path(output_dir)
    txt_dir.mkdir(parents=True, exist_ok=True)
    img_dir = Path(output_dir).joinpath('images')
    img_dir.mkdir(parents=True, exist_ok=True)
    return str(img_dir), str(txt_dir)

def output_data_handler(
        pdf_info: dict,
        pdf_bytes: bytes,
        pdf_file_name: str,
        local_md_dir: Path,
        local_image_dir: Path,
        md_writer,
        f_draw_layout_bbox: bool,
        f_draw_span_bbox: bool,
        f_dump_orig_pdf: bool,
        f_dump_md: bool,
        f_dump_content_list: bool,
        f_dump_middle_json: bool,
        f_dump_model_output: bool,
        f_make_md_mode: MakeMode,
        middle_json: dict,
        model_output: Optional[List[Union[Dict, List[Dict]]]],
        is_pipeline: bool,
        apply_scaled_output: bool,
) -> None:

    image_dir = str(os.path.basename(local_image_dir))

    # for content
    make_func = pipeline_union_make if is_pipeline else vlm_union_make
    md_content_str = make_func(pdf_info, f_make_md_mode, image_dir) # type: ignore
    md_writer.write_string(f"content.md", md_content_str)

    # for content list
    make_func = pipeline_union_make if is_pipeline else vlm_union_make
    page_sizes = { page['page_idx']: tuple(page['page_size']) for page in middle_json['pdf_info'] }
    if is_pipeline:
        content_list: List[Dict] = make_func(pdf_info, MakeMode.CONTENT_LIST, image_dir) # type: ignore
        md_writer.write_string(
            f"content_list.json", json.dumps(content_list, ensure_ascii=False, indent=2)
        )
        if apply_scaled_output:
            md_writer.write_string(
                f"content_list.scaled.json", json.dumps(
                    fix_content_list(content_list, page_sizes),
                    ensure_ascii=False, indent=2)
            )
    else:
        content_list_v2: List[Dict] = make_func(pdf_info, MakeMode.CONTENT_LIST_V2, image_dir) # type: ignore
        md_writer.write_string(
            f"content_list_v2.json", json.dumps(content_list_v2, ensure_ascii=False, indent=2)
        )
        if apply_scaled_output:
            md_writer.write_string(
                f"content_list_v2.scaled.json", json.dumps(
                    fix_content_list(content_list_v2, page_sizes),
                    ensure_ascii=False, indent=2)
            )

    # for middle
    md_writer.write_string(
        f"middle.json", json.dumps(middle_json, ensure_ascii=False, indent=2)
    )

    # for model
    md_writer.write_string(
        f"model.json", json.dumps(model_output, ensure_ascii=False, indent=2)
    )
    if apply_scaled_output:
        md_writer.write_string(
            f"model.scaled.json", json.dumps(
                fix_model_json(model_output, page_sizes),
                ensure_ascii=False, indent=2)
        )

    # for debug
    if f_draw_layout_bbox or f_draw_span_bbox:
        draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir, f"layout.pdf")
        draw_span_bbox(pdf_info, pdf_bytes, local_md_dir, f"spans.pdf")
        draw_line_sort_bbox(pdf_info, pdf_bytes, local_md_dir, f"line_sort.pdf")

    if f_dump_orig_pdf:
        md_writer.write(f"origin.pdf", pdf_bytes)
