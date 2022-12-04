from secrets import token_hex, token_urlsafe
import time, utils
from math import floor

def scan(con, mailer, URL):
    print("Scan starting")
    start = time.time()
    mail_queue = {}
    queued = []

    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    for i in users:
        cur.execute("SELECT u2 FROM matches WHERE u1=%s", (i[0],))
        existing = [j[0] for j in cur.fetchall()]
        potential = [j for j in users if utils.distance(i[1], j[1]) < 255 and not i[0] == j[0] and not j[0] in existing]
        for j in potential:
            slist = sorted([i[0], j[0]])
            queued += [ ','.join([str(k) for k in slist]) ]

    for i in [*set(queued)]:
        u1, u2 = i.split(',')
        chid = token_hex(24)
        chkey = [token_urlsafe(64) for _ in range(2)]
        e2e_key = token_urlsafe(128)
        cur.execute("INSERT INTO matches VALUES (%s, %s)", (u1, u2))
        cur.execute("INSERT INTO matches VALUES (%s, %s)", (u2, u1))
        cur.execute("INSERT INTO keys VALUES (%s, %s, %s)", (chkey[0], u1, chid))
        cur.execute("INSERT INTO keys VALUES (%s, %s, %s)", (chkey[1], u2, chid))

        cur.execute("SELECT ip FROM users WHERE id=%s", (u1,))
        u1_ip = cur.fetchone()[0]
        cur.execute("SELECT ip FROM users WHERE id=%s", (u2,))
        u2_ip = cur.fetchone()[0]
        dist = utils.distance(u1_ip, u2_ip)
        mail_queue[u1] = [dist, chid, chkey[0], e2e_key]
        mail_queue[u2] = [dist, chid, chkey[1], e2e_key]

    con.commit()
    end = time.time()

    for i in mail_queue:
        cur.execute("SELECT email,code FROM users WHERE id=%s", (i,))
        data = cur.fetchone()
        chid = mail_queue[i][1]
        chkey = mail_queue[i][2]
        e2e_key = mail_queue[i][3]
        if mailer: mailer.notify_new_match(data[0], mail_queue[i][0], URL + f"chat?key={chkey}&enc={e2e_key}", URL + 'unregister/' + data[1])
        else: print(data[0], mail_queue[i][0], URL + f"chat?key={chkey}&enc={e2e_key}", URL + 'unregister/' + data[1])
        
    print("Scan took " + str( floor(end-start) ))

if __name__ == '__main__':
    from dotenv import load_dotenv
    import psycopg2, os
    load_dotenv()

    PAPER_MAIL = bool(os.getenv('PAPER_MAIL'))
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_NAME = os.getenv('POSTGRES_NAME')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASS = os.getenv('POSTGRES_PASS')
    URL = os.getenv('URL')
    if not PAPER_MAIL: import mailer

    scan(
        psycopg2.connect(dbname=POSTGRES_NAME, user=POSTGRES_USER, password=POSTGRES_PASS, host=POSTGRES_HOST),
        None if PAPER_MAIL else mailer,
        URL
    )