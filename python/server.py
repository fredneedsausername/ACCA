# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

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

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = passwords.app_secret_key

class NoDittaSelectedException(Exception):
    """Exception raised when no ditta (entity) is selected."""
    pass


class Dipendente:

    def __init__(self, nome: str, cognome: str, ditta_name: str, is_badge_already_emesso: int, accesso_bloccato: int, note: str,
                 scadenza_autorizzazione: date):
        self.nome = nome
        self.cognome = cognome
        self.ditta_name = ditta_name
        self.is_badge_already_emesso = is_badge_already_emesso
        self.accesso_bloccato = accesso_bloccato
        self.note = note
        self.scadenza_autorizzazione = scadenza_autorizzazione
    
    @classmethod
    def from_form(cls):
        """Transforms the request form into a Dipendente object

        Raises:
            NoDittaSelectedException: no ditta was selected in the form for the creation of the dipendente.

        Returns:
            Dipendente: an object of type Dipendente
        """

        ditta_name = request.form.get("ditta")
        if ditta_name == '':
            raise NoDittaSelectedException

        nome = request.form.get("nome")

        cognome = request.form.get("cognome")

        is_badge_already_emesso = request.form.get("is_badge_already_emesso")
        if is_badge_already_emesso is None: is_badge_already_emesso = 0
        if is_badge_already_emesso == "yes": is_badge_already_emesso = 1

        accesso_bloccato = request.form.get("accesso-bloccato")
        if accesso_bloccato is None: accesso_bloccato = 0
        if accesso_bloccato == "yes": accesso_bloccato = 1

        note = request.form.get("note")

        scadenza_autorizzazione = request.form.get("scadenza-autorizzazione")
        
        if scadenza_autorizzazione:
            scadenza_autorizzazione = datetime.strptime(scadenza_autorizzazione, "%Y-%m-%d").date()

        return cls(nome, cognome, ditta_name, is_badge_already_emesso, accesso_bloccato, note, scadenza_autorizzazione)   
    
    def get_fields(self):
        return self.nome, self.cognome, self.ditta_name, self.is_badge_already_emesso, self.accesso_bloccato, self.note, self.scadenza_autorizzazione
    
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
        INSERT INTO dipendenti(nome, cognome, ditta_id, is_badge_already_emesso, accesso_bloccato, note, scadenza_autorizzazione)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (fields[0], fields[1], ditta_id, fields[3], fields[4], fields[5], scadenza_autorizzazione))

