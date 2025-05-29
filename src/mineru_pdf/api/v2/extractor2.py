import json
import logging
from re import sub as preg_replace
from typing import Optional, Union
from urllib.parse import ParseResult, urlparse
from uuid import uuid4

import arrow
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from ...models import Task, database
from ...tasks.constants import Errors, Result, Status
from ...tasks.mineru import extract_pdf
from ...utils.presenters import TaskSchema

logger = logging.getLogger(__name__)

extractor2: Blueprint = Blueprint('extractor2', __name__)


@extractor2.post('/extract/task')
def create():

    try:
        payload: dict = request.json
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

    apply_ocr: Union[bool, str] = payload.get('apply_ocr', True)
    if apply_ocr in ['yes', 'true', True]:
        apply_ocr: bool = True
    elif apply_ocr in ['no', 'false', False]:
        apply_ocr: bool = False
    else:
        return {
            'error': {
                'code': 'UnsupportedValue',
                'message': f'unknown value {apply_ocr},'
                           f'only support bool (true, false) or string (true false yes and no)',
                'target': 'apply_ocr'
            }
        }, 422

    enable_table: Union[bool, str] = payload.get('enable_table', False)
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
    if not isinstance(file_id, str) or file_id.isspace():
        return {
            'error': {
                'code': 'EmptyOrMissingValue',
                'message': 'file_id empty or missing, please ensure it present and not empty',
                'target': 'file_id'
            }
        }, 422
    elif preg_replace(r'[a-zA-z0-9-]', '', file_id).isspace():
        return {
            'error': {
                'code': 'UnsupportedValue',
                'message': 'file_id value should be ensure contain alphabets, numbers and dashes only',
                'target': 'file_id'
            }
        }, 422
    elif len(file_id) > 128:
        return {
            'error': {
                'code': 'ExceedMaximum',
                'message': 'file_id length should be less 128 characters',
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
        uuid=str(uuid4()),
        file_id=file_id,
        file_url=file_url.geturl(),
        finetune_args=json.dumps({
            'apply_ocr': apply_ocr,
            'enable_formula': enable_formula,
            'enable_table': enable_table,
            'target_language': prefer_language,
        }),
        callback_url=callback_url.geturl() if isinstance(callback_url, ParseResult) else '',
        status=Status.CREATED,
        result=Result.NONE_,
        errors=Errors.NONE_,
        created_at=arrow.now(current_app.config.get('TIMEZONE')).datetime,
        updated_at=arrow.now(current_app.config.get('TIMEZONE')).datetime
    )

    database.session.add(task)
    database.session.commit()

    # delivery to queue
    extract_pdf.delay(task.id)

    return jsonify({
        'data': {
            'task_id': task.uuid,
        }
    }), 200


@extractor2.get('/extract/task/<string:task_id>')
def fetch(task_id: str):

    task: Optional[Task] = database.session.scalars(
        select(Task).
        where(Task.uuid == task_id).
        order_by(Task.id.desc())
    ).first()

    if task is None:
        return jsonify({
            'error': {
                'code': 'NotFound',
                'message': 'task not found, please review task_id and try again',
                'target': 'task_id'
            },
        }), 404

    host: str = request.host_url
    data: dict = TaskSchema().dump(task)

    if 'tarball' in data:
        if 'location' in data['tarball']:
            data['tarball']['location'] = host + data['tarball']['location']

    return jsonify({
        'data': data
    }), 200
