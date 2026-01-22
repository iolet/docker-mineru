import logging
import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Dict, Optional, Union

import arrow
from flask import Blueprint, current_app, g, jsonify, request
from filename_sanitizer import sanitize_path_fragment
from pydantic import ValidationError
from werkzeug.datastructures import FileStorage

from ...tasks.constants import Errors
from ...tasks.exceptions import GPUOutOfMemoryError
from ...utils.fileguard import file_check, load_json_file, read_text_file, pickup_images
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

    days: str = arrow.now(current_app.config.get('TIMEZONE')).format('YYYY-MM-DD')

    cache_dir: Path = Path(mkdtemp(prefix=f'uploaded.{days}.', dir=str(
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
        from ...utils.magicfile import magic_args, magic_file

    magic_kwargs: Dict[str, Union[str, bool, None]] = magic_args(dict(filter( # type: ignore
        lambda item: item[1] is not None, {
            'parser_engine': form.parser_engine,
            'parser_prefer': form.parser_prefer,
            'target_language': form.target_language,
            'enable_table': form.enable_table,
            'enable_formula': form.enable_formula,
            'apply_scaled': form.apply_scaled,
            'vllm_endpoint': current_app.config.get('VLLM_ENDPOINT'),
        }.items()
    )))

    try:
        magic_file(input_file, cache_dir, **magic_kwargs) # type: ignore
    except GPUOutOfMemoryError as e:
        g.is_vram_full = True
        logger.warning(e, exc_info=True)
        r = jsonify({
            'error': {
                'code': Errors.GPU_OUT_OF_MEMORY,
                'message': f'{e}'
            }
        })
        r.retry_after = arrow.now(
            current_app.config.get('TIMEZONE')
        ).shift(seconds=200).datetime
        return r, 503
    except Exception as e:
        logger.exception(e)
        return jsonify({
            'error': {
                'code': getattr(e, 'code', Errors.SYS_INTERNAL_ERROR),
                'message': f'{e}'
            }
        }), 500

    data: Dict[str, Any] = {
        'md_content': read_text_file(cache_dir.joinpath('content.md'))
    }

    if form.apply_scaled:
        data['scaled'] = [ 'content_list', 'layout' ]

    if form.return_layout:
        data['layout'] = load_json_file(
            cache_dir.joinpath('model.scaled.json' if form.apply_scaled else 'model.json')
        )

    if form.return_info:
        data['info'] = load_json_file(
            cache_dir.joinpath('middle.json')
        )

    if form.return_content_list:
        data['content_list'] = load_json_file(
            cache_dir.joinpath('content_list.scaled.json' if form.apply_scaled else 'content_list.json')
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
