import os
import hashlib
import json
import logging
import zipfile
from base64 import b64encode
from datetime import datetime
from pathlib import Path
from typing import Optional

import arrow
import filetype
from dateutil import tz
from flask import current_app
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox, draw_line_sort_bbox
from mineru.utils.enum_class import MakeMode
from pypdfium2 import PdfDocument, PdfPage, PdfiumError, raw as pdfium2_raw
from pypdfium2.internal.consts import ErrorToStr

from ..models import Task
from ..tasks.exceptions import (
    FileEncryptionFoundError, FileMIMEUnsupportedError,
    FilePageRatioInvalidError,
)

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

def file_check(input_file: Path) -> None:

    if not input_file.is_file():
        raise ValueError('not a regular file')

    mime = filetype.guess_extension(input_file)

    if 'pdf' != mime:
        raise FileMIMEUnsupportedError(f'mine type {mime} is unsupported')

    # file should not have any encrypted
    try:
        document: PdfDocument = PdfDocument(input_file)
    except PdfiumError as e:
        if ErrorToStr.get(pdfium2_raw.FPDF_ERR_PASSWORD) in str(e):
            raise FileEncryptionFoundError('unsupported encrypted file')
        else:
            raise e

    # page should be common, avoid too height or width
    try:
        page: PdfPage = document.get_page(0)
        width, height = page.get_size()

        if width < height:
            longer = height
            shorter = width
        else:
            longer = width
            shorter = height

        ratio = longer / shorter

        if ratio > 3.1415926:
            raise FilePageRatioInvalidError(
                f'unsupported page ratio {ratio}, it greater then threshold',
            )

    finally:
        document.close()

def receive_json(file: Path):
    return json.loads(receive_text(file) or '{}')

def receive_text(file: Path) -> Optional[str]:
    with file.open('r') as f:
        return f.read()

def locate_image(image: Path) -> str:
    return image.name

def encode_image(image: Path) -> Optional[str]:
    with image.open('rb') as f:
        return f'data:image/jpeg;base64,{b64encode(f.read()).decode()}'

def pickup_images(image_dir: Path) -> dict:
    return {
        locate_image(image) : encode_image(image) for image in image_dir.glob('*.jpg')
    }

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
        model_output: dict,
        is_pipeline: bool
) -> None:

    image_dir = str(os.path.basename(local_image_dir))

    # for content
    make_func = pipeline_union_make if is_pipeline else vlm_union_make
    md_content_str = make_func(pdf_info, f_make_md_mode, image_dir) # type: ignore
    md_writer.write_string(f"content.md", md_content_str)

    # for content list
    make_func = pipeline_union_make if is_pipeline else vlm_union_make
    if is_pipeline:
        content_list = make_func(pdf_info, MakeMode.CONTENT_LIST, image_dir) # type: ignore
        md_writer.write_string(
            f"content_list.json",
            json.dumps(content_list, ensure_ascii=False, indent=2),
        )
    else:
        content_list_v2 = make_func(pdf_info, MakeMode.CONTENT_LIST_V2, image_dir) # type: ignore
        md_writer.write_string(
            f"content_list_v2.json",
            json.dumps(content_list_v2, ensure_ascii=False, indent=2),
        )

    # for middle
    md_writer.write_string(
        f"middle.json", json.dumps(middle_json, ensure_ascii=False, indent=2)
    )

    # for model
    md_writer.write_string(
        f"model.json", json.dumps(model_output, ensure_ascii=False, indent=2)
    )

    # for debug
    if f_draw_layout_bbox or f_draw_span_bbox:
        draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir, f"layout.pdf")
        draw_span_bbox(pdf_info, pdf_bytes, local_md_dir, f"spans.pdf")
        draw_line_sort_bbox(pdf_info, pdf_bytes, local_md_dir, f"line_sort.pdf")

    if f_dump_orig_pdf:
        md_writer.write(f"origin.pdf", pdf_bytes)
