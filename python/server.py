from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session, send_file
import passwords
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequest
import fredbconn
import fredauth
from waitress import serve
import xlsxwriter
import io
from datetime import datetime, date
import os
import sys
import logging
import traceback
import report_generator_completo
import oauth_routes

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = passwords.app_secret_key

class NoDittaSelectedException(Exception):
    """Exception raised when no ditta (entity) is selected."""
    pass


class Dipendente:
    def __init__(self, nome: str, cognome: str, ditta_name: str, is_badge_already_emesso: int, 
             accesso_bloccato: int, note: str, scadenza_autorizzazione: date, badge_sospeso: int, 
             badge_annullato: int, is_badge_temporaneo: int = None, numero_badge: str = "", ruolo_id: int = None):
        
        self.nome = nome
        self.cognome = cognome
        self.ditta_name = ditta_name
        self.is_badge_already_emesso = is_badge_already_emesso
        self.accesso_bloccato = accesso_bloccato
        self.note = note
        self.scadenza_autorizzazione = scadenza_autorizzazione
        self.badge_sospeso = badge_sospeso
        self.badge_annullato = badge_annullato
        self.is_badge_temporaneo = is_badge_temporaneo
        self.numero_badge = numero_badge
        self.ruolo_id = ruolo_id
        
    @classmethod
    def from_form(cls):
        """Transforms the request form into a Dipendente object"""

        ditta_name = request.form.get("ditta")
        if ditta_name == '':
            raise NoDittaSelectedException

        nome = request.form.get("nome")
        cognome = request.form.get("cognome")

        is_badge_already_emesso = 0
        accesso_bloccato = 0
        badge_sospeso = 0
        badge_annullato = 0
        
        # Get badge_temporaneo field and numero_badge
        is_badge_temporaneo = 1 if request.form.get("is_badge_temporaneo") == "on" else 0
        numero_badge = request.form.get("numero_badge", "")
        
        # Get role_id (could be None for regular worker)
        ruolo_id = request.form.get("ruolo_id")
        if ruolo_id == "":
            ruolo_id = None
        elif ruolo_id is not None:
            ruolo_id = int(ruolo_id)
        
        # If is_badge_temporaneo is False, ensure numero_badge is empty
        if not is_badge_temporaneo:
            numero_badge = ""

        note = request.form.get("note")
        scadenza_autorizzazione = request.form.get("scadenza-autorizzazione")
        
        if scadenza_autorizzazione:
            scadenza_autorizzazione = datetime.strptime(scadenza_autorizzazione, "%Y-%m-%d").date()

        return cls(nome, cognome, ditta_name, is_badge_already_emesso, accesso_bloccato, note, 
                  scadenza_autorizzazione, badge_sospeso, badge_annullato, is_badge_temporaneo, numero_badge, ruolo_id)
    
    def get_fields(self):
        return (self.nome, self.cognome, self.ditta_name, self.is_badge_already_emesso, 
                self.accesso_bloccato, self.note, self.scadenza_autorizzazione, 
                self.badge_sospeso, self.badge_annullato, self.is_badge_temporaneo, self.numero_badge, self.ruolo_id)

    @fredbconn.connected_to_database
    def add_to_db(cursor, self):
        fields = self.get_fields()

        # This to fix bug: no "" allowed in sql syntax
        scadenza_autorizzazione = fields[6] or None

        cursor.execute("""
        SELECT id
        FROM ditte
        WHERE nome = %s
        """, (fields[2],))

        ditta_id = cursor.fetchone()

        if ditta_id is None:
            flash("La ditta selezionata è stata rimossa", "error")
            return redirect("/aggiungi-dipendenti")

        ditta_id = ditta_id[0]

        cursor.execute("""
        INSERT INTO dipendenti(nome, cognome, ditta_id, is_badge_already_emesso, accesso_bloccato, 
                            note, scadenza_autorizzazione, badge_sospeso, badge_annullato,
                            is_badge_temporaneo, numero_badge, ruolo_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (fields[0], fields[1], ditta_id, fields[3], fields[4], fields[5], 
              scadenza_autorizzazione, fields[7], fields[8], fields[9], fields[10], fields[11]))


class Ditta:

    def get_fields(self): # This function is structured weird to make it not overflow the screen
        ret = []
        ret.append(self.nome)
        ret.append(self.piva)
        ret.append(self.nome_cognome_referente)
        ret.append(self.email_referente)
        ret.append(self.telefono_referente)
        ret.append(self.note)

        ret = tuple(ret)

        return ret

    @fredbconn.connected_to_database
    def add_to_db(cursor, self):
        fields = self.get_fields()

        cursor.execute("""
        INSERT INTO
        ditte(nome, piva, nome_cognome_referente, email_referente, telefono_referente, note)
        VALUES
        (%s, %s, %s, %s, %s, %s)
        """, self.get_fields())
    

    def __init__(self, nome: str, piva: str, nome_cognome_referente: str,
                 email_referente: str, telefono_referente: str, note: str):
        self.nome = nome
        self.piva = piva
        self.nome_cognome_referente = nome_cognome_referente
        self.email_referente = email_referente
        self.telefono_referente = telefono_referente
        self.note = note
    

    @classmethod
    def from_form(cls):
        nome = request.form.get("nome")
        if not nome:
            nome = ""

        piva = request.form.get("piva", "")
        if not piva:
            piva = ""

        nome_cognome_referente = request.form.get("nome_cognome_referente", "")
        if not nome_cognome_referente:
            nome_cognome_referente = ""
        
        email_referente = request.form.get("email_referente", "")
        if not email_referente:
            email_referente = ""
        
        telefono_referente = request.form.get("telefono_referente", "")
        if not telefono_referente:
            telefono_referente = ""
            
        note = request.form.get("note", "")
        if not note:
            note = ""

        return cls(nome, piva, nome_cognome_referente, email_referente, telefono_referente, note)


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
                    accesso_bloccato,
                    note,
                    scadenza_autorizzazione,
                    badge_sospeso,
                    badge_annullato,
                    is_badge_temporaneo,
                    numero_badge,
                    ruolo_id
                FROM 
                    dipendenti
                WHERE 
                    id = %s
            """, (dipendente_id,))
            
            dipendente_tuple = cursor.fetchone()

            if dipendente_tuple is None:
                return None

            ret = {
                "nome": dipendente_tuple[0],
                "cognome": dipendente_tuple[1],
                "selected_ditta": dipendente_tuple[2],
                "is_badge_already_emesso": dipendente_tuple[3],
                "accesso_bloccato": dipendente_tuple[4],
                "note": dipendente_tuple[5],
                "scadenza_autorizzazione": dipendente_tuple[6],
                "badge_sospeso": dipendente_tuple[7],
                "badge_annullato": dipendente_tuple[8],
                "is_badge_temporaneo": dipendente_tuple[9] if dipendente_tuple[9] is not None else 0,
                "numero_badge": dipendente_tuple[10] if dipendente_tuple[10] is not None else "",
                "ruolo_id": dipendente_tuple[11]
            }

            cursor.execute("""
                SELECT id, nome
                FROM ditte
                ORDER BY nome ASC
            """)
            
            ditte_tuple = cursor.fetchall()

            # Flatten the tuple of tuples into a single tuple of names
            ditte = tuple(ditta for ditta in ditte_tuple)

            # Add the ditte entry to the dictionary
            ret["ditte"] = ditte

            # Get all roles
            cursor.execute("""
                SELECT id, nome_ruolo
                FROM ruoli
                ORDER BY id ASC
            """)
            
            ret["ruoli"] = cursor.fetchall()

            return ret
        
        fetched = fetch_info()

        if fetched is None:
            if dipendente_id:
                return redirect("/dipendenti?id=" + dipendente_id)
            else:
                return redirect("/dipendenti")

        fetched["dipendente_id"] = dipendente_id

        @fredbconn.connected_to_database
        def fetch_selected_ditta_name(cursor):
            cursor.execute("""
            SELECT
                ditte.nome
            FROM
                ditte
            WHERE
                ditte.id = %s
            """, (fetched["selected_ditta"],))

            return cursor.fetchone()

        fetched_selected_ditta_name = fetch_selected_ditta_name()

        fetched["selected_ditta_name"] = fetched_selected_ditta_name[0]

        is_there_already_a_date = int(bool(fetched.get("scadenza_autorizzazione")))

        return render_template("aggiorna-dipendente.html", **fetched, is_there_already_a_date = is_there_already_a_date)

    if request.method == "POST":
        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        ditta = request.form.get('ditta')
        note = request.form.get('note')
        dipendente_id = request.form.get("dipendente_id")
        
        # Get role_id
        ruolo_id = request.form.get("ruolo_id", "")
        if ruolo_id == "":
            ruolo_id = None
        else:
            ruolo_id = int(ruolo_id)
        
        # Get existing values for the fields we're no longer updating through the form
        @fredbconn.connected_to_database
        def get_existing_values(cursor):
            cursor.execute("""
            SELECT is_badge_already_emesso, accesso_bloccato, badge_sospeso, badge_annullato
            FROM dipendenti
            WHERE id = %s
            """, (dipendente_id,))
            return cursor.fetchone()
        
        existing_values = get_existing_values()
        
        # Check if employee still exists
        if existing_values is None:
            flash("Il dipendente che stavi modificando è stato eliminato", "error")
            return redirect("/dipendenti")
        
        # Now safely access the values
        is_badge_already_emesso = existing_values[0] 
        accesso_bloccato = existing_values[1]
        badge_sospeso = existing_values[2]
        badge_annullato = existing_values[3]

        # Get badge_temporaneo field and numero_badge
        is_badge_temporaneo = 1 if request.form.get("is_badge_temporaneo") == "on" else 0
        numero_badge = request.form.get("numero_badge", "")
        
        # If is_badge_temporaneo is False, ensure numero_badge is empty
        if not is_badge_temporaneo:
            numero_badge = ""

        # Initialize scadenza_autorizzazione as None (will be NULL in database)
        scadenza_autorizzazione = None
            
        # Check if clear_date_flag is set to 1
        clear_date_flag = request.form.get("clear_date_flag") == "1"
            
        # Only process the date if we're not clearing it
        if not clear_date_flag:
            date_value = request.form.get("scadenza-autorizzazione")
            if date_value:
                scadenza_autorizzazione = datetime.strptime(date_value, "%Y-%m-%d").date()
            
        # If badge_temporaneo is True, ensure a valid expiration date exists
        if is_badge_temporaneo and not scadenza_autorizzazione:
            flash("È necessario specificare una data di scadenza per i badge temporanei", "error")
            return redirect(f"/aggiorna-dipendente?id={dipendente_id}")

        @fredbconn.connected_to_database
        def update_db(cursor):
            cursor.execute("""
            UPDATE dipendenti
            SET nome = %s,
                cognome = %s,
                ditta_id = %s,
                is_badge_already_emesso = %s,
                accesso_bloccato = %s,
                note = %s,
                scadenza_autorizzazione = %s,
                badge_sospeso = %s,
                badge_annullato = %s,
                is_badge_temporaneo = %s,
                numero_badge = %s,
                ruolo_id = %s
            WHERE id = %s
            """, (nome, cognome, ditta, is_badge_already_emesso, accesso_bloccato, 
                 note, scadenza_autorizzazione, badge_sospeso, badge_annullato, 
                 is_badge_temporaneo, numero_badge, ruolo_id, dipendente_id))

        update_db()

        flash("Dipendente aggiornato con successo", "success")
        return redirect("/dipendenti")


