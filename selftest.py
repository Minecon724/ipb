import requests, random

URL = "http://127.0.0.1:5000/"
ACCOUNTS = 1000
codes = []
"""
for i in range(ACCOUNTS):
    re = requests.post(URL + 'api/register', json={
        'ip': '.'.join([str(random.randint(0,255)) for _ in range(4)]),
        'email': 'test@example.invalid' + str(i)
    })
    if bool(random.getrandbits(1)): codes.append(re.json()['code'])

for i in codes:
    requests.post(URL + 'api/unregister', json={'code': i})
"""

re = requests.post(URL + 'api/register', json={
    'ip': '0.0.0.5',
    'email': 'fkzkytnm@sharklasers.com'
})
re = requests.post(URL + 'api/register', json={
    'ip': '0.0.0.0',
    'email': 'rnvmzhlz@sharklasers.com'
})

print(requests.get(URL + 'api/accounts').text)