# coding=utf-8

__author__ = 'yinlan'


from web import WSGI, intercept

import routes


from dbx import engine, lazy_session
from models import Base
from security import secured_session

# Base.metadata.create_all(engine)


"""
pay attention to the order of interceptors
sometimes, order matters
if 3 interceptor configured as follow order:

intercept(i1, path)
intercept(i2, path)
intercept(i3, path)

then the execution would be:

i1(i2(i3(handler)))

"""

intercept(lazy_session, '/api/')
intercept(secured_session, '/api/')


wsgi = WSGI(debug=True)

app = None

if __name__ == '__main__':
    wsgi.run('0.0.0.0')
else:
    app = wsgi.get_wsgi()
