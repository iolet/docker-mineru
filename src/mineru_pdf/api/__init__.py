import logging
from flask import jsonify

from ..exceptions import ExtraErrorCodes

logger = logging.getLogger(__name__)


def handle_server_error(e: Exception):

    logger.exception(e)

    return jsonify({
        'error': {
            'code': getattr(e, 'code', ExtraErrorCodes.INTERNAL_ERROR),
            'message': f'{e.__class__} {e}'
        }
    }), 500
