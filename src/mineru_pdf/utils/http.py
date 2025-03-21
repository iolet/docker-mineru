import hashlib
from pathlib import Path

from requests import get as http_get


def download_file(uri: str, sink: Path) -> Path:
    """Raises :class:`HTTPError`, if one occurred."""

    with http_get(uri, stream=True) as r:
        r.raise_for_status()
        with open(sink, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    return sink

def calc_sha256sum(file_path: Path) -> str:

    hash_func = hashlib.new('sha256')

    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)

    return hash_func.hexdigest()
