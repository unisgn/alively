# coding=utf-8
# Created by 0xFranCiS on May 08, 2016.
import datetime
import redis
import dbx
__author__ = '0xFranCiS'

import demjson
import functools


def encode_value(obj):
    try:
        return obj._asdict()
    except AttributeError:
        raise demjson.JSONEncodeError('can not encode object into a JSON representation', obj)


jsonify = functools.partial(demjson.encode, encode_default=encode_value)


def next_project_contract_no():
    return date_seq_next('project_contract', 'HT')


def next_project_no():
    return date_seq_next('project', 'PJ')


def date_seq_next(key_seq, prefix, datefmt='%Y%m%d', digits=4):
    # TODO: use redis lock
    key_seq = 'seq_%s' % key_seq
    key_date = key_seq + '_date'
    cli = dbx.redis
    today = datetime.datetime.today()
    today_date_lock = today.strftime('%Y%m%d')
    date_lock = cli.get(key_date)
    if date_lock != today_date_lock:
        cli.set(key_date, today_date_lock)
        cli.set(key_seq, 0)
    nxt = cli.incr(key_seq)
    fmt = '%%s%%s#%%0%sd' % digits
    return fmt % (prefix, today.strftime(datefmt), int(nxt))


# print(next_project_no())


class ChainDict(dict):

    def update(self, e=None, **kwargs):
        if e:
            super(ChainDict, self).update(e, **kwargs)
        else:
            super(ChainDict, self).update(**kwargs)
        return self