@app.route('/elimina-dipendente', methods=['POST'])
@fredauth.authorized("admin")
def elimina_dipendente():

    if session["user"] == passwords.no_permessi_eliminare or session["user"] == "Pippo2":
        flash("Non hai i permessi per eliminare dipendenti", "error")
        return redirect(request.referrer or "/dipendenti")

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
    return redirect(request.referrer or "/dipendenti")


@app.route("/")
@fredauth.authorized("user")
def index():
    return render_template("index.html", username = session['user']) # username = session['user'] usato in jinja


@app.route("/ditte")
@fredauth.authorized("user")
def ditte():

    nome = request.args.get("nome")

    fetch_ditte_info = None

    if nome is not None:
        @fredbconn.connected_to_database
        def func(cursor):
            cursor.execute("""
            SELECT
                id, nome, piva, nome_cognome_referente, email_referente, telefono_referente, note, is_ditta_individuale
            FROM
                ditte
            WHERE
                INSTR(LOWER(ditte.nome), LOWER(%s)) > 0 
            ORDER BY
                nome ASC
            """, (nome,))

            fetched = cursor.fetchall()

            return fetched

        fetch_ditte_info = func

    else:

        @fredbconn.connected_to_database
        def func(cursor):
            cursor.execute("""
            SELECT
                id, nome, piva, nome_cognome_referente, email_referente, telefono_referente, note, is_ditta_individuale
            FROM
                ditte
            ORDER BY
                nome ASC
            """)

            fetched = cursor.fetchall()

            return fetched
        
        fetch_ditte_info = func


    @fredbconn.connected_to_database
    def fetch_ditte_names(cursor):
        cursor.execute("""
        SELECT
            ditte.nome
        FROM
            ditte
        ORDER BY
            nome ASC
        """)

        fetched = cursor.fetchall()

        return fetched

    fetched_ditte_info = None 

    fetched_ditte_info = fetch_ditte_info()
    
    ditte_names = fetch_ditte_names()

    return render_template("ditte.html", ditte = fetched_ditte_info, ditte_names = ditte_names)


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
                    nome_cognome_referente,
                    email_referente,
                    telefono_referente,
                    note
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
                "nome_cognome_referente": ditta_tuple[2],
                "email_referente": ditta_tuple[3],
                "telefono_referente": ditta_tuple[4],
                "note": ditta_tuple[5]
            }

            return ret
        
        fetched = fetch_info()

        if fetched is None: return redirect("/ditte")

        fetched["ditta_id"] = ditta_id

        return render_template("aggiorna-ditta.html", **fetched)

    if request.method == "POST":
        nome = request.form.get("nome")
        piva = request.form.get("piva")
        nome_cognome_referente = request.form.get("nome_cognome_referente")
        email_referente = request.form.get("email_referente")
        telefono_referente = request.form.get("telefono_referente")
        note = request.form.get("note")
        ditta_id = request.form.get("ditta_id")

        @fredbconn.connected_to_database
        def update_db(cursor):
            cursor.execute("""
            UPDATE ditte
            SET nome = %s,
                piva = %s,
                nome_cognome_referente = %s,
                email_referente = %s,
                telefono_referente = %s,
                note = %s
            WHERE id = %s
            """, (nome, piva, nome_cognome_referente, email_referente, telefono_referente, note, ditta_id))

        update_db()

        flash("Ditta aggiornata con successo", "success")
        return redirect("/ditte")


