CREATE TABLE IF NOT EXISTS users(id serial PRIMARY KEY, ip varchar, email varchar, confirmed boolean, code varchar);
CREATE TABLE IF NOT EXISTS matches(u1 serial, u2 serial);
CREATE TABLE IF NOT EXISTS keys(key varchar PRIMARY KEY, uid serial, chat varchar);
CREATE TABLE IF NOT EXISTS sessions(cid varchar PRIMARY KEY, chat varchar, uid serial);
CREATE TABLE IF NOT EXISTS nicknames(uid serial PRIMARY KEY, chat varchar, nickname varchar, unique(uid,chat));
CREATE TABLE IF NOT EXISTS messages(chat varchar, sender serial, timestamp bigserial, content varchar);