
import psycopg2, os, click
from flask import current_app, g

POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_NAME = os.getenv('POSTGRES_NAME')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASS = os.getenv('POSTGRES_PASS')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = psycopg2.connect(dbname=POSTGRES_NAME, user=POSTGRES_USER, password=POSTGRES_PASS, host=POSTGRES_HOST)
    return db

def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        with app.open_resource('schema.sql', mode='r') as f:
            for line in f:
                cur.execute(line)
        cur.execute("TRUNCATE TABLE sessions")
        db.commit()

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)