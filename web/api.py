import sys
sys.path.insert(1, '../lib')

import os, random, re, string
from flask import Blueprint, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import dns.resolver
from db import get_db

URL = os.getenv('URL')
PAPER_MAIL = bool(os.getenv('PAPER_MAIL'))

app = Blueprint('api', __name__, url_prefix='/api')

@app.route('/register', methods=['POST'])
def api_register():
    data = request.json
    ip_addr = data['ip']
    email = data['email']
    return register(ip_addr, email)

@app.route('/unregister', methods=['POST'])
def api_unregister():
    data = request.json
    code = data['code']
    user = unregister(code)
    if user == None: return 'Invalid code', 404
    return {'id': user}

@app.route('/confirm', methods=['POST'])
def api_confirm():
    data = request.json
    code = data['code']
    user = confirm(code)
    if user == None: return 'Invalid code', 404
    return {'id': user}

@app.route('/accounts', methods=['GET'])
def accounts():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users")
    return str(cur.fetchall())

def unregister(code):
    con = get_db()
    cur = con.cursor()
    user = cur.execute("SELECT id FROM users WHERE code=%s", (code,))
    if user.fetchone() == None: return None
    cur.execute("DELETE FROM users WHERE id=%s", (user[0],))
    con.commit()
    return user

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

def confirm(code):
    con = get_db()
    cur = con.cursor()
    user = cur.execute("SELECT id FROM users WHERE code=%s", (code,))
    if user.fetchone() == None: return None
    cur.execute("UPDATE users SET confirmed=TRUE WHERE code=%s", (code,))
    con.commit()
    return user