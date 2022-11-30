import smtplib, ssl
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

my_name = "FriendProtocol"
my_address = "notifications@3craft.xyz"
password = "f6uF_1k3"


def auth():
    server = smtplib.SMTP_SSL("mail.3craft.xyz", context=ssl.create_default_context())
    server.login(my_address, password)
    return server

server = auth()

def notify_new_match(recipent, distance, chat_url, unsub_url):
    global server
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "IP buddy spotted!"
    msg['From'] = f"{my_name} <{my_address}>"
    msg['To'] = recipent
    msg['Date'] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S %z")
    msg.attach(MIMEText(
    f"""A new IP buddy was found!<br>
    They're {distance} addresses far from you.
    <br><br>
    <a href="{chat_url}">Click here to chat</a>
    <br><br>
    <a href="{unsub_url}">Click here to unsubscribe</a>
    """, 'html'))
    try:
        server.sendmail(my_address, recipent, msg.as_string())
    except smtplib.SMTPSenderRefused:
        server = auth()

def confirm(recipent, url):
    global server
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Please confirm your FriendProtocol account"
    msg['From'] = f"{my_name} <{my_address}>"
    msg['To'] = recipent
    msg['Date'] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S %z")
    msg.attach(MIMEText(
    f"""<a href="{url}">Click here to confirm your account</a><br>
    If you didn't request an account, ignore this email.
    """
    , 'html'))
    try:
        server.sendmail(my_address, recipent, msg.as_string())
    except smtplib.SMTPSenderRefused:
        server = auth()