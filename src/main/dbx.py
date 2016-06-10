# coding=utf-8
# Created by 0xFranCiS on May 10, 2016.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from redis import StrictRedis, ConnectionPool

engine = create_engine('postgresql://postgres:postgres@localhost/lively', echo=True)
# engine = create_engine('sqlite://')

session_factory = sessionmaker(bind=engine)

Session = scoped_session(session_factory)


@contextmanager
def open_session():
    s = session_factory()
    try:
        yield s
        s.commit()
    except:
        s.rollback()
        raise
    finally:
        s.close()


def open_conn():
    return engine.connect()


redis = StrictRedis(decode_responses=True)


def db2redis_user():
    with open_conn() as conn:
        id_name = 'identifier_user'
        sql = 'SELECT username, name, password, archived, active, alias FROM t_user'
        cur = conn.execute(sql)
        rs = cur.fetchall()
        pipe = redis.pipeline()
        pipe.multi()
        pipe.delete(id_name)
        for r in rs:
            pipe.hmset('user:%s' % r[0], {
                'username': r[0],
                'name': r[1],
                'password': r[2],
                'archived': r[3],
                'active': r[4],
                'alias': r[5]
            })
            pipe.sadd(id_name, r[0])
            sql = 'SELECT p.code FROM user_permission_header t, permission p WHERE t.permission_fk = p.id AND t.user_fk =%s;'
            cur = conn.execute(sql, r[0])
            rrs = cur.fetchall()
            if rrs:
                pipe.delete('user_permissions#%s' % r[0])
                pipe.sadd('user_permissions#%s' % r[0], *[e[0] for e in rrs])
        pipe.execute()

# db2redis_user()


def lazy_session(nxt):
    try:
        rv = nxt()
        Session.commit()
        return rv
    except:
        Session.rollback()
        raise
    finally:
        Session.remove()
