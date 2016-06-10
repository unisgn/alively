# coding=utf-8
# Created by 0xFranCiS on May 13, 2016.

from models import *
from dbx import open_session, engine

import demjson

import functools

import tempfile

import datetime
import dateutil
import time

import calendar



project = Project.__table__
print(type(project))