class Ditta:

    def get_fields(self): # This function is structured weird to make it not overflow the screen

        ret = []
        ret.append(self.nome)
        ret.append(self.piva)
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
        ditte(nome, piva, blocca_accesso, nome_cognome_referente, email_referente, telefono_referente)
        VALUES
        (%s, %s, %s, %s, %s, %s)
        """, self.get_fields())
    

    def __init__(self, nome: str, piva: str, blocca_accesso: int, nome_cognome_referente: str,
                 email_referente: str, telefono_referente: str):
        self.nome = nome
        self.piva = piva
        self.blocca_accesso = blocca_accesso
        self.nome_cognome_referente = nome_cognome_referente
        self.email_referente = email_referente
        self.telefono_referente = telefono_referente
    

    @classmethod
    def from_form(cls):

        nome = request.form.get("nome")
        if not nome:
            nome = ""

        piva = request.form.get("piva", "")
        if not piva:
            piva = ""

        blocca_accesso = request.form.get("blocca_accesso")
        if blocca_accesso is None: blocca_accesso = 0
        if blocca_accesso == "yes": blocca_accesso = 1

        nome_cognome_referente = request.form.get("nome_cognome_referente", "")
        if not nome_cognome_referente:
            nome_cognome_referente = ""
        
        email_referente = request.form.get("email_referente", "")
        if not email_referente:
            email_referente = ""
        
        telefono_referente = request.form.get("telefono_referente", "")
        if not telefono_referente:
            telefono_referente = ""

        return cls(nome, piva, blocca_accesso, nome_cognome_referente, email_referente, telefono_referente)
    

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
                    scadenza_autorizzazione
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
                "scadenza_autorizzazione": dipendente_tuple[6]
            }


            #TODO if possible, fix this part by adding a generator instead of fetchall
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
            """, (fetched["selected_ditta"]))

            return cursor.fetchone()

        fetched_selected_ditta_name = fetch_selected_ditta_name()

        fetched["selected_ditta_name"] = fetched_selected_ditta_name[0]

        return render_template("aggiorna-dipendente.html", **fetched)

    if request.method == "POST":
        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        ditta = request.form.get('ditta')
        is_badge_already_emesso = (1 if (request.form.get('is_badge_already_emesso') == 'yes') else 0)
        accesso_bloccato = (1 if (request.form.get('accesso_bloccato') == 'yes') else 0)
        note = request.form.get('note')
        dipendente_id = request.form.get("dipendente_id")

        scadenza_autorizzazione = request.form.get("scadenza-autorizzazione")
        if scadenza_autorizzazione:
            scadenza_autorizzazione = datetime.strptime(scadenza_autorizzazione, "%Y-%m-%d").date() 

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
                scadenza_autorizzazione = %s
                
            WHERE id = %s
            """, (nome, cognome, ditta, is_badge_already_emesso, accesso_bloccato, note, dipendente_id, scadenza_autorizzazione))

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

    nome = request.args.get("nome")

    fetch_ditte_info = None

    if nome is not None:
        @fredbconn.connected_to_database
        def func(cursor):
            cursor.execute("""
            SELECT
                id, nome, piva, blocca_accesso, nome_cognome_referente, email_referente, telefono_referente
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
                id, nome, piva, blocca_accesso, nome_cognome_referente, email_referente, telefono_referente
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
                "blocca_accesso": ditta_tuple[2],
                "nome_cognome_referente": ditta_tuple[3],
                "email_referente": ditta_tuple[4],
                "telefono_referente": ditta_tuple[5]
            }

            return ret
        
        fetched = fetch_info()

        if fetched is None: return redirect("/ditte")

        fetched["ditta_id"] = ditta_id

        return render_template("aggiorna-ditta.html", **fetched)

    if request.method == "POST":


        nome = request.form.get("nome")
        piva = request.form.get("piva")
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
                blocca_accesso = %s,
                nome_cognome_referente = %s,
                email_referente = %s,
                telefono_referente = %s
                
            WHERE id = %s
            """, (nome, piva, blocca_accesso,
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


@app.route("/dipendenti")
@fredauth.authorized("user")
def show_dipendenti():

    if request.method == "GET":

        id_ditta = request.args.get("id_ditta")
        cognome = request.args.get("cognome")

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
                    dipendenti.scadenza_autorizzazione
                FROM 
                    dipendenti
                JOIN 
                    ditte
                ON 
                    dipendenti.ditta_id = ditte.id
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
                    dipendenti.id
                FROM 
                    dipendenti
                JOIN 
                    ditte
                ON 
                    dipendenti.ditta_id = ditte.id
                WHERE
                    INSTR(LOWER(dipendenti.cognome), LOWER(%s)) > 0 
                ORDER BY
                    dipendenti.cognome ASC
                """, (cognome,))

                return cursor.fetchall()

            fetch_dipendenti_data = func
        
        fetched = None
        
        if fetch_dipendenti_data is not None:
            fetched = fetch_dipendenti_data()

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
        
        ditte = fetch_ditte()

        return render_template("aggiungi-dipendenti.html", ditte = ditte)
    
    if request.method == "POST":
        try:
            dipendente = Dipendente.from_form()
        except NoDittaSelectedException as e:
            flash("Selezionare una ditta", "error")
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


