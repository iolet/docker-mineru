import json
import logging
import uuid
from re import sub as preg_replace
from typing import Optional, Union
from urllib.parse import ParseResult, urlparse

import arrow
from flask import Blueprint, current_app, request
from sqlalchemy import select
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from ..models import Task, database
from ..utils.task import Result, Status
from ..utils.presenters import TaskSchema

logger = logging.getLogger(__name__)

extractor2: Blueprint = Blueprint('extractor2', __name__)


@extractor2.post('/task')
def create_task():

    try:
        payload: dict = request.json()
    except BadRequest as e:
        return {
            'error': {
                'code': 'FailedDecodeJson',
                'message': str(e),
                'target': '_request'
            },
        }, 400
    except UnsupportedMediaType as e:
        return {
            'error': {
                'code': 'UnsupportedMediaType',
                'message': str(e),
                'target': '_body'
            },
        }, 415

    file_url: ParseResult = urlparse(payload.get('file_url', None))
    if file_url.scheme not in ['http', 'https']:
        return {
            'error': {
                'code': 'InvalidURL',
                'message': 'invalid file_url, only support http(s) url',
                'target': 'file_url'
            },
        }, 422

    enable_ocr: Union[bool, str] = payload.get('enable_ocr', False)
    if enable_ocr in ['yes', 'true', True]:
        enable_ocr: bool = True
    elif enable_ocr in ['no', 'false', False]:
        enable_ocr: bool = False
    else:
        return {
            'error': {
                'code': 'UnsupportedValue',
                'message': f'unknown value {enable_ocr},'
                           f'only support bool (true, false) or string (true false yes and no)',
                'target': 'enable_ocr'
            }
        }, 422

    enable_table: Union[bool, str] = payload.get('enable_table', True)
    if enable_table in ['yes', 'true', True]:
        enable_table: bool = True
    elif enable_table in ['no', 'false', False]:
        enable_table: bool = False
    else:
        return {
            'error': {
                'code': 'UnsupportedValue',
                'message': f'unknown value {enable_table},'
                           f'only support bool (true, false) or string (true false yes and no)',
                'target': 'enable_table'
            }
        }, 422

    enable_formula: Union[bool, str] = payload.get('enable_formula', False)
    if enable_formula in ['yes', 'true', True]:
        enable_formula: bool = True
    elif enable_formula in ['no', 'false', False]:
        enable_formula: bool = False
    else:
        return {
            'error': {
                'code': 'UnsupportedValue',
                'message': f'unknown value {enable_formula},'
                           f'only support bool (true, false) or string (true false yes and no)',
                'target': 'enable_formula'
            }
        }, 422

    # current support english and chinese only, for more supported language,
    # see https://paddlepaddle.github.io/PaddleOCR/latest/ppocr/blog/multi_languages.html#5
    prefer_language: Optional[str] = payload.get('prefer_language', 'ch')
    if prefer_language not in ['ch', 'en']:
        return {
            'error': {
                'code': 'UnsupportedValue',
                'message': f'unknown value {prefer_language}, only support ch (chinese) or en (english)',
                'target': 'prefer_language'
            }
        }, 422

    file_id: Optional[str] = payload.get('file_id', None)
    if not isinstance(file_id, str) or not file_id.isprintable():
        return {
            'error': {
                'code': 'EmptyOrMissingValue',
                'message': 'empty or missing, please ensure file_id is present and not empty',
                'target': 'file_id'
            }
        }, 422
    elif not preg_replace(r'[a-zA-z0-9-]', '', file_id).isprintable():
        return {
            'error': {
                'code': 'UnsupportedValue',
                'message': 'field value should be ensure contain alphabets, numbers and dashes only',
                'target': 'file_id'
            }
        }, 422
    elif len(file_id) > 128:
        return {
            'error': {
                'code': 'ExceedMaximum',
                'message': 'field length should be less 128 characters',
                'target': 'file_id'
            }
        }, 422

    callback_url: ParseResult = urlparse(payload.get('callback_url', None))
    if isinstance(callback_url.scheme, bytes):
        callback_url = None
    elif callback_url.scheme not in ['http', 'https']:
        return {
            'error': {
                'code': 'InvalidURL',
                'message': 'invalid callback_url, only support http(s) url',
                'target': 'callback_url'
            },
        }, 422

    task: Task = Task(
        uuid=uuid.uuid4(),
        file_id=file_id,
        file_url=str(file_url),
        finetune_args=json.dumps({
            'is_ocr': enable_ocr,
            'enable_formula': enable_formula,
            'enable_table': enable_table,
            'lang': prefer_language,
        }),
        callback_url=callback_url,
        status=Status.CREATED,
        result=Result.NONE_,
        created_at=arrow.now(current_app.config.get('TIMEZONE')),
        updated_at=arrow.now(current_app.config.get('TIMEZONE'))
    )

    database.session.add(task)
    database.session.commit()

    # todo add to queue

    return {
        'data': {
            'task_id': task.uuid,
        }
    }, 200


@extractor2.get('/task/<string:task_id>')
def query_task(task_id: str):

    task: Optional[Task] = database.session.scalars(
        select(Task).
        where(Task.uuid == task_id).
        order_by(Task.id.desc())
    ).first()

    if task is None:
        return {
            'error': {
                'code': 'NotFound',
                'message': 'task not found, please review task_id and try again',
                'target': 'task_id'
            },
        }, 404

    return {
        'data': TaskSchema().dump(task)
    }, 200
