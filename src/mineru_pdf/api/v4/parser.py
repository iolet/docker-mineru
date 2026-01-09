import json
import logging
import os
import shutil
import signal
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Dict, Optional

import arrow
from flask import Blueprint, current_app, jsonify, request
from filename_sanitizer import sanitize_path_fragment
from pydantic import ValidationError
from werkzeug.datastructures import FileStorage

from ...tasks.constants import Errors
from ...tasks.exceptions import GPUOutOfMemoryError
from ...utils.fileguard import file_check, receive_json, receive_text, pickup_images
from ...utils.requests import FileParseForm

parser: Blueprint = Blueprint('parser', __name__)
logger = logging.getLogger(__name__)


@parser.post('/file_parse')
def file_parse():

    uploaded_file: Optional[FileStorage] = request.files.get('file')
    form: FileParseForm = FileParseForm.model_validate({
        **request.form.to_dict(), 'file': uploaded_file
    })

    if uploaded_file is None:
        logger.fatal('file exists but passed validation rules')
        return jsonify({
            'error': {
                'code': Errors.SYS_INTERNAL_ERROR,
                'message': 'file: unaccepted rules passed',
            }
        }), 500

    timestamp: int = arrow.now(current_app.config.get('TIMEZONE')).int_timestamp

    cache_dir: Path = Path(mkdtemp(prefix=f'{timestamp}.', dir=str(
        Path(current_app.instance_path).joinpath('cache').resolve()
    )))
    input_file: Path = cache_dir.joinpath(
        sanitize_path_fragment(uploaded_file.filename),
    )

    uploaded_file.save(input_file)

    try:
        file_check(input_file)
    except Exception as e:
        return jsonify({
            'error': {
                'code': getattr(e, 'code', Errors.SYS_INTERNAL_ERROR),
                'message': f'{e}',
            }
        }), 400

    if not 'magic_file' in globals():
        from ...utils.magicfile import magic_file

    try:
        magic_file(input_file, cache_dir, **magic_kwargs) # type: ignore
    except GPUOutOfMemoryError as e:
        logger.warning(e, exc_info=True)
        os.kill(os.getpid(), signal.SIGTERM)
        return jsonify({
            'error': {
                'code': Errors.GPU_OUT_OF_MEMORY,
                'message': f'{e}'
            }
        }), 500
    except Exception as e:
        logger.exception(e)
        return jsonify({
            'error': {
                'code': getattr(e, 'code', Errors.SYS_INTERNAL_ERROR),
                'message': f'{e}'
            }
        }), 500

    data: Dict[str, Any] = {
        'md_content': receive_text(cache_dir.joinpath('content.md'))
    }

    if form.return_layout:
        data['layout'] = receive_json(
            cache_dir.joinpath('model.json')
        )

    if form.return_info:
        data['info'] = receive_json(
            cache_dir.joinpath('middle.json')
        )

    if form.return_content_list:
        data['content_list'] = receive_json(
            cache_dir.joinpath('content_list.json')
        )

    if form.return_images:
        data['images'] = pickup_images(
            cache_dir.joinpath('images')
        )

    shutil.rmtree(cache_dir)

    return jsonify(data)

@parser.errorhandler(ValidationError)
def validate_failed(e: ValidationError):

    errors = []
    for field in e.errors(): # type: ignore
        errors.append(str(field['loc'][0]) + ': ' + field['msg'].lower())

    return jsonify({
        'error': {
            'code': 'ValidationError',
            'message': '; '.join(errors),
        },
    }), 422
