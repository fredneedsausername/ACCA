# Licensed under the BSD 2-Clause License. See LICENSE file in the project root for details.

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import passwords
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequest
import fredbconn
import fredauth
from waitress import serve
import xlsxwriter
import io
from datetime import datetime

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = passwords.app_secret_key

class NoDittaSelectedException(Exception):
    """Exception raised when no ditta (entity) is selected."""
    pass


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
            nome = "No"

        piva = request.form.get("piva", "")
        if not piva:
            piva = "No"

        blocca_accesso = request.form.get("blocca_accesso")
        if blocca_accesso is None: blocca_accesso = 0
        if blocca_accesso == "yes": blocca_accesso = 1

        nome_cognome_referente = request.form.get("nome_cognome_referente", "")
        if not nome_cognome_referente:
            nome_cognome_referente = "No"
        
        email_referente = request.form.get("email_referente", "")
        if not email_referente:
            email_referente = "No"
        
        telefono_referente = request.form.get("telefono_referente", "")
        if not telefono_referente:
            telefono_referente = "No"

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
                    autorizzato,
                    note
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
                "autorizzato": dipendente_tuple[4],
                "note": dipendente_tuple[5]
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
        autorizzato = (1 if (request.form.get('autorizzato') == 'yes') else 0)
        note = request.form.get('note')
        dipendente_id = request.form.get("dipendente_id")

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
            """, (nome, cognome, ditta, is_badge_already_emesso, autorizzato, note, dipendente_id))

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
                    INSTR(LOWER(dipendenti.cognome), LOWER(%s)) > 0 
                ORDER BY
                    dipendenti.cognome ASC
                """, (cognome,))

                return cursor.fetchall()

            fetch_dipendenti_data = func

        # else:
        #     @fredbconn.connected_to_database
        #     def func(cursor):
        #         cursor.execute("""
        #         SELECT 
        #             ditte.nome AS nome_ditta,
        #             dipendenti.nome AS nome_dipendente, 
        #             dipendenti.cognome,  
        #             dipendenti.is_badge_already_emesso, 
        #             dipendenti.autorizzato,
        #             dipendenti.note,
        #             dipendenti.id
        #         FROM 
        #             dipendenti
        #         JOIN 
        #             ditte
        #         ON 
        #             dipendenti.ditta_id = ditte.id
        #         ORDER BY
        #             dipendenti.cognome ASC
        #         """)

        #         return cursor.fetchall()
            
        #    fetch_dipendenti_data = func
        
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
    #TODO testa ognuno di questi messaggi di errore
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

    @fredbconn.connected_to_database
    def fetch_dipendenti(cursor):
        cursor.execute("""
        SELECT
            dipendenti.autorizzato,
            ditte.blocca_accesso,
            ditte.nome,
            dipendenti.nome,
            dipendenti.cognome,  
            dipendenti.is_badge_already_emesso, 
            dipendenti.note
        FROM 
            dipendenti
        JOIN 
            ditte
        ON 
            dipendenti.ditta_id = ditte.id
        ORDER BY
            ditte.nome ASC
        """)

        return fredbconn.fetch_generator(cursor)
    
    custom_data = []

    for dipendente in fetch_dipendenti():

        if ( (not dipendente[0]) or dipendente[1] ):
            continue

        custom_data.append(
            (
                dipendente[2], 
                dipendente[3],
                dipendente[4],
                "Sì" if dipendente[5] else "No",
                dipendente[6]
            )
        )

    todays_local_date = datetime.now().strftime("%d-%m-%Y")

    aggiornato_string = " (Agg. " + todays_local_date + ")"
    
    # Create an in-memory output file for the new workbook.
    output = io.BytesIO()
    
    # Create a workbook and add a worksheet.
    # The workbook is created in memory.
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("report")
    
    # -----------------------------
    # Define common formats
    # -----------------------------
    # Default cell format for data: font size 13, centered text, border=1.
    default_format = workbook.add_format({
        'font_size': 13,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
    })
    
    # Header cell common format: bold text, font size 14, centered, border=1.
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
    })
    
    # For horizontal padding we ensure the columns are wide enough.
    # (XlsxWriter does not support explicit padding settings for cells.)
    
    # -----------------------------
    # Specific header formats
    # -----------------------------
    # First column header ("DITTA"): yellow background and always bold.
    ditta_header_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'bg_color': '#FFFF00'
    })
    # For every data row in the first column, text should be bold too.
    ditta_data_format = workbook.add_format({
        'bold': True,
        'font_size': 13,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
    })
    
    # Second and third column headers: blue background (#00B0F0).
    nome_header_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'bg_color': '#00B0F0'
    })
    # Data for these columns use the default (normal) format.
    
    # Fourth column header: "BADGE EMESSO" with pink background (#F7A4D0).
    badge_header_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'bg_color': '#F7A4D0'
    })
    # Data for badge: normal text.
    badge_data_format = default_format
    
    # Fifth column header: "NOTE" with green background (#92D050).
    note_header_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'bg_color': '#92D050'
    })
    # Data for notes should be italic.
    note_data_format = workbook.add_format({
        'italic': True,
        'font_size': 13,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
    })
    
    # -----------------------------
    # Special first header cell with overflowing rich text
    # -----------------------------
    # This cell is the very first cell of the file.
    # Its text is composed of two parts with different font sizes.
    rich_format_18 = workbook.add_format({
        'font_size': 18,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'bold': True
    })
    rich_format_14 = workbook.add_format({
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'bold': True
    })
    # Write the rich string in cell A1.
    # (By not merging, if adjacent cells are empty the text will overflow.)
    worksheet.write_rich_string(0, 0,
                                rich_format_18, "LISTA PERSONALE AUTORIZZATO ALL'INGRESSO",
                                rich_format_14, aggiornato_string)
    
    # -----------------------------
    # Write the header row (for the data columns) with additional horizontal padding
    # -----------------------------
    header_row = 1
    worksheet.set_row(header_row, 38)  # Approximately 15 * 2.5 = 37.5

    # Note the added spaces before and after the header text to simulate padding.
    worksheet.write(header_row, 0, "  DITTA  ", ditta_header_format)
    worksheet.write(header_row, 1, "  NOME  ", nome_header_format)
    worksheet.write(header_row, 2, "  COGNOME DIPENDENTE  ", nome_header_format)
    worksheet.write(header_row, 3, "  BADGE EMESSO  ", badge_header_format)
    worksheet.write(header_row, 4, "  NOTE  ", note_header_format)
    
    # -----------------------------
    # Insert custom data
    # -----------------------------
    # The custom data is supplied as a list of lists (each sublist is a row).
    # Each row must provide data for:
    # [DITTA, NOME, COGNOME DIPENDENTE, BADGE EMESSO, NOTE]
    
    data_start_row = header_row + 1
    for row_idx, data_row in enumerate(custom_data):
        current_row = data_start_row + row_idx
        # Optionally set a standard row height (e.g. 15 points)
        worksheet.set_row(current_row, 15)
        
        # Write each cell using the appropriate format:
        # Column 0 (DITTA): always bold.
        worksheet.write(current_row, 0, data_row[0], ditta_data_format)
        # Column 1 (NOME)
        worksheet.write(current_row, 1, data_row[1], default_format)
        # Column 2 (COGNOME DIPENDENTE)
        worksheet.write(current_row, 2, data_row[2], default_format)
        # Column 3 (BADGE EMESSO)
        worksheet.write(current_row, 3, data_row[3], badge_data_format)
        # Column 4 (NOTE): italic
        worksheet.write(current_row, 4, data_row[4], note_data_format)
    
    # -----------------------------
    # Dynamically adjust column widths based on the longest text (header or data) plus extra padding
    # -----------------------------
    # Define header names (unpadded)
    headers = ["DITTA", "NOME", "COGNOME DIPENDENTE", "BADGE EMESSO", "NOTE"]
    num_columns = len(headers)
    
    # Initialize a list to hold the maximum length (in characters) for each column.
    col_widths = [len(header) for header in headers]
    
    # Update each column width based on the data in custom_data.
    # (Make sure 'custom_data' is defined before this snippet.)
    for row in custom_data:
        for i in range(num_columns):
            cell_text = str(row[i])
            # Measure the length of the cell text.
            cell_length = len(cell_text)
            if cell_length > col_widths[i]:
                col_widths[i] = cell_length
    
    # Add extra padding to each column width. Increase the extra_padding value if needed.
    extra_padding = 10  # This value can be adjusted as needed.
    col_widths = [width + extra_padding for width in col_widths]
    
    # Set the width for each column individually.
    for i, width in enumerate(col_widths):
        worksheet.set_column(i, i, width)



    
    # Close the workbook before sending the data.
    workbook.close()
    output.seek(0)
    
    # Send the in-memory file as an attachment.
    return send_file(
        output,
        as_attachment=True,
        download_name="report.xlsx",  # For Flask >=2.0; use attachment_filename for older versions.
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


if __name__ == "__main__":
    fredbconn.initialize_database(*passwords.database_config)
    serve(app, host='0.0.0.0', port=16000)
    # app.run(host="127.0.0.1", port="5000", debug=True)