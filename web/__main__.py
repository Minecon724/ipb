import sys
sys.path.insert(1, '../lib')

from flask import Flask, request, g
from flask_minify import Minify
from werkzeug.middleware.proxy_fix import ProxyFix
import utils, time
import string, random, re, os
from dotenv import load_dotenv
import api, frontend, db

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = SECRET_KEY
    Minify(app=app, html=True, js=True, cssless=True)

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=4, x_proto=1, x_host=0, x_prefix=0
    )
    app.register_blueprint(api.app)
    app.register_blueprint(frontend.app)
    db.init_app(app)
    db.init_db()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host=os.getenv("HOST", '127.0.0.1'), port=os.getenv("PORT", '5000'), debug=True)