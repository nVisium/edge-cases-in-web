from flask import Flask, Response, abort, flash, g, jsonify, render_template, render_template_string, request
from hashlib import sha1
import base64
import cPickle
import hmac
import json

SECRET_KEY = 'notsosecretanymore'

app = Flask(__name__)
app.config.from_object(__name__)

def check_hmac(sig, data, key):
    m = hmac.new(key, json.dumps(data, sort_keys=True))
    return sig == m.hexdigest()

def create_hmac(data, key):
    m = hmac.new(key, json.dumps(data, sort_keys=True))
    return m.hexdigest()

@app.after_request
def session_serializer(response):
    session_object = {'data': g.session, 'signature': create_hmac(g.session, SECRET_KEY)}
    response.set_cookie('session', base64.b64encode(cPickle.dumps(session_object)))
    return response

@app.before_request
def session_deserializer():
    g.session = {'csrf_token': 'thisisacryptographicallystrongrandomtoken'}
    serialized_session = request.cookies.get('session')
    if serialized_session:
        try:
            session_object = cPickle.loads(base64.b64decode(serialized_session))
            if check_hmac(session_object['signature'], session_object['data'], SECRET_KEY):
                g.session = session_object['data']
            else:
                g.error = 'Failed signature validation.'
        except:
            g.error = 'Failed session deserialization.'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/serialization', methods=['GET', 'POST'])
def serialization():
    if request.method == 'POST':
        name = request.form.get('name')
        value = request.form.get('value')
        if all((name, value)):
            g.session[name] = value
    return render_template('serialization.html')

@app.route('/csrf', methods=['GET', 'POST'])
def csrf():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if password == request.form.get('confirm'):
            if request.form.get('csrf_token') == g.session.get('csrf_token'):
                message = 'Update successful.'
            else:
                message = 'Update failed. CSRF detected.'
        else:
            message = 'Update failed. Passwords didn\'t match.'
    return render_template('csrf.html', message=message)

@app.route('/clickjack')
def clickjack():
    return render_template('clickjack.html')

@app.route('/cors-bypass')
def cors_bypass():
    return render_template('cors-bypass.html')

@app.route('/api/users', methods=['POST'])
def create_user():
    if request.cookies.get('session'):
        jsonobj = request.get_json(force=True)
        if not jsonobj:
            abort(400)
        user = {
            'id': 53,
            'username': jsonobj.get('username'),
            'hash': sha1(jsonobj.get('username')+jsonobj.get('password')).hexdigest()
        }
        # store user
        return jsonify({'user': user}), 201
    else:
        abort(401)

@app.route('/ssti', methods=['GET', 'POST'])
def ssti():
    template = '''
<!DOCTYPE html>
<html>
<head>
</head>
<body>
    <h3>Welcome %s!</h3>
    <h3>Enter name:</h3>
    <form action="{{ url_for('ssti') }}" method="post">
        <table>
            <tbody>
                <tr>
                    <td><input type="text" name="name" placeholder="name" /></td>
                    <td><input type="submit" value="Submit" onclick="this.form.submit();" /></td>
                </tr>
            </tbody>
        </table>
    </form>
</body>
</html>
'''
    name = 'Guest'
    if request.method == 'POST':
        name = request.form.get('name')
    return render_template_string(template % name)

if __name__ == '__main__':
    app.debug = True
    app.run()
