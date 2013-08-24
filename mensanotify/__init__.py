import os.path
from socket import getfqdn

from flask import Flask

app = Flask(__name__)
app.secret_key = 'key'

app.config.from_object('mensanotify.default_settings')
app.config.from_envvar('MENSA_SETTINGS')

from mensanotify.jsonobj import JsonObjDict
users = JsonObjDict(os.path.join(app.config['DATA_ROOT'], 'users'))

import mensanotify.views
