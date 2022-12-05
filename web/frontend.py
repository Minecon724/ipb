from flask import Blueprint, render_template, request
import api

app = Blueprint('frontend', __name__, url_prefix='/')

@app.route('/', methods=['GET'])
def page_home():
    print(request.headers)
    return render_template('index.html')

@app.route('/unregister/<code>', methods=['GET'])
def page_unregister(code):
    user = api.unregister(code)
    if user == None: return "Invalid code", 404
    return "Unsubscribed!"

@app.route('/confirm/<code>', methods=['GET'])
def page_confirm(code):
    user = api.confirm(code)
    if user == None: return "Invalid code", 404
    return "Registered successfully!"

@app.route('/register', methods=['POST'])
def page_register():
    data = request.form
    email = data['email']
    try:
        api.register(request.remote_addr, email)
    except Exception as e:
        return str(e)
    return "Check your inbox"