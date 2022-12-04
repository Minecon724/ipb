var uid = 0;
const textbox = document.getElementById("textbox");
const chat = document.getElementById("chat");
const popup = document.getElementById('popup');
const status = document.getElementById('status');
const nickname = document.getElementById('nickname');
const params = new URLSearchParams(window.location.search);
const e2eKey = params.get('enc');

const start = new Date();
const socket = io({
    auth: {
        'key': params.get('key'),
        'history': true
    }
});

socket.on('connect', () => {
    console.log(socket.auth.history);
    notify(`Connected (${new Date() - start}ms)`);
})

socket.on('disconnect', (reason) => {
    socket.auth.history = false;
    notify(`Disconnected: ${reason}`);
});

socket.on('welcome', (data) => {
    this.uid = data['uid'];
    console.log(`My id is ${this.uid}`);
});

socket.on('message', (data) => {
    (async() => {
        const message = await openpgp.readMessage({ armoredMessage: data['content'] });
        const {data: decrypted} = await openpgp.decrypt({
            message,
            passwords: [e2eKey],
            format: 'armored'
        });
        add_message(data['sender'], data['timestamp'], decrypted);
    })();
});

socket.on('status', (data) => {
    console.log(data);
    if (data['uid'] == uid) return;
    var online = data['online'];
    const text = online ? 'Online' : 'Offline';
    const color = online ? 'rgb(100,255,100)' : 'rgb(255,100,100)';
    status.innerText = text;
    status.style.backgroundColor = color;
})

var editing = false;
nickname.addEventListener('blur', function() {
    if (editing) {
        socket.emit('nickname', {'nickname': nickname.innerText});
        console.log('Nickname set');
    }
    editing = false;
})
nickname.addEventListener('input', function() {
    editing = true;
    console.log(nickname.innerText);
})

socket.on('nickname', (data) => {
    nickname.innerText = data['nickname'];
})

socket.on('system', (data) => {
    notify(data['message']);
});

socket.on('error', (data) => {
    console.log("Error " + data["code"]);
    notify("Error: " + data['description']);
});

function notify(content) {
    popup.style.display = 'block';
    popup.innerText = content;
    hideAt = Date.now() + 4000;
    setTimeout(() => { if (hideAt < Date.now()) popup.style.display = 'none'; }, 4200);
}

function add_message(sender, timestamp, content) {
    console.log(`New message by ${sender}: ${content}`);

    const line = document.createElement('div');
    line.className = 'message';
    if (sender == uid) line.classList.add('own');

    const div = document.createElement('div');
    div.innerText = content;

    line.appendChild(div);
    chat.appendChild(line);
    chat.scrollTo({top: chat.scrollHeight, behavior: 'smooth'});
}

function send(content) {
    socket.emit('message', {'content': content});
}

function sendmsg() {
    var content = textbox.value;
    if (content.length == 0) return;
    textbox.value = '';
    console.log(content);

    (async() => {
        const message = await openpgp.createMessage({ text: content });
        const encrypted = await openpgp.encrypt({
            message,
            passwords: [e2eKey],
            format: 'armored'
        });
        send(encrypted);
    })();
}

window.addEventListener('keypress', function(ev) {
    if (ev.key == 'Enter') sendmsg();
})

var switched = false;
setInterval(function() {
    if (!switched) document.title = nickname.innerText + " | FriendProtocol";
    else document.title = "C | FriendProtocol";
    switched = !switched;
}, 5000);