@app.route('/genera-report')
@fredauth.authorized("user")
def genera_report():

    return render_template("report-disattivato.html")

    # @fredbconn.connected_to_database
    # def fetch_dipendenti(cursor):
    #     cursor.execute("""
    #     SELECT
    #         dipendenti.accesso_bloccato,
    #         ditte.blocca_accesso,
    #         ditte.nome,
    #         dipendenti.nome,
    #         dipendenti.cognome,  
    #         dipendenti.is_badge_already_emesso, 
    #         dipendenti.note
    #     FROM 
    #         dipendenti
    #     JOIN 
    #         ditte
    #     ON 
    #         dipendenti.ditta_id = ditte.id
    #     ORDER BY
    #         ditte.nome ASC
    #     """)

    #     return fredbconn.fetch_generator(cursor)
    
    # custom_data = []

    # for dipendente in fetch_dipendenti():

    #     if ( (not dipendente[0]) or dipendente[1] ):
    #         continue

    #     custom_data.append(
    #         (
    #             dipendente[2], 
    #             dipendente[3],
    #             dipendente[4],
    #             "Sì" if dipendente[5] else "No",
    #             dipendente[6]
    #         )
    #     )

    # todays_local_date = datetime.now().strftime("%d-%m-%Y")

    # aggiornato_string = " (Agg. " + todays_local_date + ")"
    
    # # Create an in-memory output file for the new workbook.
    # output = io.BytesIO()
    
    # # Create a workbook and add a worksheet.
    # # The workbook is created in memory.
    # workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    # worksheet = workbook.add_worksheet("report")
    
    # # -----------------------------
    # # Define common formats
    # # -----------------------------
    # # Default cell format for data: font size 13, centered text, border=1.
    # default_format = workbook.add_format({
    #     'font_size': 13,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    # })
    
    # # Header cell common format: bold text, font size 14, centered, border=1.
    # header_format = workbook.add_format({
    #     'bold': True,
    #     'font_size': 14,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    # })
    
    # # For horizontal padding we ensure the columns are wide enough.
    # # (XlsxWriter does not support explicit padding settings for cells.)
    
    # # -----------------------------
    # # Specific header formats
    # # -----------------------------
    # # First column header ("DITTA"): yellow background and always bold.
    # ditta_header_format = workbook.add_format({
    #     'bold': True,
    #     'font_size': 14,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    #     'bg_color': '#FFFF00'
    # })
    # # For every data row in the first column, text should be bold too.
    # ditta_data_format = workbook.add_format({
    #     'bold': True,
    #     'font_size': 13,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    # })
    
    # # Second and third column headers: blue background (#00B0F0).
    # nome_header_format = workbook.add_format({
    #     'bold': True,
    #     'font_size': 14,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    #     'bg_color': '#00B0F0'
    # })
    # # Data for these columns use the default (normal) format.
    
    # # Fourth column header: "BADGE EMESSO" with pink background (#F7A4D0).
    # badge_header_format = workbook.add_format({
    #     'bold': True,
    #     'font_size': 14,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    #     'bg_color': '#F7A4D0'
    # })
    # # Data for badge: normal text.
    # badge_data_format = default_format
    
    # # Fifth column header: "NOTE" with green background (#92D050).
    # note_header_format = workbook.add_format({
    #     'bold': True,
    #     'font_size': 14,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    #     'bg_color': '#92D050'
    # })
    # # Data for notes should be italic.
    # note_data_format = workbook.add_format({
    #     'italic': True,
    #     'font_size': 13,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    # })
    
    # # -----------------------------
    # # Special first header cell with overflowing rich text
    # # -----------------------------
    # # This cell is the very first cell of the file.
    # # Its text is composed of two parts with different font sizes.
    # rich_format_18 = workbook.add_format({
    #     'font_size': 18,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    #     'bold': True
    # })
    # rich_format_14 = workbook.add_format({
    #     'font_size': 14,
    #     'align': 'center',
    #     'valign': 'vcenter',
    #     'border': 1,
    #     'bold': True
    # })
    # # Write the rich string in cell A1.
    # # (By not merging, if adjacent cells are empty the text will overflow.)
    # worksheet.write_rich_string(0, 0,
    #                             rich_format_18, "LISTA PERSONALE AUTORIZZATO ALL'INGRESSO",
    #                             rich_format_14, aggiornato_string)
    
    # # -----------------------------
    # # Write the header row (for the data columns) with additional horizontal padding
    # # -----------------------------
    # header_row = 1
    # worksheet.set_row(header_row, 38)  # Approximately 15 * 2.5 = 37.5

    # # Note the added spaces before and after the header text to simulate padding.
    # worksheet.write(header_row, 0, "  DITTA  ", ditta_header_format)
    # worksheet.write(header_row, 1, "  NOME  ", nome_header_format)
    # worksheet.write(header_row, 2, "  COGNOME DIPENDENTE  ", nome_header_format)
    # worksheet.write(header_row, 3, "  BADGE EMESSO  ", badge_header_format)
    # worksheet.write(header_row, 4, "  NOTE  ", note_header_format)
    
    # # -----------------------------
    # # Insert custom data
    # # -----------------------------
    # # The custom data is supplied as a list of lists (each sublist is a row).
    # # Each row must provide data for:
    # # [DITTA, NOME, COGNOME DIPENDENTE, BADGE EMESSO, NOTE]
    
    # data_start_row = header_row + 1
    # for row_idx, data_row in enumerate(custom_data):
    #     current_row = data_start_row + row_idx
    #     # Optionally set a standard row height (e.g. 15 points)
    #     worksheet.set_row(current_row, 15)
        
    #     # Write each cell using the appropriate format:
    #     # Column 0 (DITTA): always bold.
    #     worksheet.write(current_row, 0, data_row[0], ditta_data_format)
    #     # Column 1 (NOME)
    #     worksheet.write(current_row, 1, data_row[1], default_format)
    #     # Column 2 (COGNOME DIPENDENTE)
    #     worksheet.write(current_row, 2, data_row[2], default_format)
    #     # Column 3 (BADGE EMESSO)
    #     worksheet.write(current_row, 3, data_row[3], badge_data_format)
    #     # Column 4 (NOTE): italic
    #     worksheet.write(current_row, 4, data_row[4], note_data_format)
    
    # # -----------------------------
    # # Dynamically adjust column widths based on the longest text (header or data) plus extra padding
    # # -----------------------------
    # # Define header names (unpadded)
    # headers = ["DITTA", "NOME", "COGNOME DIPENDENTE", "BADGE EMESSO", "NOTE"]
    # num_columns = len(headers)
    
    # # Initialize a list to hold the maximum length (in characters) for each column.
    # col_widths = [len(header) for header in headers]
    
    # # Update each column width based on the data in custom_data.
    # # (Make sure 'custom_data' is defined before this snippet.)
    # for row in custom_data:
    #     for i in range(num_columns):
    #         cell_text = str(row[i])
    #         # Measure the length of the cell text.
    #         cell_length = len(cell_text)
    #         if cell_length > col_widths[i]:
    #             col_widths[i] = cell_length
    
    # # Add extra padding to each column width. Increase the extra_padding value if needed.
    # extra_padding = 10  # This value can be adjusted as needed.
    # col_widths = [width + extra_padding for width in col_widths]
    
    # # Set the width for each column individually.
    # for i, width in enumerate(col_widths):
    #     worksheet.set_column(i, i, width)



    
    # # Close the workbook before sending the data.
    # workbook.close()
    # output.seek(0)
    
    # # Send the in-memory file as an attachment.
    # return send_file(
    #     output,
    #     as_attachment=True,
    #     download_name="report.xlsx",  # For Flask >=2.0; use attachment_filename for older versions.
    #     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    # )

