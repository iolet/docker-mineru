from flask import jsonify
from flask_httpauth import HTTPTokenAuth
from sqlalchemy import select

from .extensions import database
from .models import Bearer

bearer = HTTPTokenAuth()

@bearer.verify_token
def verify_token(token: str):
    return database.session.scalars(
        select(Bearer).
        where(Bearer.token == token).
        order_by(Bearer.id.desc())
    ).first()

@bearer.error_handler
def auth_error(status: int):

    if 401 == status:
        return jsonify({
            'error': {
                'code': 'ACCESS_DENIED',
                'message': 'token invalid or missing'
            }
        }), status

    if 403 == status:
        return jsonify({
            'error': {
                'code': 'ACCESS_FORBIDDEN',
                'message': 'no permission for entry'
            }
        }), status

    return jsonify({
        'error': {
            'code': 'UNKNOWN_AUTH_PROVIDER',
            'message': 'unknown auth provider'
        }
    }), status

@bearer.get_user_roles
def get_bearer_labels(bearer: Bearer):
    return [ label.strip().lower() for label in bearer.labels.split(',')]
