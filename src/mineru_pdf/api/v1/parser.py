import logging
import json
import os
import shutil
import signal
from base64 import b64encode
from pathlib import Path
from tempfile import mkdtemp
from typing import Optional, Union

import arrow
from flask import Blueprint, current_app, jsonify, render_template_string, request
from filename_sanitizer import sanitize_path_fragment
from werkzeug.datastructures import FileStorage

from ...tasks.constants import Errors
from ...tasks.exceptions import GPUOutOfMemoryError
from ...utils.fileguard import file_check, img2pdf, doc2pdf

logger = logging.getLogger(__name__)

parser: Blueprint = Blueprint('parser', __name__)


@parser.get('/docs')
def fake_docs():
    moment = arrow.now().format(arrow.FORMAT_RFC3339)
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="zh-CN">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>mineru fake docs</title>
        <style>
          body {
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
          }
        </style>
      </head>
      <body>
        <div><h2>FAKE DOCS</h2></div>
        <div>{{ moment }}</div>
      </body>
    </html>
    ''', moment=moment)

@parser.post('/pdf_parse')
@parser.post('/file_parse')
def pdf_parse():

    if 'pdf_file' in request.files:
        uploaded_file: FileStorage = request.files['pdf_file']
    elif 'file' in request.files:
        uploaded_file: FileStorage = request.files['file']
    else:
        return jsonify({
            'error': 'pdf_file and file are missing'
        }), 400

    if '' == uploaded_file.filename:
        return jsonify({
            'error': 'pdf_file and file are not found, make sure it selected'
        }), 400

    timestamp: int = arrow.now(current_app.config.get('TIMEZONE')).int_timestamp

    cache_dir: Path = Path(mkdtemp(prefix=f'{timestamp}.', dir=str(
        Path(current_app.instance_path).joinpath('cache').resolve()
    )))
    input_file: Path = cache_dir.joinpath(
        sanitize_path_fragment(uploaded_file.filename),
    )
    tune_args: dict = {
        'ocr': True, 'table_enable': True
    }

    uploaded_file.save(input_file)

    try:

        if input_file.suffix in [ '.png', '.jpg', '.jpeg', ]:
            input_file = img2pdf(input_file)

        if input_file.suffix in [ '.docx', '.pptx', '.doc', '.ppt', ]:
            input_file = doc2pdf(input_file)

        file_check(input_file)

    except Exception as e:
        return jsonify({
            'error': str(e),
            'detail': {
                'code': getattr(e, 'code', Errors.SYS_INTERNAL_ERROR),
                'message': f'{e}'
            }
        }), 400

    if not 'magic_file' in globals():
        from ...utils.magicfile import magic_file

    try:
        magic_file(input_file, cache_dir, **tune_args)
    except GPUOutOfMemoryError as e:
        logger.warning(e, exc_info=True)
        os.kill(os.getpid(), signal.SIGTERM)
        return jsonify({
            'error': str(e),
            'detail': {
                'code': Errors.GPU_OUT_OF_MEMORY,
                'message': f'{e}'
            }
        }), 500
    except Exception as e:
        logger.exception(e)
        return jsonify({
            'error': str(e),
            'detail': {
                'code': getattr(e, 'code', Errors.SYS_INTERNAL_ERROR),
                'message': f'{e}'
            }
        }), 500

    data = {
        'md_content': receive_text(cache_dir.joinpath('content.md'))
    }

    if semantic_bool(request.args.get('return_layout'), False):
        data['layout'] = receive_json(
            cache_dir.joinpath('model.json')
        )

    if semantic_bool(request.args.get('return_info'), False):
        data['info'] = receive_json(
            cache_dir.joinpath('middle.json')
        )

    if semantic_bool(request.args.get('return_content_list'), False):
        data['content_list'] = receive_json(
            cache_dir.joinpath('content_list.json')
        )

    if semantic_bool(request.args.get('return_images'), False):
        data['images'] = pickup_images(
            cache_dir.joinpath('images')
        )

    shutil.rmtree(cache_dir)

    return jsonify(data)

def receive_json(file: Path):
    return json.loads(receive_text(file))

def receive_text(file: Path) -> Optional[str]:
    with file.open('r') as f:
        return f.read()

def locate_image(image: Path) -> str:
    return image.name

def encode_image(image: Path) -> Optional[str]:
    with image.open('rb') as f:
        return f'data:image/jpeg;base64,{b64encode(f.read()).decode()}'

def pickup_images(image_dir: Path) -> dict:
    return {
        locate_image(image) : encode_image(image) for image in image_dir.glob('*.jpg')
    }

def semantic_bool(input_: Union[str, bool, None], default: bool) -> bool:

    if input_ is None:
        return False

    if isinstance(input_, bool):
        return input_

    if isinstance(input_, str) and input_.isspace():
        return False

    parsed = input_.strip().lower()

    if parsed in ['true', 'yes', 'y', '1']:
         return True

    if parsed in ['false', 'no', 'n', '0', '']:
        return False

    return default
