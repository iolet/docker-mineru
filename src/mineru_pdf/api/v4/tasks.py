import json
import logging
from typing import Optional
from uuid import uuid4

import arrow
from flask import Blueprint, current_app, jsonify, request
from flask_pydantic import validate
from flask_pydantic.exceptions import ValidationError
from sqlalchemy import select

from ...models import Task, database
from ...requests import TaskRequest
from ...tasks.constants import Errors, Result, Status
from ...tasks.miner import extract_pdf
from ...utils.presenters import TaskSchema

logger = logging.getLogger(__name__)

tasks: Blueprint = Blueprint('tasks', __name__)


@tasks.post('/tasks')
@validate()
def create(body: TaskRequest):

    task: Task = Task(
        uuid=str(uuid4()),
        file_id=body.file_id,
        file_url=str(body.file_url),
        finetune_args=json.dumps({
            'apply_ocr': body.apply_ocr,
            'enable_formula': body.enable_formula,
            'enable_table': body.enable_table,
            'target_language': body.prefer_language,
        }),
        callback_url=str(body.callback_url),
        status=Status.CREATED,
        result=Result.NONE_,
        errors=Errors.NONE_,
        created_at=arrow.now(current_app.config.get('TIMEZONE')).datetime,
        updated_at=arrow.now(current_app.config.get('TIMEZONE')).datetime
    )

    database.session.add(task)
    database.session.commit()

    # delivery to queue
    extract_pdf.delay(task.id) # type: ignore

    return jsonify({
        'data': {
            'task_id': task.uuid,
        }
    }), 200


@tasks.get('/tasks/<string:task_id>')
@validate()
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
    data: dict = TaskSchema().dump(task) # type: ignore

    if 'tarball' in data:
        if 'location' in data['tarball']:
            data['tarball']['location'] = host + data['tarball']['location']

    return jsonify({
        'data': data
    }), 200

@tasks.errorhandler(ValidationError)
def validate_failed(e: ValidationError):

    messages = { field['loc'][0]: field['msg'] for field in e.body_params } # type: ignore

    return jsonify({
        'error': {
            'code': 'ValidationError',
            'message': json.dumps(messages),
            'target': json.dumps(list(messages.keys()))
        },
    }), 422
