import logging
from pathlib import Path
from urllib.parse import ParseResult, urlparse

import requests
from flask import current_app

from ..models import Task
from ..utils.presenters import TaskSchema

logger = logging.getLogger(__name__)


def download_file(uri: str, sink: Path) -> Path:
    """Raises :class:`HTTPError`, if one occurred."""

    with requests.get(uri, stream=True) as r:
        r.raise_for_status()
        with open(sink, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    return sink

def post_callback(task: Task) -> None:

    if task.callback_url is None:
        return

    if task.callback_url.isspace():
        return

    uri: ParseResult = urlparse(task.callback_url)

    if not uri.scheme or not uri.netloc:
        logger.warning(f'scheme not found in task {task.uuid} callback: {task.callback_url}')
        return

    host: str = current_app.config['APP_URL']
    data: dict = TaskSchema().dump(task) # type: ignore

    if 'tarball' in data:
        if 'location' in data['tarball']:
            data['tarball']['location'] = '/'.join([
                host.rstrip('/'), str(data['tarball']['location']).lstrip('/')
            ])

    payload: dict = {
        'data': data
    }

    for i in range(5):
        with requests.post(task.callback_url, json=payload) as r:
            try:
                r.raise_for_status()
                logger.info(f'posted callback <{task.callback_url}> with {r.status_code} in {i + 1}th times successfully')
                break;
            except requests.HTTPError as e:
                logger.warning(f'callback failed for <{e}> in {i + 1}th times')
