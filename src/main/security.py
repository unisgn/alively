"""

"""

import threading
from web import ctx, restful
import logging
import functools
from decorator import decorator
import dbx
import time
import demjson
import hashlib

from models import User

_authorities = {}
_principals = {}

_sessions = {}

SESSION_NAME = 'SPYSESSION'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def secured(role_expr):
    def d(fn):
        @functools.wraps(fn)
        def dd(*args, **kwargs):
            logger.info('make decision for %s access' % fn.__name__)
            make_decision(role_expr)
            return fn(*args, **kwargs)
        return dd
    return d


def make_decision(role_expr):
    required_roles = role_expr.split(',')
    principal = ctx.session.get('user')
    if principal:
        granted_roles = dbx.redis.smembers('user_permits:%s' % principal['username'])
        for r in required_roles:
            if r not in granted_roles:
                raise SecurityException('permission: %s are required' % ','.join(required_roles))
    else:
        raise SecurityException('login required')


class SecurityException(Exception):
    pass


class AuthenticateException(SecurityException):
    pass


base_url = '/api'


def secured_session(nxt):
    """
    an interceptor to secure request,
    better be the first in interceptors chain
    :param nxt:
    :return:
    """
    sessionid = ctx.request.cookie(SESSION_NAME)
    if not sessionid:
        if ctx.session.get('user'):
            del ctx.session['user']
        return demjson.encode({
            'success': False,
            'msg': 'login required'
        })
    else:
        session_key = 'secured_session:%s' % sessionid
        principal = dbx.redis.hgetall(session_key)
        now = int(time.time())
        if not principal:
            if ctx.session.get('user'):
                del ctx.session['user']
            return demjson.encode({
                'success': False,
                'msg': 'session expired, login required'
            })
        principal.update({
            'last_active': now
        })
        ctx.session['user'] = principal
        ctx.session['id'] = sessionid
        last_session_key = 'last_session:%s' % principal['username']
        pipe = dbx.redis.pipeline()
        pipe.multi()
        pipe.hset(session_key, 'last_active', now)
        pipe.expire(session_key, MAX_AGE)
        pipe.expire(last_session_key, MAX_AGE)
        pipe.execute()
        ctx.response.make_cookie(SESSION_NAME, sessionid, expires=MAX_AGE)
    rv = nxt()
    del ctx.session['user']
    return rv


MAX_AGE = int(10*60)


def authenticate(fn):
    """
    a handler to make a controller as an login enter
    should be used only once
    :param fn:
    :return:
    """
    def d(*args, **kwargs):
        username = ctx.request.form['username']
        password = ctx.request.form['password']
        user = dbx.redis.hgetall('user:%s' % username)
        if user:
            po = User(id=username, password=password).digest_passwd()
            if po.password == user['password']:
                last_session_key = 'last_session:%s' % username
                sessionid = dbx.redis.get(last_session_key)
                if not sessionid:
                    sessionid = hashlib.sha1((username + password + str(int(time.time()*1000))).encode()).hexdigest()
                pipe = dbx.redis.pipeline()
                session_key = 'secured_session:%s' % sessionid
                now = int(time.time())
                user.update({
                    'login_time': now,
                    'last_active': now
                })
                pipe.hmset(session_key, user)
                pipe.expire(session_key, MAX_AGE)
                pipe.set(last_session_key, sessionid)
                pipe.expire(last_session_key, MAX_AGE)
                pipe.execute()
                ctx.response.make_cookie(SESSION_NAME, sessionid, expires=MAX_AGE)
                ctx.session['user'] = user
                ctx.session['id'] = sessionid
                return fn(*args, **kwargs)
            ctx.response.del_cookie(SESSION_NAME)
            raise AuthenticateException('password does not match')
        else:
            ctx.response.del_cookie(SESSION_NAME)
            raise AuthenticateException('invalid username')
    return d
