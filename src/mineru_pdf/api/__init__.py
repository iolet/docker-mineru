import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

from ..exceptions import ExtraErrorCodes

logger = logging.getLogger(__name__)


def handle_server_error(e: Exception):

    logger.exception(e)

    if isinstance(e, HTTPException):
        error_code = e.__class__.__name__.split('.')[-1]
        error_message = e.description
        status_code = e.code
    else:
        error_code = getattr(e, 'code') or ExtraErrorCodes.INTERNAL_ERROR
        error_message = f'{e.__class__} {e}'
        status_code = 500

    return jsonify({
        'error': {
            'code': error_code,
            'message': error_message
        }
    }), status_code
