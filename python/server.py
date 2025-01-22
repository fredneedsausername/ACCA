# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

from flask import Flask, render_template, request, redirect, url_for, flash, session
import passwords
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequest
import fredbconn
import fredauth

#TODO metti che il testo delle note se è troppo fa i puntini (su css)

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = passwords.app_secret_key

class Dipendente:

    def __init__(self, nome: str, cognome: str, ditta_id: int, is_badge_already_emesso: int, autorizzato: int):
        self.nome = nome
        self.cognome = cognome
        self.ditta_id = ditta_id
        self.is_badge_already_emesso = is_badge_already_emesso
        self.autorizzato = autorizzato
    

    @classmethod
    def from_form(cls):
        """Transforms the request form into a Dipendente object

        Raises:
            BadRequest: either "nome", "cognome", "ditta_id", "is_badge_already_emesso" based on what field is missing

        Returns:
            Dipendente: an object of type Dipendente
        """
        nome = request.form.get("nome")
        if (nome == None) or (nome == ""): raise BadRequest("nome")

        cognome = request.form.get("cognome")
        if (cognome == None) or (cognome == ""): raise BadRequest("cognome")

        ditta_id = request.form.get("ditta_id")
        if ditta_id is None: raise BadRequest("ditta_id")

        is_badge_already_emesso = request.form.get("is_badge_already_emesso")
        if is_badge_already_emesso is None: is_badge_already_emesso = 0
        if is_badge_already_emesso == "yes": is_badge_already_emesso = 1

        autorizzato = request.form.get("autorizzato")
        if autorizzato is None: autorizzato = 0
        if autorizzato == "yes": autorizzato = 1

        return cls(nome, cognome, ditta_id, is_badge_already_emesso, autorizzato)
    
    
    def get_fields(self):
        return self.nome, self.cognome, self.ditta_id, self.is_badge_already_emesso, self.autorizzato
    
    @fredbconn.connected_to_database
    def add_to_db(cursor, self):
        fields = self.get_fields()
        cursor.execute("""
        INSERT INTO dipendenti(nome, cognome, ditta_id, is_badge_already_emesso, autorizzato)
        VALUES (%s, %s, %s, %s, %s)
        """, (fields[0], fields[1], fields[2], fields[3], fields[4]))


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
    return render_template("dipendenti.html", dipendenti = dipendenti)


@app.route("/aggiungi-dipendenti", methods=["GET", "POST"])
@fredauth.authorized
def aggiungi_dipendenti():

    @fredbconn.connected_to_database
    def fetch_is_admin(cursor):
        cursor.execute("""
        SELECT is_admin
        FROM utenti
        WHERE username = %s
        """, (session["user"],))
        return cursor.fetchone()
    
    # Will never return None because of fredauth.authorized
    if fetch_is_admin()[0] == 0:
        flash("Il suo account non dispone delle autorizzazioni necessarie per aggiungere o modificare dipendenti",
               "autenticazione-fallita")
        return redirect("/dipendenti")
    
    if request.method == "GET":
        return render_template("aggiungi-dipendenti.html")
    
    if request.method == "POST":
        try:
            dipendente = Dipendente.from_form()
        except BadRequest as e:
            flash(f"Non ha inserito il campo {e}")
            return redirect("/aggiungi-dipendenti")
        else:
            dipendente.add_to_db()


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
