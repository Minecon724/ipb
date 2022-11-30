from flask import Flask, request, g, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_apscheduler import APScheduler
import sqlite3, utils, time, mailer
import string, random, re, os
import dns.resolver
from math import floor

app = Flask(__name__)
app.config['SECRET_KEY'] = "5cb9de18113c3121974032fe411a3f123187c756bb957814f27dccedf59e3e27d3ff79a97e5994ad3f182fdd3514158275ee08283a11228ae880c91271e4c6bd"
socketio = SocketIO(app)

DATABASE = 'data.db'
URL = os.getenv("URL", 'http://127.0.0.1:5000/')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
init_db()

@app.route('/', methods=['GET'])
def page_home():
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
    user = cur.execute("SELECT id FROM users WHERE code=?", (code,)).fetchone()
    con.execute("UPDATE users SET confirmed=TRUE WHERE code=?", (code,))
    con.commit()
    if user == None: return "Invalid code", 404
    return "Registered successfully!"

@app.route('/register', methods=['POST'])
def page_register():
    data = request.form
    email = data['email']
    try:
        register(request.remote_addr, email)
    except Exception as e:
        return str(e)
    return "Now wait for a message"

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
    cur.execute('SELECT id FROM users WHERE ip=?', (ip,))
    if cur.fetchone() != None:
        raise ValueError("Duplicate")

    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
    cur.execute('SELECT MAX(id) FROM users')
    latest = cur.fetchone()
    uid = 0
    if latest[0] != None: uid = latest[0]+1
    con.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (uid, ip, email, False, code))
    con.commit()
    mailer.confirm(email, URL + 'confirm/' + code)
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
    user = cur.execute("SELECT id FROM users WHERE code=?", (code,)).fetchone()
    if user[0] == None: return None
    con.execute("DELETE FROM users WHERE id=?", (user[0],))
    con.commit()
    return user

@app.route('/api/accounts', methods=['GET'])
def accounts():
    if request.remote_addr != '127.0.0.1': return "Unauthorized", 403
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users")
    return str(cur.fetchall())

@socketio.on('connect')
def socket_connect(auth):
    cid = request.sid
    key = auth['key']
    with app.app_context():
        con = get_db()
        cur = con.cursor()

        cur.execute("SELECT chat,uid FROM keys WHERE key=?", (key,))
        room_info = cur.fetchone()
        if room_info == None:
            emit('error', {'code': -1, 'description': 'Invalid key'}) # Not found
            return
        
        con.execute("INSERT INTO sessions VALUES (?, ?, ?)", (cid,room_info[0],room_info[1]))
        con.commit()
        join_room(room_info[0])
        emit('success', {})
    emit('welcome', {'cid': cid, 'uid': room_info[1]})
    print("Connected")

@socketio.on('disconnect')
def socket_disconnect():
    cid = request.sid
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT chat,uid FROM sessions WHERE cid=?", (cid,))

@socketio.on('message')
def socket_message(data):
    print(data)
    cid = request.sid
    content = data['content']
    if len(content) > 200:
        emit('system', {'message': 'Message too long'})
        return
    with app.app_context():
        con = get_db()
        cur = con.cursor()

        cur.execute("SELECT chat,uid FROM sessions WHERE cid=?", (cid,))
        room = cur.fetchone()
        print(room)
        if room == None:
            emit('error', {'code': 1, 'description': 'Unauthorized'}) # Unauthorized
            return
        
        emit('message', {'sender': room[1], 'content': content}, to=room[0])

scheduler = APScheduler()
scheduler.api_enabled = True

@scheduler.task('interval', id='matcher', seconds=5, max_instances=1)
def matcher():
    print("Scan starting")
    start = time.time()
    mail_queue = {}
    queued = []
    with scheduler.app.app_context():
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        for i in users:
            cur.execute("SELECT u2 FROM matches WHERE u1=?", (i[0],))
            existing = [j[0] for j in cur.fetchall()]
            potential = [j for j in users if utils.distance(i[1], j[1]) < 255 and not i[0] == j[0] and not j[0] in existing]
            for j in potential:
                slist = sorted([i[0], j[0]])
                queued += [ ','.join([str(k) for k in slist]) ]
        for i in [*set(queued)]:
            u1, u2 = i.split(',')
            chid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
            chkey = [''.join(random.choices(string.ascii_uppercase + string.digits, k=128)) for _ in range(2)]
            con.execute("INSERT INTO matches VALUES (?, ?)", (u1, u2))
            con.execute("INSERT INTO matches VALUES (?, ?)", (u2, u1))
            con.execute("INSERT INTO keys VALUES (?, ?, ?)", (chkey[0], u1, chid))
            con.execute("INSERT INTO keys VALUES (?, ?, ?)", (chkey[1], u2, chid))
            dist = utils.distance(
                cur.execute("SELECT ip FROM users WHERE id=?", (u1,)).fetchone()[0],
                cur.execute("SELECT ip FROM users WHERE id=?", (u2,)).fetchone()[0]
            )
            mail_queue[u1] = [dist, chid, chkey[0]]
            mail_queue[u2] = [dist, chid, chkey[1]]
        con.commit()
        end = time.time()
        print("Scan took " + str( floor(end-start) ))
        for i in mail_queue:
            cur.execute("SELECT email,code FROM users WHERE id=?", (i,))
            data = cur.fetchone()
            chid = mail_queue[i][1]
            chkey = mail_queue[i][2]
            mailer.notify_new_match(data[0], mail_queue[i][0], URL + f"chat?key={chkey}", URL + 'unregister/' + data[1])
            #print(data[0], mail_queue[i][0], URL + f"chat?key={chkey}", URL + 'unregister/' + data[1])

scheduler.init_app(app)
scheduler.start()
socketio.run(app, host=os.getenv("HOST", '127.0.0.1'), port=os.getenv("PORT", '5000'), debug=False)