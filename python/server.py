# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

from flask import Flask, render_template, request, redirect, url_for, flash, session
import passwords
from werkzeug.security import generate_password_hash, check_password_hash
import fredbconn

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = passwords.app_secret_key

@app.route("/")
def index():
    if 'user' in session:
        return render_template("index.html", username = session['user']) # username = session['user'] usato in jinja
    return render_template("login.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        #TODO cambia con la struttura vera del db
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


@app.route("/") 
def dashboard():
    if "user" in session:
        return render_template("dashboard.html", username=session["user"])
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    fredbconn.initialize_database(*passwords.database_config)
    app.run(host="127.0.0.1", port="5000", debug=True)
