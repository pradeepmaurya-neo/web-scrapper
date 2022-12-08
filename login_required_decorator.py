from flask import g, request, redirect, url_for,session


def login_required(f):
    def decorated_function(*args,**kwargs):
        if session.get('user')==None:
            return redirect(url_for('login',next=request.url))
        return f(*args,**kwargs)
    return decorated_function