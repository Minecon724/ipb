from flask import Flask, request, g, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_minify import Minify
from werkzeug.middleware.proxy_fix import ProxyFix
import psycopg2, utils, time
import string, random, re, os
import dns.resolver
from secrets import token_urlsafe, token_hex
from datetime import datetime
from math import floor
from dotenv import load_dotenv

load_dotenv()

PAPER_MAIL = bool(os.getenv('PAPER_MAIL'))
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_NAME = os.getenv('POSTGRES_NAME')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASS = os.getenv('POSTGRES_PASS')
URL = os.getenv('URL')

if not PAPER_MAIL: import mailer

app = Flask(__name__)
app.config['SECRET_KEY'] = "5cb9de18113c3121974032fe411a3f123187c756bb957814f27dccedf59e3e27d3ff79a97e5994ad3f182fdd3514158275ee08283a11228ae880c91271e4c6bd"
socketio = SocketIO(app)
Minify(app=app, html=True, js=True, cssless=True)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = psycopg2.connect(dbname=POSTGRES_NAME, user=POSTGRES_USER, password=POSTGRES_PASS, host=POSTGRES_HOST)
    return db

@app.teardown_appcontext
def close_connection(exception):
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
init_db()

@app.route('/', methods=['GET'])
def page_home():
    print(request.headers)
    return render_template('index.html')

@app.route('/chat', methods=['GET'])
def page_chat():
    return render_template('chat.html')

@app.route('/unregister/<code>', methods=['GET'])
def page_unregister(code):
    user = unregister(code)
    if user == None: return "Invalid code", 404
    return "Unsubscribed!"

@app.route('/confirm/<code>', methods=['GET'])
def page_confirm(code):
    con = get_db()
    cur = con.cursor()
    user = cur.execute("SELECT id FROM users WHERE code=%s", (code,))
    if user.fetchone() == None: return "Invalid code", 404
    cur.execute("UPDATE users SET confirmed=TRUE WHERE code=%s", (code,))
    con.commit()
    return "Registered successfully!"

@app.route('/register', methods=['POST'])
def page_register():
    data = request.form
    email = data['email']
    try:
        register(request.remote_addr, email)
    except Exception as e:
        return str(e)
    return "Check your inbox"

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    ip_addr = data['ip']
    email = data['email']
    return register(ip_addr, email)

def register(ip, email):
    print(ip, email)
    if re.search(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$", ip) == None:
        raise ValueError("Invalid IP address")
    dns.resolver.resolve(email.split("@")[1], 'MX')

    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT id FROM users WHERE ip=%s', (ip,))
    #if cur.fetchone() != None:
    #    raise ValueError("Duplicate")

    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
    cur.execute('SELECT MAX(id) FROM users')
    latest = cur.fetchone()
    uid = 1
    if latest[0] != None: uid = latest[0]+1
    cur.execute("INSERT INTO users VALUES (%s, %s, %s, %s, %s)", (uid, ip, email, False, code))
    con.commit()
    if not PAPER_MAIL: mailer.confirm(email, URL + 'confirm/' + code)
    else: print(email, URL + 'confirm/' + code)
    return {'id': uid, 'ip': ip, 'email': email, 'code': code}

@app.route('/api/unregister', methods=['POST'])
def api_unregister():
    data = request.json
    code = data['code']
    user = unregister(code)
    if user == None: return 'Invalid code', 404
    return {'id': user}

def unregister(code):
    con = get_db()
    cur = con.cursor()
    user = cur.execute("SELECT id FROM users WHERE code=%s", (code,))
    if user.fetchone() == None: return None
    cur.execute("DELETE FROM users WHERE id=%s", (user[0],))
    con.commit()
    return user

@app.route('/api/accounts', methods=['GET'])
def accounts():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users")
    return str(cur.fetchall())

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

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=4, x_proto=1, x_host=0, x_prefix=0
)
if __name__ == "__main__":
    socketio.run(app, host=os.getenv("HOST", '127.0.0.1'), port=os.getenv("PORT", '5000'), debug=True)