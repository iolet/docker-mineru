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

from ...auth import bearer
from ...constants import ParserEngines, TokenLabels
from ...exceptions import ExtraErrorCodes, GPUOutOfMemoryException
from ...requests import FileParseForm
from ...utils.fileguard import file_check, load_json_file, read_text_file, pickup_images

parser: Blueprint = Blueprint('parser', __name__)
logger = logging.getLogger(__name__)


@parser.post('/file_parse')
@bearer.login_required(role=TokenLabels.FILES)
def file_parse():

    uploaded_file: Optional[FileStorage] = request.files.get('file')
    form: FileParseForm = FileParseForm.model_validate({
        **request.form.to_dict(), 'file': uploaded_file
    })

    if uploaded_file is None:
        logger.fatal('file exists but passed validation rules')
        return jsonify({
            'error': {
                'code': ExtraErrorCodes.INTERNAL_ERROR,
                'message': 'file: unaccepted rules passed',
            }
        }), 500

    days: str = arrow.now(current_app.config.get('TIMEZONE')).format('YYYY-MM-DD')

    cache_dir: Path = Path(mkdtemp(prefix=f'uploaded.{days}_', dir=str(
        Path(current_app.instance_path).joinpath('cache').resolve()
    )))
    input_file: Path = cache_dir.joinpath(
        sanitize_path_fragment(uploaded_file.filename),
    )

    uploaded_file.save(input_file)

    try:
        file_check(input_file, max_page=500)
    except Exception as e:
        return jsonify({
            'error': {
                'code': getattr(e, 'code', ExtraErrorCodes.INTERNAL_ERROR),
                'message': f'{e}',
            }
        }), 400

    if not 'magic_file' in globals():
        from ...utils.magicfile import magic_args, magic_file

    magic_kwargs: Dict[str, Union[str, bool, None]] = magic_args({ # type: ignore
        'parser_engine': form.parser_engine,
        'parser_prefer': form.parser_prefer,
        'target_language': form.target_language,
        'enable_table': form.enable_table,
        'enable_formula': form.enable_formula,
        'apply_scaled': form.apply_scaled,
        'vllm_endpoint': current_app.config.get('VLLM_ENDPOINT'),
    })

    try:
        magic_file(input_file, cache_dir, **magic_kwargs) # type: ignore
    except GPUOutOfMemoryException as e:
        g.is_vram_full = True
        logger.warning(e, exc_info=True)
        r = jsonify({
            'error': {
                'code': e.code,
                'message': f'{e}'
            }
        })
        r.retry_after = arrow.now(
            current_app.config.get('TIMEZONE')
        ).shift(seconds=200).datetime
        return r, 503

    data: Dict[str, Any] = {}

    if form.apply_scaled:
        data['scaled'] = [ 'layout' ]
        if ParserEngines.PIPELINE == form.parser_engine:
            data['scaled'].append('content_list')
        else:
            data['scaled'].append('content_list_v2')

    if form.return_md:
        data['md_content'] = read_text_file(cache_dir.joinpath('content.md'))

    if form.return_info:
        data['info'] = load_json_file(
            cache_dir.joinpath('middle.json')
        )

    if form.return_content_list:

        if ParserEngines.PIPELINE == form.parser_engine:
            data['content_list'] = load_json_file(
                cache_dir.joinpath('content_list.scaled.json' if form.apply_scaled else 'content_list.json')
            )
        else:
            data['content_list_v2'] = load_json_file(
                cache_dir.joinpath('content_list_v2.scaled.json' if form.apply_scaled else 'content_list_v2.json')
            )

    if form.return_layout:
        data['layout'] = load_json_file(
            cache_dir.joinpath('model.scaled.json' if form.apply_scaled else 'model.json')
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
            'code': ExtraErrorCodes.VALIDATION_FAIL,
            'message': '; '.join(errors),
        },
    }), 422
