# -*- coding: utf-8 -*-
import re
import pytest

from sanic import Sanic, response
from wtforms.validators import DataRequired, Length
from wtforms import StringField, SubmitField

from sanic_wtf import SanicWTF, to_bytes


# NOTE
# taking shortcut here, assuming there will be only one "string" (the token)
# ever longer than 40.
csrf_token_pattern = '''value="([0-9a-f#]{40,})"'''


def render_form(form):
    return """
    <form action="" method="POST">
    {}
    </form>""".format(''.join(str(field) for field in form))


def test_form_validation():
    app = Sanic('test')
    wtf = SanicWTF(app)

    app.config['WTF_CSRF_ENABLED'] = False

    class TestForm(wtf.Form):
        msg = StringField('Note', validators=[DataRequired(), Length(max=10)])
        submit = SubmitField('Submit')

    @app.route('/', methods=['GET', 'POST'])
    async def index(request):
        form = TestForm(request.form)
        if request.method == 'POST' and form.validate():
            return response.text('validated')
        content = render_form(form)
        return response.html(content)

    req, resp = app.test_client.get('/')
    assert resp.status == 200
    # we disabled it
    assert 'csrf_token' not in resp.text

    # this is longer than 10
    payload = {'msg': 'love is beautiful'}
    req, resp = app.test_client.post('/', data=payload)
    assert resp.status == 200
    assert 'validated' not in resp.text

    payload = {'msg': 'happy'}
    req, resp = app.test_client.post('/', data=payload)
    assert resp.status == 200
    assert 'validated' in resp.text


def test_form_csrf_validation():
    app = Sanic('test')
    wtf = SanicWTF(app)

    app.config['WTF_CSRF_SECRET_KEY'] = 'top secret !!!'

    # setup mock up session for testing
    session = {}
    wtf.get_csrf_context = lambda _: session

    class TestForm(wtf.Form):
        msg = StringField('Note', validators=[DataRequired(), Length(max=10)])
        submit = SubmitField('Submit')

    @app.route('/', methods=['GET', 'POST'])
    async def index(request):
        form = TestForm(request.form)
        if request.method == 'POST' and form.validate():
            return response.text('validated')
        content = render_form(form)
        return response.html(content)

    req, resp = app.test_client.get('/')
    assert resp.status == 200
    assert 'csrf_token' in resp.text
    token = re.findall(csrf_token_pattern, resp.text)[0]
    assert token

    payload = {'msg': 'happy', 'csrf_token': token}
    req, resp = app.test_client.post('/', data=payload)
    assert resp.status == 200
    assert 'validated' in resp.text

    payload = {'msg': 'happy'}
    req, resp = app.test_client.post('/', data=payload)
    assert resp.status == 200
    # should fail, no CSRF token in payload
    assert 'validated' not in resp.text


def test_uninitialized_form():
    wtf = SanicWTF()

    class Form(wtf.Form):
        pass

    with pytest.raises(NotImplementedError):
        Form()


def test_forbid_init_app_more_than_once():
    app = Sanic('test')
    wtf = SanicWTF(app)

    with pytest.raises(RuntimeError):
        wtf.init_app(app)

    app = Sanic('test')
    wtf = SanicWTF()

    wtf.init_app(app)

    with pytest.raises(RuntimeError):
        wtf.init_app(app)


def test_property_hidden_tag():
    app = Sanic('test')
    wtf = SanicWTF(app)

    app.config['WTF_CSRF_SECRET_KEY'] = 'top secret !!!'
    app.config['WTF_CSRF_FIELD_NAME'] = 'csrf_token'

    # setup mock up session for testing
    session = {}
    wtf.get_csrf_context = lambda _: session

    class TestForm(wtf.Form):
        msg = StringField('Note', validators=[DataRequired(), Length(max=10)])
        submit = SubmitField('Submit')

    @app.route('/', methods=['GET', 'POST'])
    async def index(request):
        form = TestForm(request.form)
        assert form.hidden_tag == form.csrf_token
        return response.text("")

    # trigger the assert statement.
    req, resp = app.test_client.get('/')
    assert resp.status == 200


def test_to_bytes():
    assert isinstance(to_bytes(bytes()), bytes)
    assert isinstance(to_bytes(str()), bytes)
