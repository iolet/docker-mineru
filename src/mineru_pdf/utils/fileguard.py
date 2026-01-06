import os
import hashlib
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Union

import arrow
import filetype
from dateutil import tz
from flask import current_app
from mineru.data.data_reader_writer.filebase import FileBasedDataWriter
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

class ImgWriter(FileBasedDataWriter):
    """Write image data to file"""

    def __init__(self, parent_dir: Union[Path, str] = '') -> None:
        """Initialized with parent_dir.

        Args:
            parent_dir (str, optional): the parent directory that may be used within methods. Defaults to ''.
        """
        super().__init__(str(parent_dir))

class TxtWriter(FileBasedDataWriter):
    """Write txt data to file and replace path inside"""

    def __init__(self, parent_dir: Union[Path, str] = '') -> None:
        """Initialized with parent_dir.

        Args:
            parent_dir (str, optional): the parent directory that may be used within methods. Defaults to ''.
        """
        super().__init__(str(parent_dir))

    def write_string(self, path: str, data: str) -> None:
        """Write the data to file, the data will be encoded to bytes.

        Args:
            path (Path | str): the target file where to write
            data (str): the data want to write
        """

        savedir: Path = Path(self._parent_dir)

        if savedir.is_absolute():
            data = data.replace(str(savedir) + os.sep, '')

        super().write_string(path, data)
