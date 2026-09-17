from flask import Flask

from . import config


def create_app(overrides=None):
    cfg = {
        'DB_PATH': config.DB_PATH,
        'SECRET_KEY': config.SECRET_KEY,
        'TESTING': False,
    }
    if overrides:
        cfg.update(overrides)

    app = Flask(__name__, template_folder=config.TEMPLATES_DIR,
                static_folder=config.STATIC_DIR)
    app.config['SECRET_KEY'] = cfg['SECRET_KEY']
    app.config['TESTING'] = cfg['TESTING']

    from . import db
    db.DB_PATH = cfg['DB_PATH']
    db.bootstrap()

    from .routes import admin, ai, api, auth, chart, patients
    for blueprint in (auth.bp, patients.bp, chart.bp, ai.bp, admin.bp, api.bp):
        app.register_blueprint(blueprint)

    return app