@app.route('/checkbox-pressed', methods=["POST"])
@fredauth.authorized("admin")
def checkbox_pressed():

    # The function takes the info from the button and toggles the corresponding value in the db.

    data = None

    try:
        # Get JSON data from the request
        data = request.get_json()

        # Check if data exists
        # Per proteggersi da attacchi informatici
        if not data:
            flash("Non sono stati ricevuti dati JSON", "error")
            return redirect(request.referrer or url_for("/"))
          
    except Exception as e:
        flash(str(e), "error")
        return redirect(request.referrer or url_for("/"))
    
    data_type = data.get("type")
    data_id = data.get("id")
    data_clicked = data.get("clicked")

    if not data_type:
        flash("Campo richiesto mancante: 'type'", "error")
        return redirect(request.referrer or url_for("/"))
    if not data_id:
        flash("Campo richiesto mancante: 'id'", "error")
        return redirect(request.referrer or url_for("/"))
    if not data_clicked:
        flash("Campo richiesto mancante: 'clicked'", "error")
        return redirect(request.referrer or url_for("/"))
    
    match data_type:
        
        case "dipendente":

            match data_clicked:

                case "accesso":

                    @fredbconn.connected_to_database
                    def toggle_dipendente_accesso(cursor, id):

                        cursor.execute("""
                        SELECT accesso_bloccato
                        FROM dipendenti
                        WHERE id = %s
                        """, (id,))

                        result = cursor.fetchone()

                        if not result:
                            flash("Il dipendente che voleva modificare è stato eliminato", "error")
                            return redirect(request.referrer or url_for("/"))
                        
                        accesso_to_be_set = int(not result[0])

                        cursor.execute("""
                        UPDATE dipendenti
                        SET accesso_bloccato = %s                
                        WHERE id = %s
                        """, (accesso_to_be_set, id))

                        return jsonify({"success": "Tutto ok"}), 200
                    
                    return toggle_dipendente_accesso(data_id)
                        
                case "badge":
                    
                    if session['user'] !=  "Malfatti":
                        flash("Solo Malfatti può modificare quel campo", "error")
                        return redirect(request.referrer or url_for("/"))
                    
                    @fredbconn.connected_to_database
                    def toggle_dipendente_badge_emesso(cursor, id):

                        cursor.execute("""
                        SELECT is_badge_already_emesso
                        FROM dipendenti
                        WHERE id = %s
                        """, (id,))

                        result = cursor.fetchone()

                        if not result:
                            flash("Il dipendente che voleva modificare è stato eliminato", "error")
                            return redirect(request.referrer or url_for("/"))
                        
                        badge_emesso_to_be_set = int(not result[0])

                        cursor.execute("""
                        UPDATE dipendenti
                        SET is_badge_already_emesso = %s                
                        WHERE id = %s
                        """, (badge_emesso_to_be_set, id))

                        return jsonify({"success": "Tutto ok"}), 200
                    
                    return toggle_dipendente_badge_emesso(data_id)

