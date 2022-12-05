import os, psycopg2
from flask import Flask, g
from flask_socketio import SocketIO, join_room, leave_room, emit
from werkzeug.middleware.proxy_fix import ProxyFix

from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
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

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = SECRET_KEY

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=4, x_proto=1, x_host=0, x_prefix=0
    )

    return app

app = create_app()
socketio = SocketIO(app)

@app.route('/chat', methods=['GET'])
def page_chat():
    return render_template('chat.html')

@socketio.on('connect')
def socket_connect(auth):
    cid = request.sid
    key = auth['key']
    history = auth['history']
    print(history)
    with app.app_context():
        con = get_db()
        cur = con.cursor()

        cur.execute("SELECT chat,uid FROM keys WHERE key=%s", (key,))
        room_info = cur.fetchone()
        if room_info == None:
            emit('error', {'code': -1, 'description': 'Invalid key'}) # Not found
            return
        
        cur.execute("INSERT INTO sessions VALUES (%s, %s, %s)", (cid,room_info[0],room_info[1]))
        con.commit()
        join_room(room_info[0])
        emit('success', {})
        emit('welcome', {'cid': cid, 'uid': room_info[1]})
        emit('status', {'uid': room_info[1], 'online': True}, to=room_info[0])
        cur.execute("SELECT uid FROM sessions WHERE chat=%s AND NOT uid=%s", room_info)
        recipent = cur.fetchone()
        if recipent != None:
            emit('status', {'uid': recipent[0], 'online': True}, to=room_info[0])

        cur.execute("SELECT nickname FROM nicknames WHERE chat=%s AND uid=%s", room_info)
        nickname = cur.fetchone()
        print("Nn", nickname)
        if nickname != None:
            emit('nickname', {'nickname': nickname[0]})
        if history:
            cur.execute("SELECT sender,timestamp,content FROM messages WHERE chat=%s ORDER BY timestamp ASC LIMIT 25", (room_info[0],))
            for m in cur.fetchall():
                emit('message', {'sender': m[0], 'timestamp': m[1], 'content': m[2]})
        
    print("Connected")

@socketio.on('disconnect')
def socket_disconnect():
    with app.app_context():
        cid = request.sid
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT chat,uid FROM sessions WHERE cid=%s", (cid,))
        room = cur.fetchone()
        print(room)
        if room == None:
            return

        cur.execute("DELETE FROM sessions WHERE cid=%s", (cid,))
        con.commit()

        cur.execute("SELECT chat,cid FROM sessions WHERE uid=%s", (room[1],))
        if cur.fetchone() == None:
            emit('status', {'uid': room[1], 'online': False}, to=room[0])

@socketio.on('message')
def socket_message(data):
    cid = request.sid
    content = data['content']
    timestamp = datetime.utcnow().timestamp() * 1000
    if len(content) > 2000:
        emit('system', {'message': 'Message too long'})
        return
    with app.app_context():
        con = get_db()
        cur = con.cursor()

        cur.execute("SELECT chat,uid FROM sessions WHERE cid=%s", (cid,))
        room = cur.fetchone()
        print(room)
        if room == None:
            emit('error', {'code': 1, 'description': 'Unauthorized'}) # Unauthorized
            return
        
        emit('message', {'sender': room[1], 'timestamp': timestamp, 'content': content}, to=room[0])
        cur.execute("INSERT INTO messages VALUES (%s, %s, %s, %s)", (room[0], room[1], timestamp, content))
        con.commit()

@socketio.on('load')
def socket_load(data):
    # TODO
    last = data['last']

@socketio.on('nickname')
def socket_nickname(data):
    cid = request.sid
    nickname = data['nickname']
    with app.app_context():
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT uid,chat FROM sessions WHERE cid=%s", (cid,))
        info = cur.fetchone()
        if info == None:
            emit('system', {'message': 'wat'})
            return

        print((nickname,) + info)
        cur.execute("INSERT INTO nicknames (uid,chat,nickname) VALUES (%s, %s, %s) ON CONFLICT (uid,chat) DO UPDATE SET nickname=EXCLUDED.nickname", info + (nickname,))
        con.commit()
        emit('system', {'message': 'Nickname saved'})

if __name__ == "__main__":
    socketio.run(app)