@app.route("/aggiungi-ditte", methods=["GET", "POST"])
@fredauth.authorized("admin")
def aggiungi_ditte():
    if request.method == "GET":
        return render_template("aggiungi-ditte.html")
    
    if request.method == "POST":
        # Extract the company name from the form
        nome_ditta = request.form.get("nome")
        
        # Extract and trim the partita IVA as requested
        piva = request.form.get("piva", "").strip()
        
        # Check if a company with this name or partita IVA already exists 
        @fredbconn.connected_to_database
        def check_duplicate_ditta(cursor):
            if piva:
                # Check both name and partita IVA if provided
                cursor.execute("""
                SELECT id FROM ditte 
                WHERE REPLACE(LOWER(nome), ' ', '') = REPLACE(LOWER(%s), ' ', '')
                OR TRIM(piva) = %s
                """, (nome_ditta, piva))
            else:
                # Check only name if partita IVA not provided
                cursor.execute("""
                SELECT id FROM ditte 
                WHERE REPLACE(LOWER(nome), ' ', '') = REPLACE(LOWER(%s), ' ', '')
                """, (nome_ditta,))
                
            return cursor.fetchone()
        
        # Call the function and check the result
        duplicate_found = check_duplicate_ditta()
        
        if duplicate_found:
            flash("Ditta già esistente", "error")
            return redirect("/aggiungi-ditte")
            
        # If no duplicate, proceed with company creation
        ditta = Ditta.from_form()
        ditta.add_to_db()
        flash("Ditta aggiunta con successo", "success")
        return redirect("/aggiungi-ditte")


