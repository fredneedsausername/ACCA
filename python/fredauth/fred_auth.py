from functools import wraps
from flask import flash, redirect, session, render_template, request, url_for
import fredbconn

def authorized(auth_type):
    """Decorator to censure authorized access to a server

    Usage:
        Use as decorator to the function to force the authorization in, and the authorization will be forced
    """
    def decorator(fn):
    
        @wraps(fn)
        def ret_func(*args, **kwargs):
            if 'user' in session:

                if(auth_type == "admin"):
                    @fredbconn.connected_to_database
                    def fetch_is_admin(cursor):
                        cursor.execute("""
                        SELECT is_admin
                        FROM utenti
                        WHERE username = %s
                        """, (session["user"],))
                        return cursor.fetchone()
                    
                    # Will never return None because of previous check
                    if fetch_is_admin()[0] == 0:
                        flash("Il suo account non dispone delle autorizzazioni necessarie per questa operazione", "error")
                        return redirect(request.referrer or url_for("/")) 

                if(auth_type == "user"):
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
                        flash("Il suo account è stato rimosso.", "error")
                        return redirect("/login")

                    if result[0] == 0:
                        flash("Il suo account è stato disabilitato.", "error")
                        return redirect("/login")

                return fn(*args, **kwargs)
            else: return render_template("login.html")
        return ret_func
    return decorator