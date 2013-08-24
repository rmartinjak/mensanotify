from __future__ import unicode_literals

from functools import wraps
import random
import string

from flask import (request, session, render_template, redirect, url_for,
                   flash, jsonify, abort)

from werkzeug.routing import BaseConverter

from wtforms import Form, validators, widgets
from wtforms.fields import (TextField, SubmitField, SelectMultipleField,
                            FieldList)

from mensanotify import app, mensa, users
from mensanotify.mensa import MENSA_NAMES, MENSA_CHARS
from mensanotify.email import send_login, send_delete


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


class QueryListConverter(BaseConverter):
    def to_python(self, value):
        return value.split('/')

    def to_url(self, value):
        return '/'.join(value)


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
    new_query = TextField('Add query')
    mensae = MultiCheckboxField('mens', choices=zip(MENSA_NAMES, MENSA_NAMES))
    submit = SubmitField(label='Update')


def gen_key(N=16):
    keyspace = string.ascii_letters + string.digits
    return ''.join(random.choice(keyspace) for _ in xrange(N))


@app.route('/')
@app.route('/s/<mensalist:mensae>')
@app.route('/s/<mensalist:mensae>/')
def overview(mensae=MENSA_NAMES):
    return search(mensae)


@app.route('/s/<mensalist:mensae>/<query:query>')
def search(mensae, query=None):
    results = mensa.search_many(query, mensae)

    if not results:
        msg = 'No results'
        if query:
            msg += 'for "{}"'.format(query)
        flash(msg, 'warn')
        results = mensa.overview(mensae)

    return render_template('results.html',
                           mensae=mensae,
                           query=query,
                           results=results)


@app.route('/s/<mensalist:mensae>', methods=['POST'])
def search_post(mensae, query=''):
    query = request.form['query']
    return redirect(url_for('search', mensae=mensae, query=[query]))


@app.route('/json')
@app.route('/json/<mensalist:mensae>')
@app.route('/json/<mensalist:mensae>/<query:query>')
def search_json(mensae=mensa.MENSA_NAMES, query=None):
    results = mensa.search_many(query, mensae)
    return jsonify(**results)


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
        form = QueryForm()
        for q in user.queries:
            form.queries.append_entry(q)
        form.mensae.data = user.mensae
        results = mensa.search_many(user.queries, user.mensae)
        return render_template('edit.html',
                               user=session['user'],
                               form=form,
                               results=results)
    else:
        form = QueryForm(request.form)
        q = form.queries.entries + [form.new_query]
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