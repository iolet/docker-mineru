import hashlib
import hmac
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import arrow
import requests
from dateutil import tz
from flask import current_app

from ..models import Task
from ..utils.presenters import TaskSchema

logger = logging.getLogger(__name__)


def confirm_archivedir(moment: Optional[arrow.Arrow] = None) -> Path:

    archivedir: Path = Path(
        current_app.instance_path
    ).joinpath(
        'archives', moment.format('YYYY-MM-DD')
    ).resolve()

    if not archivedir.exists():
        archivedir.mkdir(parents=True, exist_ok=True)

    return archivedir

def create_workdir(folder_name: str) -> Path:

    workdir: Path = Path(
        current_app.instance_path
    ).joinpath(
        'cache', folder_name
    ).resolve()

    if not workdir.exists():
        workdir.mkdir(parents=True, exist_ok=True)

    return workdir

def post_callback(task: Task) -> None:

    if task.callback_url is None:
        return

    if task.callback_url.isspace():
        return

    payload: dict = {
        'content': TaskSchema().dump(task),
        'signature': hmac.digest(
            key=task.tarball_checksum,
            msg=task.uuid,
            digest=hashlib.sha256
        )
    }

    for i in range(5):
        with requests.post(task.callback_url, json=payload) as r:
            try:
                r.raise_for_status()
                break;
            except requests.HTTPError as e:
                pass

def semantic_repl(task: Task) -> str:

    if not isinstance(task.started_at, datetime):
        raise RuntimeError('started_at does not exists or empty')

    moment: str = arrow.get(
        task.started_at, tz.gettz(current_app.config.get('TIMEZONE'))
    )

    return '_'.join([
        f'taskid.{task.uuid}',
        f'moment.{moment.format("YYYYMMDDHHmm")}'
    ])
