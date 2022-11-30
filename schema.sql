CREATE TABLE IF NOT EXISTS users(id int PRIMARY KEY, ip string, email string, confirmed int, code string);
CREATE TABLE IF NOT EXISTS matches(u1 int, u2 int);
CREATE TABLE IF NOT EXISTS keys(key string PRIMARY KEY, uid int, chat int);
CREATE TABLE IF NOT EXISTS chatrooms(id int PRIMARY KEY);
CREATE TABLE IF NOT EXISTS sessions(cid int PRIMARY KEY, chat string, uid int);