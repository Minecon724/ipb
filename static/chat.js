var uid = 0;
const textbox = document.getElementById("textbox");
const chat = document.getElementById("chat");
const popup = document.getElementById('popup');
const params = new URLSearchParams(window.location.search);

const socket = io({
    auth: {
        'key': params.get('key')
    }
});

socket.on('welcome', (data) => {
    this.uid = data['uid'];
    console.log(`My id is ${this.uid}`);
});

socket.on('message', (data) => {
    add_message(data['sender'], data['content']);
});

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

function add_message(sender, content) {
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
    console.log(content)
    send(content);
}

window.addEventListener('keypress', function(ev) {
    if (ev.key == 'Enter') sendmsg();
})