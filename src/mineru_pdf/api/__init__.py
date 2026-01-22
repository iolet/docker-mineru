import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

from ..tasks.constants import Errors

logger = logging.getLogger(__name__)


def handle_server_error(e: Exception):

    if isinstance(e, HTTPException):
        return jsonify({
            'error': {
                'code': e.name,
                'message': str(e)
            }
        }), e.code

    logger.exception(e)

    return jsonify({
        'error': {
            'code': Errors.SYS_INTERNAL_ERROR,
            'message': f'{e.__class__} {e}'
        }
    }), 500
