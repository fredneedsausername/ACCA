# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

from flask import Flask, render_template, request, redirect, url_for, flash, session
import passwords
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequest
import fredbconn
import fredauth

#TODO aggiungi messaggio di successo quando elimini dipendente, flash non funziona causa js
#TODO fai report
#TODO refactor finale codice
#TODO aggiungi funzionalità per ricercare per ditta
#TODO aggiungi funzionalità per ricercare per cognome
#TODO quando aggiungi un dipendente senza avere una ditta ti dice la ditta selezionata è stata rimossa

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = passwords.app_secret_key

class Dipendente:

    def __init__(self, nome: str, cognome: str, ditta_name: str, is_badge_already_emesso: int, autorizzato: int, note: str):
        self.nome = nome
        self.cognome = cognome
        self.ditta_name = ditta_name
        self.is_badge_already_emesso = is_badge_already_emesso
        self.autorizzato = autorizzato
        self.note = note
    
    @classmethod
    def from_form(cls):
        """Transforms the request form into a Dipendente object

        Raises:
            BadRequest: either "nome", "cognome", "ditta_name" based on what field is missing

        Returns:
            Dipendente: an object of type Dipendente
        """
        nome = request.form.get("nome")

        cognome = request.form.get("cognome")

        ditta_name = request.form.get("ditta")

        is_badge_already_emesso = request.form.get("is_badge_already_emesso")
        if is_badge_already_emesso is None: is_badge_already_emesso = 0
        if is_badge_already_emesso == "yes": is_badge_already_emesso = 1

        autorizzato = request.form.get("autorizzato")
        if autorizzato is None: autorizzato = 0
        if autorizzato == "yes": autorizzato = 1

        note = request.form.get("note")

        return cls(nome, cognome, ditta_name, is_badge_already_emesso, autorizzato, note)
    
    
    def get_fields(self):
        return self.nome, self.cognome, self.ditta_name, self.is_badge_already_emesso, self.autorizzato, self.note
    
    @fredbconn.connected_to_database
    def add_to_db(cursor, self):

        fields = self.get_fields()

        cursor.execute("""
        SELECT id
        FROM ditte
        WHERE nome = %s
        """, (fields[2],))

        ditta_id = cursor.fetchone()

        if ditta_id is None:
            flash("La ditta selezionata è stata rimossa", "error")
            return redirect("/aggiungi-dipendenti")

        cursor.execute("""
        INSERT INTO dipendenti(nome, cognome, ditta_id, is_badge_already_emesso, autorizzato, note)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (fields[0], fields[1], ditta_id, fields[3], fields[4], fields[5]))


class Ditta:

    def get_fields(self): # This function is structured weird to make it not overflow the screen

        ret = []
        ret.append(self.nome)
        ret.append(self.piva)
        ret.append(self.scadenza_autorizzazione)
        ret.append(self.blocca_accesso)
        ret.append(self.nome_cognome_referente)
        ret.append(self.email_referente)
        ret.append(self.telefono_referente)

        ret = tuple(ret)

        return ret

    @fredbconn.connected_to_database
    def add_to_db(cursor, self):

        fields = self.get_fields()

        cursor.execute("""
        INSERT INTO
        ditte(nome, piva, scadenza_autorizzazione, blocca_accesso, nome_cognome_referente, email_referente, telefono_referente)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s)
        """, self.get_fields())
    

    def __init__(self, nome: str, piva: str, scadenza_autorizzazione: str,
                 blocca_accesso: int, nome_cognome_referente: str, email_referente: str, telefono_referente: str):
        self.nome = nome
        self.piva = piva
        self.scadenza_autorizzazione = scadenza_autorizzazione
        self.blocca_accesso = blocca_accesso
        self.nome_cognome_referente = nome_cognome_referente
        self.email_referente = email_referente
        self.telefono_referente = telefono_referente
    

    @classmethod
    def from_form(cls):

        nome = request.form.get("nome")
        if not nome:
            nome = "No"

        piva = request.form.get("piva", "")
        if not piva:
            piva = "No"
        
        scadenza_autorizzazione = request.form.get("scadenza_autorizzazione", "")
        if not scadenza_autorizzazione:
            scadenza_autorizzazione = "No"

        blocca_accesso = request.form.get("blocca_accesso")
        if blocca_accesso is None: blocca_accesso = 0
        if blocca_accesso == "yes": blocca_accesso = 1

        scadenza_autorizzazione = request.form.get("scadenza_autorizzazione", "")
        if not scadenza_autorizzazione:
            scadenza_autorizzazione = "No"
        
        nome_cognome_referente = request.form.get("nome_cognome_referente", "")
        if not nome_cognome_referente:
            nome_cognome_referente = "No"
        
        email_referente = request.form.get("email_referente", "")
        if not email_referente:
            email_referente = "No"
        
        telefono_referente = request.form.get("telefono_referente", "")
        if not telefono_referente:
            telefono_referente = "No"

        return cls(nome, piva, scadenza_autorizzazione, blocca_accesso, nome_cognome_referente, email_referente, telefono_referente)
    

@app.route('/aggiorna-dipendente', methods=['GET', 'POST'])
@fredauth.authorized("admin")
def aggiorna_dipendente():

    if request.method == "GET":
        # Extract the ID from the query parameters
        dipendente_id = request.args.get('id')

        @fredbconn.connected_to_database
        def fetch_info(cursor):
            cursor.execute("""
                SELECT 
                    nome,
                    cognome,
                    ditta_id,
                    is_badge_already_emesso,
                    autorizzato,
                    note
                FROM 
                    dipendenti
                WHERE 
                    id = %s;
            """, (dipendente_id,))
            
            dipendente_tuple = cursor.fetchone()

            if dipendente_tuple is None:
                return None

            ret = {
                "nome": dipendente_tuple[0],
                "cognome": dipendente_tuple[1],
                "selected_ditta": dipendente_tuple[2],
                "is_badge_already_emesso": dipendente_tuple[3],
                "autorizzato": dipendente_tuple[4],
                "note": dipendente_tuple[5]
            }

            cursor.execute("""
                SELECT nome
                FROM ditte;
            """)
            
            ditte_names_tuple = cursor.fetchall()

            # Flatten the tuple of tuples into a single tuple of names
            ditte_names = tuple(name[0] for name in ditte_names_tuple)

            # Add the ditte entry to the dictionary
            ret["ditte"] = ditte_names

            return ret
        
        fetched = fetch_info()

        if fetched is None: return redirect("/dipendenti")

        fetched["dipendente_id"] = dipendente_id

        return render_template("aggiorna-dipendente.html", **fetched)

    if request.method == "POST":
        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        ditta = request.form.get('ditta')
        is_badge_already_emesso = (1 if (request.form.get('is_badge_already_emesso') == 'yes') else 0)
        autorizzato = (1 if (request.form.get('autorizzato') == 'yes') else 0)
        note = request.form.get('note')
        dipendente_id = request.form.get("dipendente_id")

        @fredbconn.connected_to_database
        def fetch_info(cursor):
            cursor.execute("""
            SELECT id
            FROM ditte
            WHERE nome = %s
            """, (ditta,))
            
            return cursor.fetchone()
        
        fetched = fetch_info()

        if fetched is None: return redirect("/dipendenti")

        ditta_id = fetched[0]

        @fredbconn.connected_to_database
        def update_db(cursor):
            cursor.execute("""
            UPDATE dipendenti
            SET nome = %s,
                cognome = %s,
                ditta_id = %s,
                is_badge_already_emesso = %s,
                autorizzato = %s,
                note = %s
                
            WHERE id = %s
            """, (nome, cognome, ditta_id, is_badge_already_emesso, autorizzato, note, dipendente_id))

        update_db()

        flash("Dipendente aggiornato con successo", "success")
        return redirect("/dipendenti")

@app.route('/elimina-dipendente', methods=['POST'])
@fredauth.authorized("admin")
def elimina_dipendente():
    dipendente_id = request.form.get('id')

    @fredbconn.connected_to_database
    def eliminate_dipendente(cursor):
        cursor.execute("""
        DELETE
        FROM dipendenti
        WHERE id = %s
        """, (dipendente_id,))
    
    eliminate_dipendente()

    flash("Dipendente eliminato con successo", "success")
    return redirect("/dipendenti")

@app.route("/")
@fredauth.authorized("user")
def index():
    return render_template("index.html", username = session['user']) # username = session['user'] usato in jinja


@app.route("/ditte")
@fredauth.authorized("user")
def ditte():

    @fredbconn.connected_to_database
    def fetch_ditte_info(cursor):
        cursor.execute("""
        SELECT id, nome, piva, scadenza_autorizzazione, blocca_accesso, nome_cognome_referente, email_referente, telefono_referente
        FROM ditte
        """)

        fetched = cursor.fetchall()

        return fetched

    fetched = fetch_ditte_info()

    return render_template("ditte.html", ditte = fetched)


@app.route("/aggiorna-ditta", methods = ["GET", "POST"])
@fredauth.authorized("admin")
def aggiorna_ditta():
    if request.method == "GET":
        # Extract the ID from the query parameters
        ditta_id = request.args.get('id')

        @fredbconn.connected_to_database
        def fetch_info(cursor):
            cursor.execute("""
                SELECT 
                    nome,
                    piva,
                    scadenza_autorizzazione,
                    blocca_accesso,
                    nome_cognome_referente,
                    email_referente,
                    telefono_referente
                FROM
                    ditte
                WHERE 
                    id = %s;
            """, (ditta_id,))
            
            ditta_tuple = cursor.fetchone()

            if ditta_tuple is None:
                return None

            ret = {
                "nome": ditta_tuple[0],
                "piva": ditta_tuple[1],
                "scadenza_autorizzazione": ditta_tuple[2],
                "blocca_accesso": ditta_tuple[3],
                "nome_cognome_referente": ditta_tuple[4],
                "email_referente": ditta_tuple[5],
                "telefono_referente": ditta_tuple[6]
            }

            return ret
        
        fetched = fetch_info()

        if fetched is None: return redirect("/ditte")

        fetched["ditta_id"] = ditta_id

        return render_template("aggiorna-ditta.html", **fetched)

    if request.method == "POST":


        nome = request.form.get("nome")
        piva = request.form.get("piva")
        scadenza_autorizzazione = request.form.get("scadenza_autorizzazione")
        blocca_accesso = (1 if (request.form.get('blocca_accesso') == 'yes') else 0)
        nome_cognome_referente = request.form.get("nome_cognome_referente")
        email_referente = request.form.get("email_referente")
        telefono_referente = request.form.get("telefono_referente")
        ditta_id = request.form.get("ditta_id")

        @fredbconn.connected_to_database
        def update_db(cursor):
            cursor.execute("""
            UPDATE ditte
            SET nome = %s,
                piva = %s,
                scadenza_autorizzazione = %s,
                blocca_accesso = %s,
                nome_cognome_referente = %s,
                email_referente = %s,
                telefono_referente = %s
                
            WHERE id = %s
            """, (nome, piva, scadenza_autorizzazione, blocca_accesso,
                  nome_cognome_referente, email_referente, telefono_referente, ditta_id))

        update_db()

        flash("Ditta aggiornata con successo", "success")
        return redirect("/ditte")


@app.route("/aggiungi-ditte", methods=["GET", "POST"])
@fredauth.authorized("admin")
def aggiungi_ditte():

    if request.method == "GET":
        return render_template("aggiungi-ditte.html")
    
    if request.method == "POST":
        ditta = Ditta.from_form()

        ditta.add_to_db()
        flash("Ditta aggiunta con successo", "success")
        return redirect("/aggiungi-ditte")


@app.route("/elimina-ditta", methods=["POST"])
@fredauth.authorized("admin")
def elimina_ditta():
    
    ditta_id = request.form.get("id")

    @fredbconn.connected_to_database
    def eliminate_ditta(cursor):
        cursor.execute("""
        DELETE
        FROM ditte
        WHERE id = %s
        """, (ditta_id,))
    
    eliminate_ditta()

    flash("Ditta eliminata con successo", "success")
    return redirect("/ditte")


@app.route("/dipendenti", methods=["GET", "POST"])
@fredauth.authorized("user")
def show_dipendenti():

    if request.method == "GET":

        id_ditta = request.args.get("id_ditta")

        fetch_dipendenti_data = None

        if id_ditta is not None:
            @fredbconn.connected_to_database
            def func(cursor):
                cursor.execute("""
                SELECT 
                    ditte.nome AS nome_ditta,
                    dipendenti.nome AS nome_dipendente, 
                    dipendenti.cognome,  
                    dipendenti.is_badge_already_emesso, 
                    dipendenti.autorizzato,
                    dipendenti.note,
                    dipendenti.id
                FROM 
                    dipendenti
                JOIN 
                    ditte
                ON 
                    dipendenti.ditta_id = ditte.id
                WHERE
                    ditte.id = %s
                """, (id_ditta,))

                return cursor.fetchall()
            
            fetch_dipendenti_data = func

        else:
            @fredbconn.connected_to_database
            def func(cursor):
                cursor.execute("""
                SELECT 
                    ditte.nome AS nome_ditta,
                    dipendenti.nome AS nome_dipendente, 
                    dipendenti.cognome,  
                    dipendenti.is_badge_already_emesso, 
                    dipendenti.autorizzato,
                    dipendenti.note,
                    dipendenti.id
                FROM 
                    dipendenti
                JOIN 
                    ditte
                ON 
                    dipendenti.ditta_id = ditte.id
                """)

                return cursor.fetchall()
            
            fetch_dipendenti_data = func

        fetched = fetch_dipendenti_data()

        @fredbconn.connected_to_database
        def fetch_ditte_names(cursor):
            cursor.execute("""
            SELECT id, nome
            FROM ditte
            """)

            return cursor.fetchall()
        
        ditte = fetch_ditte_names()

        return render_template("dipendenti.html", dipendenti = fetched, ditte = ditte)
    
    if request.method == "POST":
        telefono_referente = request.form.get("telefono_referente")
        


@app.route("/aggiungi-dipendenti", methods=["GET", "POST"])
@fredauth.authorized("admin")
def aggiungi_dipendenti():
    
    if request.method == "GET":

        @fredbconn.connected_to_database
        def fetch_ditte(cursor):
            cursor.execute("""
            SELECT nome
            FROM ditte
            """)

            fetched = cursor.fetchall()

            ret = []

            for row in fetched:
                ret.append(row[0])
            
            return ret
        
        ditte = fetch_ditte()

        return render_template("aggiungi-dipendenti.html", ditte = ditte)
    #TODO testa ognuno di questi messaggi di errore
    if request.method == "POST":
        try:
            dipendente = Dipendente.from_form()
        except BadRequest as e:
            match str(e):
                case "nome":
                    field_error = "nome dipendente"
                case "cognome":
                    field_error = "cognome dipendente"
                case "ditta_name":
                    field_error = "nome ditta"

            flash(f"Non ha inserito il campo {field_error}", "error")
            return redirect("/aggiungi-dipendenti")
        else:
            dipendente.add_to_db()
            flash("Dipendente aggiunto con successo", "success")
            return redirect("/aggiungi-dipendenti")


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
            flash("L'utente non è registrato", "error")
            return redirect("/login")
        
        if not password == fetched[0]:
            flash("La password è sbagliata", "error")
            return redirect("/login")

        if not fetched[1] == 1:
            flash("Il suo account è stato disabilitato.", "error")
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