if __name__ == "__main__":
    fredbconn.initialize_database(*passwords.database_config)

    class CrashLogger:
        def __init__(self, log_dir=None, log_filename=None):
            # On Windows, use "../crash-logs" as the default log directory.
            if log_dir is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                log_dir = os.path.join(base_dir, "..", "crash-logs")
            
            # Ensure the log directory is an absolute path and exists.
            self.log_dir = os.path.abspath(log_dir)
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Generate a log filename if not provided.
            if log_filename is None:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                log_filename = f"error_{timestamp}.log"
            
            self.log_file = os.path.join(self.log_dir, log_filename)
            
            # Configure logging
            logging.basicConfig(
                filename=self.log_file,
                level=logging.ERROR,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )
            
            # Set the global exception hook to log unhandled exceptions.
            sys.excepthook = self.log_exception

        def log_exception(self, exc_type, exc_value, exc_traceback):
            """
            Logs uncaught exceptions with the full traceback.
            """
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logging.error("Unhandled Exception:\n" + error_message)

        def log_custom_error(self, message):
            """
            Allows manual logging of error messages.
            """
            logging.error(message)

    crash_logger = CrashLogger()
    crash_logger.log_custom_error("ERROR")

    a = 1 / 0
    # serve(app, host='0.0.0.0', port=16000)
    app.run(host="127.0.0.1", port="5000", debug=True)