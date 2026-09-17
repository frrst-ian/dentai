import secrets

from flask import abort, current_app, request, session

# Lightweight session-based CSRF protection covering all state-changing
# requests (forms and JSON APIs). A token is minted per session and must be
# echoed back via a `csrf_token` form field or the `X-CSRF-Token` header.
_TOKEN_KEY = '_csrf_token'


def generate_csrf_token():
    token = session.get(_TOKEN_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_TOKEN_KEY] = token
    return token


def _submitted_token():
    form = request.values
    if form and form.get('csrf_token'):
        return form.get('csrf_token')
    payload = request.get_json(silent=True) or {}
    if payload.get('csrf_token'):
        return payload.get('csrf_token')
    return request.headers.get('X-CSRF-Token')


def protect():
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return None
    expected = session.get(_TOKEN_KEY)
    if not expected or not secrets.compare_digest(expected, _submitted_token() or ''):
        abort(403)
    return None


def init_app(app):
    @app.before_request
    def _csrf_protect():
        return protect()

    @app.context_processor
    def _csrf_context():
        return {'csrf_token': generate_csrf_token()}