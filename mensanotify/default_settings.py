from os.path import expanduser
from socket import getfqdn

FROM_ADDR = 'noreply@' + getfqdn()
SMTP_HOST = 'localhost'
SMTP_USER = None
SMTP_PASS = None
DATA_ROOT = expanduser('~')
