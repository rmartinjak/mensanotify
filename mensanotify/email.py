from __future__ import absolute_import, unicode_literals

import smtplib
from email.mime.text import MIMEText
from email import Charset
Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')

from flask import url_for, request

from mensanotify import app


def send(recipient, message, subject):
    msg = MIMEText(message.encode('utf-8'), 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = app.config['FROM_ADDR']
    msg['To'] = recipient
    msg['Content-Type'] = "text/plain; charset=utf-8"
    msg['Content-Transfer-Encoding'] = "quoted-printable"
    s = smtplib.SMTP(app.config['SMTP_HOST'])
    if app.config['SMTP_USER'] and app.config['SMTP_PASS']:
        s.login(app.config['SMTP_USER'], app.config['SMTP_PASS'])
    s.sendmail(app.config['FROM_ADDR'], [recipient], msg.as_string())
    s.quit()


def send_login(email, key):
    url = url_for('login', email=email, key=key)
    txt = '{}{}\n'.format(request.url_root[:-1], url)
    subj = 'Login link for {}'.format(request.url_root)
    send(email, txt, subj)


def send_delete(email, key):
    url = url_for('confirm_delete', email=email, key=key)
    txt = '{}{}\n'.format(request.url_root[:-1], url)
    subj = 'Deletion link for {}'.format(request.url_root)
    send(email, txt, subj)


def sorted_dict(d, cmp=None, key=None, reverse=False):
    for k in sorted(d.keys(), cmp, key, reverse):
        yield k, d[k]


def send_results(email, results):
    lines = ['Hello {}, here are your results:'.format(email), '']
    for mensa, weeks in sorted_dict(results):
        lines.append(mensa + ':')
        for day, menu in sorted_dict(weeks):
            lines.append('  ' + day)
            for item in menu:
                lines.append('{}{} ({})'.format('  ' * 2,
                                                item['name'],
                                                item['desc']))
    txt = '\n'.join(lines)
    subj = 'Mensa!'
    send(email, txt, subj)
