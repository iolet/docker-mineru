import json
import re
import shutil
from pathlib import Path
from typing import Optional

import arrow
from celery import shared_task
from celery.app.task import Task as Concrete
from celery.utils.log import get_task_logger
from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from .exceptions import ExtraErrorCodes
from .extensions import database
from .models import Task
from .utils.fileguard import (
    as_semantic, calc_sha256sum, file_check,
    create_savedir, create_workdir, create_zipfile
)
from .utils.httpclient import download_file, post_callback

logger = get_task_logger(__name__)


class Result(object):
    NONE_: str = 'NONE'
    COLLECTING: str = 'COLLECTING'
    CHECKING: str = 'CHECKING'
    INFERRING: str = 'INFERRING'
    PACKING: str = 'PACKING'
    CLEANING: str = 'CLEANING'
    FINISHED: str = 'FINISHED'

class Status(object):
    CREATED: str = 'CREATED'
    RUNNING: str = 'RUNNING'
    COMPLETED: str = 'COMPLETED'
    TERMINATED: str = 'TERMINATED'

@shared_task(bind=True, max_retries=2, retry_backoff=True)
def mining_pdf(self: Concrete, task_id: int) -> int:

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
    task.errors = ExtraErrorCodes.NONE_.value
    task.started_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    database.session.commit()

    # prepare workdir
    folder: str = as_semantic(task)
    workdir: Path = create_workdir(folder)
    logger.info(f'workdir -> {workdir} folder -> {folder}')

    # download file
    task.result = Result.COLLECTING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    database.session.commit()

    try:
        pdf_file: Path = download_file(
            task.file_url, workdir.joinpath(task.file_id).with_suffix('.pdf')
        )
    except Exception as e:
        logger.exception(e)
        task.status = Status.TERMINATED
        task.errors = getattr(e, 'code', ExtraErrorCodes.INTERNAL_ERROR.value)
        task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
        database.session.commit()
        return 0

    # check file
    task.result = Result.CHECKING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    database.session.commit()

    try:
        file_check(pdf_file)
    except Exception as e:
        logger.exception(e)
        task.status = Status.TERMINATED
        task.errors = getattr(e, 'code', ExtraErrorCodes.INTERNAL_ERROR.value)
        task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
        database.session.commit()
        return 0

    # infect content
    task.result = Result.INFERRING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    database.session.commit()

    if not 'magic_file' in globals():
        from .utils.magicfile import magic_args, magic_file

    try:
        finetune_args = json.loads(task.finetune_args)
    except (json.decoder.JSONDecodeError, TypeError) as e:
        logger.warning(e, exc_info=True)
        finetune_args = {}

    try:
        magic_kwargs = magic_args({ **finetune_args, # type: ignore
            'vllm_endpoint': current_app.config.get('VLLM_ENDPOINT')
        })
    except ValueError as e:
        logger.warning(e, exc_info=True)
        magic_kwargs = {}

    try:
        magic_file(pdf_file, workdir, **magic_kwargs) # type: ignore
    except Exception as e:
        logger.exception(e)
        task.status = Status.TERMINATED
        task.errors = getattr(e, 'code', ExtraErrorCodes.INTERNAL_ERROR.value)
        task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
        database.session.commit()
        return 255

    # packing result
    task.result = Result.PACKING
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
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
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    database.session.commit()

    if tarball.exists():
        shutil.rmtree(workdir)

    # mark as completed
    task.status = Status.COMPLETED
    task.result = Result.FINISHED
    task.updated_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    task.finished_at = arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    database.session.commit()

    # post callback
    try:
        post_callback(task)
    except Exception as e:
        logger.warning(e, exc_info=True)

    return 0

def start_of_day(moment: arrow.Arrow) -> arrow.Arrow:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)

@shared_task
def prune_archives():

    timezone: str = current_app.config.get('TIMEZONE') # type: ignore
    archives_dir: Path = Path(current_app.instance_path).joinpath('archives')
    keep_days: int = abs(current_app.config.get('ARCHIVE_KEEP_DAYS')) # type: ignore

    if 0 == keep_days:
        logger.debug('ARCHIVE_KEEP_DAYS is 0, skipped')
        return

    oldest_day: arrow.Arrow = start_of_day(arrow.now(tz=timezone).shift(days=-keep_days))

    for chunks in archives_dir.iterdir():
        try:
            target_day = start_of_day(arrow.get(chunks.name, 'YYYY-MM-DD', tzinfo=timezone))
        except arrow.ParserError:
            continue
        if target_day < oldest_day:
            shutil.rmtree(chunks)
            logger.info(f'pruned archives {chunks}')

@shared_task
def remove_workdir():

    timezone: str = current_app.config.get('TIMEZONE') # type: ignore
    cache_dir: Path = Path(current_app.instance_path).joinpath('cache')
    keep_days: int = abs(current_app.config.get('WORKDIR_KEEP_DAYS')) # type: ignore

    if 0 == keep_days:
        logger.debug('WORKDIR_KEEP_DAYS is 0, skipped')
        return

    oldest_day: arrow.Arrow = start_of_day(arrow.now(tz=timezone).shift(days=-keep_days))

    for target in cache_dir.iterdir():

        target_day = None

        if target.name.startswith('uploaded.'):
            matches = re.search(r'(?<=uploaded\.)(?P<day>\d{4}-\d{2}-\d{2})', target.name, re.ASCII)
            if matches is not None:
                target_day = start_of_day(arrow.get(matches.group('day'), 'YYYY-MM-DD', tzinfo=timezone))

        if target.name.startswith('taskid.'):
            matches = re.search(r'(?<=moment\.)(?P<moment>\d{12})', target.name, re.ASCII)
            if matches is not None:
                target_day = start_of_day(arrow.get(matches.group('moment'), 'YYYYMMDDHHmm', tzinfo=timezone))

        if target_day is not None:
            if target_day < oldest_day:
                shutil.rmtree(target)
                logger.info(f'removed workdir {target}')
