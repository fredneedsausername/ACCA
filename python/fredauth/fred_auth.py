# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details
from functools import wraps
from flask import flash, redirect, session, render_template
import fredbconn

def authorized(fn):
    """Decorator to censure authorized access to a server

    Usage:
        Use as decorator to the function to force the authorization in, and the authorization will be forced
    """
    @wraps(fn)
    def ret_func(*args, **kwargs):
        if 'user' in session:

            @fredbconn.connected_to_database
            def fetch_abilitato(cursor):
                cursor.execute("""
                SELECT abilitato
                FROM utenti
                WHERE username = %s
                """, (session["user"],))
                return cursor.fetchone()

            result = fetch_abilitato()

            if result is None:
                flash("Il suo account è stato rimosso.", "autenticazione-fallita")
                return redirect("/login")

            if result[0] == 0:
                flash("Il suo account è stato disabilitato.", "autenticazione-fallita")
                return redirect("/login")

            return fn(*args, **kwargs)
        else: return render_template("login.html")
    return ret_func