# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details
from functools import wraps
from flask import session, render_template

def authorized(fn):
    """Decorator to censure authorized access to a server

    Usage:
        Use as decorator to the function to force the authorization in, and the authorization will be forced
    """
    @wraps(fn)
    def ret_func(*args, **kwargs):
        if 'user' in session: return fn(*args, **kwargs)
        else: return render_template("login.html")
    return ret_func