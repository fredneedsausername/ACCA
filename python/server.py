# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

from flask import Flask, render_template, request, redirect, url_for, flash, session
import passwords
from werkzeug.security import generate_password_hash, check_password_hash
import fredbconn
import fredauth

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = passwords.app_secret_key

@app.route("/")
@fredauth.authorized
def index():
    return render_template("index.html", username = session['user']) # username = session['user'] usato in jinja


@app.route("/ditte")
@fredauth.authorized
def ditte():
    return render_template("ditte.html")


@app.route("/dipendenti")
@fredauth.authorized
def dipendenti():
    
    

    @fredbconn.connected_to_database
    def fetch_is_admin(cursor):
        cursor.execute("""
        SELECT is_admin
        FROM utenti
        WHERE username = %s
        """, (session['user'],))
        return cursor.fetchone()

    result = fetch_is_admin()

    # Have to repeat the process of result validation in case the account was removed in between the "authorized" check and this db query
    if result is None: 
        flash("Il suo account è stato rimosso.", "autenticazione-fallita")
        return redirect("/login")

    return render_template("dipendenti.html", dipendenti = dipendenti)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        @fredbconn.connected_to_database
        def fetch_info(cursor):
            cursor.execute("SELECT password, abilitato FROM utenti WHERE username = %s", (username,))
            return cursor.fetchone()
        
        fetched = fetch_info()

        if not fetched:
            flash("L'utente non è registrato", "autenticazione-fallita")
            return redirect("/login")
        
        if not password == fetched[0]:
            flash("La password è sbagliata", "autenticazione-fallita")
            return redirect("/login")

        if not fetched[1] == 1:
            flash("Il suo account è stato disabilitato.", "autenticazione-fallita")
            return redirect("/login")

        session["user"] = username
        return redirect("/")
        
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    fredbconn.initialize_database(*passwords.database_config)
    app.run(host="127.0.0.1", port="5000", debug=True)
