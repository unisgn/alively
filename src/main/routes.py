# coding=utf-8
# Created by 0xFranCiS on Jun 08, 2016.

from web import ctx, restful, route
from dbx import redis, Session

from sqlalchemy import text, select, func
from sqlalchemy.sql import select, and_, or_, not_, label, func as sqlfn
from models import *

import uuid
import os
import time

import util

from security import secured, authenticate



@route('/login', method='post')
@restful
@authenticate
def login():
    user = ctx.session['user']
    return user


