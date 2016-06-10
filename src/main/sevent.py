# coding=utf-8
# Created by 0xFranCiS on Jun 04, 2016.
import functools


class Reactor:
    def __init__(self):
        self._events = {}

    def listen(self, event, handler):
        h = self._events.get(event)
        if h:
            h.append(handler)
        else:
            h = [handler]
            self._events[event] = h

    def fire(self, event, *args, **kwargs):
        for h in self._events.get(event):
            h(*args, **kwargs)

reactor = Reactor()


def on(event):
    def d(fn):
        reactor.listen(event, fn)

        def dd(*args, **kwargs):
            return fn(*args, **kwargs)
        return dd
    return d




