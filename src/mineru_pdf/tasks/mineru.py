import json
import shutil
from pathlib import Path
from typing import Optional

import arrow
from celery import shared_task
from celery.app.task import Task as Concrete
from celery.utils.log import get_task_logger
from flask import current_app
from requests.exceptions import HTTPError
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from .constants import Errors, Result, Status, find_http_errors
from ..models import Task
from ..services import database
from ..utils.fileguard import file_check
from ..utils.filepath import as_semantic, create_savedir, create_workdir, create_zipfile
from ..utils.http import calc_sha256sum, download_file, post_callback

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=2, retry_backoff=True)
def extract_pdf(self: Concrete, task_id: int) -> int:

    # mark as start
    try:
        task: Optional[Task] = database.session.scalars(
            select(Task).
            where(Task.id == task_id).
            order_by(Task.id.desc())
        ).one()
    except NoResultFound as e:
        logger.exception(e)
        return 0

    task.status = Status.RUNNING
    task.result = Result.NONE_
    task.errors = Errors.NONE_
    task.started_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    database.session.commit()

    # prepare workdir
    folder: str = as_semantic(task)
    workdir: Path = create_workdir(folder)
    logger.info(f'workdir -> {workdir} folder -> {folder}')

    # download file
    task.result = Result.COLLECTING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    database.session.commit()

    try:
        pdf_file: Path = download_file(
            task.file_url, workdir.joinpath(task.file_id).with_suffix('.pdf')
        )
    except HTTPError as e:
        logger.exception(e)
        task.status = Status.TERMINATED
        task.errors = find_http_errors(e.response.status_code)
        task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
        database.session.commit()
        return 0

    # check file
    task.result = Result.CHECKING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    database.session.commit()

    try:
        file_check(pdf_file)
    except Exception as e:
        logger.exception(e)
        task.status = Status.TERMINATED
        task.errors = getattr(e, 'code', Errors.SYS_INTERNAL_ERROR)
        task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
        database.session.commit()
        return 0

    # infect content
    task.result = Result.INFERRING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    database.session.commit()

    if not 'tune_spell' in globals():
        from ..utils.magicfile import tune_spell

    try:
        fine_args = tune_spell(
            json.loads(task.finetune_args)
        )
    except json.decoder.JSONDecodeError as e1:
        logger.warning(e1, exc_info=True)
        fine_args = {}
    except TypeError as e2:
        logger.warning(e2, exc_info=True)
        fine_args = {}

    if not 'magic_file' in globals():
        from ..utils.magicfile import magic_file

    try:
        magic_file(pdf_file, workdir, **fine_args)
    except Exception as e:
        logger.exception(e)
        task.status = Status.TERMINATED
        task.errors = getattr(e, 'code', Errors.SYS_INTERNAL_ERROR)
        task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
        database.session.commit()
        return 255

    # packing result
    task.result = Result.PACKING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    database.session.commit()

    moment = arrow.now(current_app.config.get('TIMEZONE'))
    tarball: Path = create_zipfile(
        create_savedir(moment).joinpath(folder + '.zip'), workdir
    )

    task.tarball_location = str(tarball.relative_to(current_app.instance_path))
    task.tarball_checksum = calc_sha256sum(tarball)
    database.session.commit()

    # clean workarea
    task.result = Result.CLEANING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    database.session.commit()

    if tarball.exists():
        shutil.rmtree(workdir)

    # mark as completed
    task.status = Status.COMPLETED
    task.result = Result.FINISHED
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    task.finished_at = arrow.now(current_app.config.get('TIMEZONE')).datetime
    database.session.commit()

    # post callback
    try:
        post_callback(task)
    except Exception as e:
        logger.warning(e, exc_info=True)

    return 0
