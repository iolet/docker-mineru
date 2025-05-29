from pathlib import Path

import fitz

from ..tasks.exceptions import FileEncryptionFoundError


def file_check(input_file: Path) -> None:

    document: fitz.Document = fitz.open(input_file)

    if document.is_encrypted:
        document.close()
        del document
        raise FileEncryptionFoundError('unsupported encrypted file')

    document.close()
    del document
