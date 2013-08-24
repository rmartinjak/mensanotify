#!/usr/bin/env python
from flup.server.fcgi import WSGIServer
from mensanotify import app

if __name__ == '__main__':
    WSGIServer(app, bindAddress='/tmp/mensa-fcgi.sock').run()
