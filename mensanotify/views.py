from __future__ import unicode_literals

from functools import wraps
import random
import string
import urllib
import datetime

from flask import (request, session, render_template, redirect, url_for,
                   flash, jsonify, abort)

from werkzeug.routing import BaseConverter, PathConverter

from wtforms import Form, validators, widgets
from wtforms.fields import (TextField, SubmitField, SelectMultipleField,
                            FieldList)

from mensanotify import app, mensa, users
from mensanotify.mensa import MENSA_NAMES, MENSA_CHARS
from mensanotify.email import send_login, send_delete
import mensanotify.date


def mensasort(value):
    return sorted(value.items(), key=lambda x: MENSA_NAMES.index(x[0]))


app.jinja_env.filters['mensasort'] = mensasort
app.jinja_env.filters['weekday'] = mensanotify.date.to_weekday


c2n = dict(zip(MENSA_CHARS, MENSA_NAMES))
n2c = dict(zip(MENSA_NAMES, MENSA_CHARS))


class MensaListConverter(BaseConverter):
    def to_python(self, value):
        if not value:
            return MENSA_NAMES
        if set(value).difference(MENSA_CHARS):
            abort(404)
        return [c2n[x] for x in value]

    def to_url(self, value):
        return ''.join(n2c[x] for x in value)


class QueryListConverter(PathConverter):
    def to_python(self, value):
        if not value:
            return None
        return [x for x in value.split('/') if x]

    def to_url(self, value):
        v = (urllib.quote(x.encode('utf-8')) for x in value)
        return '/'.join(v)


app.url_map.converters['mensalist'] = MensaListConverter
app.url_map.converters['query'] = QueryListConverter


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class RegisterForm(Form):
    email = TextField('Email', [validators.Email('Invalid email address')])
    submit = SubmitField('Get login link')


class QueryForm(Form):
    queries = FieldList(TextField('Query'))
    mensae = MultiCheckboxField('mens', choices=zip(MENSA_NAMES, MENSA_NAMES))
    submit = SubmitField(label='Update')


def query_form(queries, mensae):
    form = QueryForm()
    if queries is not None:
        for q in queries:
            form.queries.append_entry(q)
    form.queries.append_entry('')
    form.mensae.data = mensae
    return form


def gen_key(N=16):
    keyspace = string.ascii_letters + string.digits
    return ''.join(random.choice(keyspace) for _ in xrange(N))


@app.route('/', methods=['GET', 'POST'])
@app.route('/s/<mensalist:mensae>', methods=['GET', 'POST'])
@app.route('/s/<mensalist:mensae>/<query:query>', methods=['GET', 'POST'])
def search(mensae=MENSA_NAMES, query=None):
    if request.method == 'POST':
        form = QueryForm(request.form)
        q = [x.data for x in form.queries if x.data] or None
        return redirect(url_for('search', mensae=form.mensae.data, query=q))

    results = mensa.search_many(query, mensae)
    form = query_form(query, mensae)

    if not results:
        msg = 'No results'
        if query:
            msg += ' for '
            msg += ', '.join('"{}"'.format(q) for q in query)
        flash(msg, 'warn')
        results = mensa.overview(mensae)

    return render_template('results.html',
                           form=form,
                           form_action=url_for('search'),
                           mensae=mensae,
                           results=results)


@app.route('/json')
@app.route('/json/<mensalist:mensae>')
@app.route('/json/<mensalist:mensae>/<query:query>')
def search_json(mensae=mensa.MENSA_NAMES, query=None):
    results = mensa.search_many(query, mensae)
    return jsonify(**results)


@app.route('/today', methods=['GET', 'POST'])
@app.route('/today/<mensalist:mensae>', methods=['GET', 'POST'])
def today(mensae=MENSA_NAMES):
    return today_tomorrow('today', mensae)


@app.route('/tomorrow', methods=['GET', 'POST'])
@app.route('/tomorrow/<mensalist:mensae>', methods=['GET', 'POST'])
def tomorrow(mensae=MENSA_NAMES):
    return today_tomorrow('tomorrow', mensae)


def today_tomorrow(day, mensae):
    if (request.method == 'POST'):
        form = QueryForm(request.form)
        return redirect(url_for(day, mensae=form.mensae.data))

    date = datetime.date.today()
    if day == 'tomorrow':
        date += datetime.timedelta(days=1)

    results = mensa.overview(mensae, day=mensanotify.date.from_date(date))
    form = QueryForm()
    form.mensae.data = mensae
    return render_template(day + '.html',
                           form=form,
                           form_action=url_for(day),
                           mensae=mensae,
                           results=results)


def login_required(f):
    @wraps(f)
    def fun(*args, **kwargs):
        if 'user' not in session:
            flash("Not logged in", 'error')
            return redirect(url_for('register'))
        return f(*args, **kwargs)
    return fun


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        if email not in users:
            user = users[email]
            user.key = gen_key()
            user.del_key = ''
            user.mensae = MENSA_NAMES
            user.queries = []
        send_login(email, users[email].key)
        flash('Your login link has been sent to your email address')

    return render_template('register.html', form=form)


@app.route('/login/<email>/<key>')
def login(email, key):
    if email not in users or users[email].key != key:
        abort(401)
    session['user'] = email
    return redirect(url_for('edit'))


@app.route('/logout')
@login_required
def logout():
    if session.pop('user', None):
        flash('Goodbye')
    return redirect(request.referrer or url_for('overview'))


@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    user = users[session['user']]
    if request.method == 'GET':
        form = query_form(user.queries, user.mensae)
        results = mensa.search_many(user.queries, user.mensae)
        return render_template('edit.html',
                               user=session['user'],
                               form=form,
                               form_action=url_for('edit'),
                               results=results)
    else:
        form = QueryForm(request.form)
        q = form.queries.entries
        user.queries = [x.data for x in q if x.data]
        user.mensae = form.mensae.data
        return redirect(url_for('edit'))


@app.route('/del')
@login_required
def delete():
    user = users[session['user']]
    user.del_key = gen_key()
    flash('A deletion link was sent to your email address')
    send_delete(session['user'], user.del_key)
    return redirect(request.referrer or url_for('edit'))


@app.route('/del/<email>/<key>')
def confirm_delete(email=None, key=None):
    if email not in users or users[email].del_key != key:
        abort(401)
    session.pop('user')
    del users[email]
    flash('Account deleted')
    return redirect(url_for('register'))