@app.route("/elimina-ditta", methods=["POST"])
@fredauth.authorized("admin")
def elimina_ditta():

    if session["user"] == passwords.no_permessi_eliminare or session["user"] == "Pippo2":
        flash("Non hai i permessi per eliminare ditte", "error")
        return redirect(request.referrer or "/ditte")
    
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
    return redirect(request.referrer or "/ditte")


@app.route("/dipendenti")
@fredauth.authorized("user")
def show_dipendenti():
    if request.method == "GET":
        id_ditta = request.args.get("id_ditta")
        cognome = request.args.get("cognome")
        annullati = request.args.get("annullati")  # Parameter for filtered view

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
                    dipendenti.accesso_bloccato,
                    dipendenti.note,
                    dipendenti.id,
                    dipendenti.scadenza_autorizzazione,
                    dipendenti.badge_sospeso,
                    dipendenti.badge_annullato,
                    dipendenti.is_badge_temporaneo,
                    dipendenti.numero_badge,
                    ruoli.nome_ruolo
                FROM 
                    dipendenti
                JOIN 
                    ditte
                ON 
                    dipendenti.ditta_id = ditte.id
                LEFT JOIN
                    ruoli
                ON
                    dipendenti.ruolo_id = ruoli.id
                WHERE
                    ditte.id = %s
                ORDER BY
                    dipendenti.cognome ASC
                """, (id_ditta,))

                return cursor.fetchall()
            
            fetch_dipendenti_data = func

        elif cognome is not None:
            @fredbconn.connected_to_database
            def func(cursor):
                cursor.execute("""
                SELECT 
                    ditte.nome AS nome_ditta,
                    dipendenti.nome AS nome_dipendente, 
                    dipendenti.cognome,  
                    dipendenti.is_badge_already_emesso, 
                    dipendenti.accesso_bloccato,
                    dipendenti.note,
                    dipendenti.id,
                    dipendenti.scadenza_autorizzazione,
                    dipendenti.badge_sospeso,
                    dipendenti.badge_annullato,
                    dipendenti.is_badge_temporaneo,
                    dipendenti.numero_badge,
                    ruoli.nome_ruolo
                FROM 
                    dipendenti
                JOIN 
                    ditte
                ON 
                    dipendenti.ditta_id = ditte.id
                LEFT JOIN
                    ruoli
                ON
                    dipendenti.ruolo_id = ruoli.id
                WHERE
                    INSTR(LOWER(dipendenti.cognome), LOWER(%s)) > 0 
                ORDER BY
                    dipendenti.cognome ASC
                """, (cognome,))

                return cursor.fetchall()

            fetch_dipendenti_data = func
            
        elif annullati is not None:
            @fredbconn.connected_to_database
            def func(cursor):
                cursor.execute("""
                SELECT 
                    ditte.nome AS nome_ditta,
                    dipendenti.nome AS nome_dipendente, 
                    dipendenti.cognome,  
                    dipendenti.is_badge_already_emesso, 
                    dipendenti.accesso_bloccato,
                    dipendenti.note,
                    dipendenti.id,
                    dipendenti.scadenza_autorizzazione,
                    dipendenti.badge_sospeso,
                    dipendenti.badge_annullato,
                    dipendenti.is_badge_temporaneo,
                    dipendenti.numero_badge,
                    ruoli.nome_ruolo
                FROM 
                    dipendenti
                JOIN 
                    ditte
                ON 
                    dipendenti.ditta_id = ditte.id
                LEFT JOIN
                    ruoli
                ON
                    dipendenti.ruolo_id = ruoli.id
                WHERE
                    dipendenti.badge_annullato = 1
                ORDER BY
                    dipendenti.cognome ASC
                """)

                return cursor.fetchall()

            fetch_dipendenti_data = func
        
        # Set fetched to an empty list when no filter is applied
        fetched = [] if fetch_dipendenti_data is None else fetch_dipendenti_data()

        @fredbconn.connected_to_database
        def fetch_ditte_names(cursor):
            cursor.execute("""
            SELECT id, nome
            FROM ditte
            ORDER BY nome ASC
            """)

            return cursor.fetchall()
        
        ditte = fetch_ditte_names()

        return render_template("dipendenti.html", dipendenti = fetched, ditte = ditte)


@app.route("/aggiungi-dipendenti", methods=["GET", "POST"])
@fredauth.authorized("admin")
def aggiungi_dipendenti():
    if request.method == "GET":
        @fredbconn.connected_to_database
        def fetch_ditte(cursor):
            cursor.execute("""
            SELECT nome
            FROM ditte
            ORDER BY nome ASC
            """)

            fetched = cursor.fetchall()

            ret = []

            for row in fetched:
                ret.append(row[0])
            
            return ret
        
        @fredbconn.connected_to_database
        def fetch_ruoli(cursor):
            cursor.execute("""
            SELECT id, nome_ruolo
            FROM ruoli
            ORDER BY id ASC
            """)
            
            return cursor.fetchall()
        
        ditte = fetch_ditte()
        ruoli = fetch_ruoli()
        return render_template("aggiungi-dipendenti.html", ditte=ditte, ruoli=ruoli)
    
    if request.method == "POST":
        try:
            # Extract relevant form data
            nome = request.form.get("nome")
            cognome = request.form.get("cognome")
            ditta_name = request.form.get("ditta")
            
            if ditta_name == '':
                raise NoDittaSelectedException
            
            # Get badge_temporaneo field and numero_badge
            is_badge_temporaneo = 1 if request.form.get("is_badge_temporaneo") == "on" else 0
            numero_badge = request.form.get("numero_badge", "")
            
            # Get role_id
            ruolo_id = request.form.get("ruolo_id", "")
            if ruolo_id == "":
                ruolo_id = None
            else:
                ruolo_id = int(ruolo_id)
            
            # If is_badge_temporaneo is False, ensure numero_badge is empty
            if not is_badge_temporaneo:
                numero_badge = ""
                
            # Get scadenza_autorizzazione
            scadenza_autorizzazione = request.form.get("scadenza-autorizzazione")
            
            if not scadenza_autorizzazione:
                scadenza_autorizzazione = None
            else:
                scadenza_autorizzazione = datetime.strptime(scadenza_autorizzazione, "%Y-%m-%d").date()
            
            # First get the ditta_id    
            @fredbconn.connected_to_database
            def get_ditta_id(cursor):
                cursor.execute("""
                SELECT id
                FROM ditte
                WHERE nome = %s
                """, (ditta_name,))
                result = cursor.fetchone()
                return result[0] if result else None
                
            ditta_id = get_ditta_id()
            
            if not ditta_id:
                flash("Ditta non trovata", "error")
                return redirect("/aggiungi-dipendenti")
                
            # Check for duplicate employee in the same company (case-insensitive)
            @fredbconn.connected_to_database
            def check_duplicate_dipendente(cursor):
                cursor.execute("""
                SELECT id 
                FROM dipendenti 
                WHERE LOWER(nome) = LOWER(%s) 
                AND LOWER(cognome) = LOWER(%s)
                AND ditta_id = %s
                """, (nome, cognome, ditta_id))
                return cursor.fetchone()
            
            # Call the function to check for duplicates
            duplicate_found = check_duplicate_dipendente()
            
            if duplicate_found:
                flash("Dipendente già esistente nella ditta", "error")
                return redirect("/aggiungi-dipendenti")
                
            is_badge_already_emesso = 0
            accesso_bloccato = 0
            badge_sospeso = 0
            badge_annullato = 0
            note = request.form.get("note", "")
            
            # If badge_temporaneo is True, ensure a valid expiration date exists
            if is_badge_temporaneo and not scadenza_autorizzazione:
                flash("È necessario specificare una data di scadenza per i badge temporanei", "error")
                return redirect("/aggiungi-dipendenti")
                
            # If all checks pass, create the employee
            @fredbconn.connected_to_database
            def add_dipendente(cursor):
                cursor.execute("""
                INSERT INTO dipendenti(
                    nome, cognome, ditta_id, is_badge_already_emesso, 
                    accesso_bloccato, note, scadenza_autorizzazione, 
                    badge_sospeso, badge_annullato, is_badge_temporaneo, numero_badge,
                    ruolo_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    nome, cognome, ditta_id, is_badge_already_emesso,
                    accesso_bloccato, note, scadenza_autorizzazione,
                    badge_sospeso, badge_annullato, is_badge_temporaneo, numero_badge,
                    ruolo_id
                ))
                
            add_dipendente()
            flash("Dipendente aggiunto con successo", "success")
            return redirect("/aggiungi-dipendenti")
                
        except NoDittaSelectedException:
            flash("Selezionare una ditta", "error")
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
        
        if not fetched or not password == fetched[0]:
            flash("Utente o password sbagliati", "error")
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


