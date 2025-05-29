from pathlib import Path

import fitz

from ..tasks.exceptions import FileEncryptionFoundError, FilePageRatioInvalidError


def file_check(input_file: Path) -> None:

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

        if ratio > 1.78:
            raise FilePageRatioInvalidError(
                'unsupported page size, A and B series, plus US Letter only',
            )

    finally:
        if getattr(document, 'is_closed', False):
            document.close()
        del document
