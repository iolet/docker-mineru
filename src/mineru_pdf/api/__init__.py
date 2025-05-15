import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def handle_server_error(e: Exception):

    logger.exception(e)

    if isinstance(e, HTTPException):
        return jsonify({
            'error': {
                'code': e.name,
                'message': str(e)
            }
        }), e.code

    return jsonify({
        'error': {
            'code': 'InternalError',
            'message': str(e)
        }
    }), 500