@app.route('/genera-report')
@fredauth.authorized("user")
def genera_report():
    
    # Get the report as a BytesIO object
    output = report_generator_completo.generate_report()
    
    # Send the in-memory file as an attachment
    return send_file(
        output,
        as_attachment=True,
        download_name="report.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/checkbox-pressed', methods=["POST"])
@fredauth.authorized("admin")
def checkbox_pressed():
    """
    Endpoint to handle checkbox state changes for different entity types.
    Takes JSON data containing entity type, ID, and the new state value.
    """

    # Kick out user from changing the checkboxes
    if session["user"] == passwords.no_permessi_eliminare or session["user"] == "Pippo2":
        return jsonify({"error": "Non hai i permessi per modificare questo campo"}), 403

    try:
        # Get JSON data from the request
        data = request.get_json()

        # Check if data exists
        if not data:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "Non sono stati ricevuti dati JSON"}), 400
            flash("Non sono stati ricevuti dati JSON", "error")
            return redirect(request.referrer or url_for("/"))
          
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": str(e)}), 400
        flash(str(e), "error")
        return redirect(request.referrer or url_for("/"))
    
    # Extract required fields
    data_type = data.get("type")
    data_id = data.get("id")
    
    # Check if 'clicked' exists in the data
    if "clicked" not in data:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Campo richiesto mancante: 'clicked'"}), 400
        flash("Campo richiesto mancante: 'clicked'", "error")
        return redirect(request.referrer or url_for("/"))
    
    # Convert the clicked value to integer (0 or 1)
    try:
        data_clicked_value = int(data.get("clicked"))
        if data_clicked_value not in [0, 1]:
            raise ValueError("Il valore 'clicked' deve essere 0 o 1")
    except ValueError as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": str(e)}), 400
        flash(str(e), "error")
        return redirect(request.referrer or url_for("/"))

    # Validate other required fields
    if not data_type or not data_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Campi richiesti mancanti"}), 400
        flash("Campi richiesti mancanti", "error")
        return redirect(request.referrer or url_for("/"))
    
    # Process different entity types
    match data_type:
        case "dipendente":
            # Process different field updates for employee type
            match data.get("field"):
                case "accesso":
                    @fredbconn.connected_to_database
                    def set_dipendente_accesso(cursor, id, new_value):
                        cursor.execute("SELECT accesso_bloccato FROM dipendenti WHERE id = %s", (id,))
                        result = cursor.fetchone()
                        if not result:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({"error": "Dipendente non trovato"}), 404
                            flash("Il dipendente che voleva modificare è stato eliminato", "error")
                            return redirect(request.referrer or url_for("/"))
                        
                        cursor.execute("UPDATE dipendenti SET accesso_bloccato = %s WHERE id = %s", (new_value, id))
                        return jsonify({
                            "success": "Accesso aggiornato con successo",
                            "newState": new_value
                        }), 200
                    
                    return set_dipendente_accesso(data_id, data_clicked_value)
                        
                case "badge":
                    if (session['user'] != passwords.capo1) and (session['user'] != passwords.capo2):
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                "error": "Non hai i permessi per modificare questo campo",
                                "newState": None
                            }), 403
                        flash("Non hai i permessi per modificare questo campo", "error")
                        return redirect(request.referrer or url_for("/"))
                    
                    @fredbconn.connected_to_database
                    def set_dipendente_badge_emesso(cursor, id, new_value):
                        cursor.execute("SELECT is_badge_already_emesso FROM dipendenti WHERE id = %s", (id,))
                        result = cursor.fetchone()
                        if not result:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({"error": "Dipendente non trovato"}), 404
                            flash("Il dipendente che voleva modificare è stato eliminato", "error")
                            return redirect(request.referrer or url_for("/"))
                        
                        cursor.execute("UPDATE dipendenti SET is_badge_already_emesso = %s WHERE id = %s", (new_value, id))
                        return jsonify({
                            "success": "Stato del badge aggiornato con successo",
                            "newState": new_value
                        }), 200
                    
                    return set_dipendente_badge_emesso(data_id, data_clicked_value)
                
                case "badge_sospeso":
                    @fredbconn.connected_to_database
                    def set_dipendente_badge_sospeso(cursor, id, new_value):
                        cursor.execute("SELECT badge_sospeso FROM dipendenti WHERE id = %s", (id,))
                        result = cursor.fetchone()
                        if not result:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({"error": "Dipendente non trovato"}), 404
                            flash("Il dipendente che voleva modificare è stato eliminato", "error")
                            return redirect(request.referrer or url_for("/"))
                        
                        cursor.execute("UPDATE dipendenti SET badge_sospeso = %s WHERE id = %s", (new_value, id))
                        return jsonify({
                            "success": "Stato di sospensione del badge aggiornato con successo",
                            "newState": new_value
                        }), 200
                    
                    return set_dipendente_badge_sospeso(data_id, data_clicked_value)
                
                case "badge_annullato":
                    @fredbconn.connected_to_database
                    def set_dipendente_badge_annullato(cursor, id, new_value):
                        cursor.execute("SELECT badge_annullato FROM dipendenti WHERE id = %s", (id,))
                        result = cursor.fetchone()
                        if not result:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({"error": "Dipendente non trovato"}), 404
                            flash("Il dipendente che voleva modificare è stato eliminato", "error")
                            return redirect(request.referrer or url_for("/"))
                        
                        cursor.execute("UPDATE dipendenti SET badge_annullato = %s WHERE id = %s", (new_value, id))
                        return jsonify({
                            "success": "Stato di annullamento del badge aggiornato con successo",
                            "newState": new_value
                        }), 200
                    
                    return set_dipendente_badge_annullato(data_id, data_clicked_value)
                
                case _:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({"error": "Campo non riconosciuto"}), 400
                    flash("Campo non riconosciuto", "error")
                    return redirect(request.referrer or url_for("/"))
    
        case "ditta":
            match data.get("field"):
                case "ditta_individuale":
                    @fredbconn.connected_to_database
                    def set_ditta_individuale(cursor, id, new_value):
                        cursor.execute("SELECT is_ditta_individuale FROM ditte WHERE id = %s", (id,))
                        result = cursor.fetchone()
                        if not result:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({"error": "Ditta non trovata"}), 404
                            flash("La ditta che voleva modificare è stata eliminata", "error")
                            return redirect(request.referrer or url_for("/"))
                        
                        cursor.execute("UPDATE ditte SET is_ditta_individuale = %s WHERE id = %s", (new_value, id))
                        return jsonify({
                            "success": "Stato ditta individuale aggiornato con successo",
                            "newState": new_value
                        }), 200
                    
                    return set_ditta_individuale(data_id, data_clicked_value)
                
                case _:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({"error": "Campo non riconosciuto"}), 400
                    flash("Campo non riconosciuto", "error")
                    return redirect(request.referrer or url_for("/"))

        case _:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "Tipo di entità non riconosciuto"}), 400
            flash("Tipo di entità non riconosciuto", "error")
            return redirect(request.referrer or url_for("/"))


