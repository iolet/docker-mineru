import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

from ..exceptions import ExtraErrorCodes

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
            'code': getattr(e, 'code', ExtraErrorCodes.INTERNAL_ERROR.value),
            'message': f'{e.__class__} {e}'
        }
    }), 500
