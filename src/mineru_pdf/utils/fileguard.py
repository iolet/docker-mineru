import subprocess
from pathlib import Path

import filetype
import fitz

from ..tasks.exceptions import (
    FileEncryptionFoundError, FileMIMEUnsupportedError,
    FilePageRatioInvalidError,
)


def img2pdf(input_file: Path) -> Path:

    if not input_file.is_file():
        raise ValueError('not a regular file')

    ext = filetype.guess_extension(input_file)

    if ext not in [ 'png', 'jpg', 'jpeg', ]:
        raise FileMIMEUnsupportedError(
            f'unsupported convert {input_file.name} to'
            f'{input_file.with_suffix(".pdf").name}'
        )

    origin = fitz.open(str(input_file))

    output: Path = input_file.with_suffix('.pdf')
    with output.open('wb') as fp:
        fp.write(origin.convert_to_pdf())

    origin.close()
    del origin

    return output

def doc2pdf(input_file: Path):

    if not input_file.is_file():
        raise ValueError(f'{input_file} not a regular file')

    ext = filetype.guess_extension(input_file)

    if ext not in [ 'ppt', 'pptx', 'doc', 'docx' ]:
        raise FileMIMEUnsupportedError(
            f'unsupported {input_file.name} to'
            f'{input_file.with_suffix(".pdf").name}'
        )

    output = input_file.resolve().with_suffix('.pdf')
    process = subprocess.run([
        'soffice', '--headless',
        '--convert-to', 'pdf',
        '--outdir', output.parent,
        input_file.resolve()
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)

    if 0 != process.returncode:
        raise ValueError(
            f'failed convert {input_file.name} to'
            f'{output.name}'
        )

    return output

def file_check(input_file: Path) -> None:

    if not input_file.is_file():
        raise ValueError('not a regular file')

    mime = filetype.guess_extension(input_file)

    if 'pdf' != mime:
        raise FileMIMEUnsupportedError(f'mine type {mime} is unsupported')

    document: fitz.Document = fitz.open(input_file)

    try:

        # file should not have any encrypted
        # see https://pymupdf.readthedocs.io/en/latest/recipes-low-level-interfaces.html#how-to-access-the-pdf-file-trailer
        trailer: str = document.xref_object(-1)
        if '/Encrypt' in trailer:
            raise FileEncryptionFoundError('unsupported encrypted file')

        # page should be common, avoid too height or width
        page = document.load_page(0)

        if page.rect.width < page.rect.height:
            longer = page.rect.height
            shorter = page.rect.width
        else:
            longer = page.rect.width
            shorter = page.rect.height

        ratio = longer / shorter

        if ratio > 3.1415926:
            raise FilePageRatioInvalidError(
                f'unsupported page ratio {ratio}, it greater then threshold',
            )

    finally:
        if getattr(document, 'is_closed', False):
            document.close()
        del document