if __name__ == "__main__":
    fredbconn.initialize_database(*passwords.database_config)

    class CrashLogger:
        def __init__(self, log_dir=None):
            # Set default log directory if none provided
            if log_dir is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                log_dir = os.path.join(base_dir, "..", "crash-logs")
            
            # Store the log directory path but don't create it yet
            self.log_dir = os.path.abspath(log_dir)
            
            # Set the global exception hook to log unhandled exceptions
            sys.excepthook = self.log_exception
            
            # Flag to track if logging has been initialized
            self._logging_initialized = False

        def _initialize_logging(self):
            """
            Initialize logging only when an exception occurs by creating the log directory
            and setting up the log file with the current timestamp.
            """
            if self._logging_initialized:
                return
                
            # Create log directory if it doesn't exist
            os.makedirs(self.log_dir, exist_ok=True)
                
            # Generate a log filename with current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_filename = f"error_{timestamp}.log"
            self.log_file = os.path.join(self.log_dir, log_filename)
                
            # Configure logging
            logging.basicConfig(
                filename=self.log_file,
                level=logging.ERROR,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )
            
            self._logging_initialized = True

        def log_exception(self, exc_type, exc_value, exc_traceback):
            """
            Logs uncaught exceptions with the full traceback.
            Only creates the log file when an exception actually occurs.
            """
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Initialize logging if this is the first error
            self._initialize_logging()
            
            error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logging.error("Unhandled Exception:\n" + error_message)
            
            # Call the original exception hook to maintain standard behavior
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

    crash_logger = CrashLogger()

    oauth_routes.init_oauth_routes(app, passwords.email_config)

    serve(app, host='0.0.0.0', port=16000)
    # app.run(host="127.0.0.1", port="5000", debug=True)