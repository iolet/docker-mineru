import logging
import zipfile
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

def create_zipfile(zip_file: Path, target_dir: Path) -> Path:

    if not zip_file.parent.is_dir() or zip_file.exists():
        raise ValueError(f"The provided zip_file {zip_file} is not a valid file path or exists")

    if not target_dir.is_dir():
        raise ValueError(f"The provided path {target_dir} is not a valid directory.")

    with zipfile.ZipFile(zip_file, 'x', zipfile.ZIP_DEFLATED) as tar:
        for file in target_dir.rglob('*'):
            tar.write(file, file.relative_to(target_dir))

    return zip_file

def post_callback(task: Task) -> None:

    if task.callback_url is None:
        return

    if task.callback_url.isspace():
        return

    host: str = current_app.config['APP_URL']
    data: dict = TaskSchema().dump(task)

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
