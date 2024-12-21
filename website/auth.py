from flask import Blueprint, render_template, request, flash, session, redirect, url_for
from flask_login import logout_user, current_user
from datetime import date, timedelta
from flask import Flask
from flask_login import LoginManager
import jinja2
import pdfkit


path_wkthmltopdf = b'C:\Program Files\wkhtmltopdf\\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_wkthmltopdf)




################################################################################
import mysql.connector
from datetime import datetime

db = mysql.connector.connect(
    host="localhost",
    user ="root",
    passwd="123456",
    database = "testdatabase")


################################################################################






auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    user = 'hamza'
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        cursor = db.cursor()
        query = "SELECT * FROM inscription WHERE email = %s AND password = %s"
        values = (email, password)
        cursor.execute(query, values)
        user = cursor.fetchone()
        if user :
           user_id =  user[0]
           session['logged_in'] = True
           session['user_id'] = user_id
           flash('Login successful!',category='success')
           return redirect(url_for('auth.home'))
        else:
           flash('Invalid email or password.', category='error')
    else :
        user = None
    return render_template("login.html",  user=current_user)



@auth.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    return redirect(url_for('auth.login'))



@auth.route('/sign-up',methods=['GET', 'POST'])
def sign_up():
    user = 'hamza'
    if request.method == 'POST':
        email = request.form.get('email')
        firstName = request.form.get('firstName')
        lastName = request.form.get('lastName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        role = request.form.get('role')

        if len(email) < 4:
            flash ('Email must be greater than 4 characters.', category='error')
        elif len(firstName) < 2:
            flash ('First name must be greater than 2 characters.', category='error')
        elif len(lastName) < 2:
            flash ('First name must be greater than 2 characters.', category='error')
        elif password1 != password2:
            flash ('Passwords dont match.', category='error')
        elif len(password1)<5:
            flash ('Passwords must be greater than 5.', category='error')
        elif role == None:
            flash ('Choose your role', category='error')
        else:
            cursor = db.cursor()
            query = "INSERT INTO inscription (email, prenom, nom, password, rolll) VALUES (%s, %s, %s, %s, %s)"
            values = (email, firstName, lastName, password1, role)
            cursor.execute(query, values)
            db.commit()
            flash('Account Created !', category='sucess')

    return render_template("sign_up.html", user=current_user)








@auth.route('/home')
def home():
    if 'user_id' in session:
        user_id = session['user_id']
        cursor = db.cursor()
        query = "SELECT prenom, nom FROM inscription WHERE id = %s"
        values = (user_id,)
        cursor.execute(query, values)
        user_data = cursor.fetchone()
        if user_data:
            first_name, last_name = user_data
            full_name = f"{first_name} {last_name}"

            cursor.execute("SELECT bid, titre, TYPE, ISBN, Place, Auteur, Date_sortie, Numero_copie, Empruntable FROM document")
            documents = cursor.fetchall()

            cursor.execute("SELECT t.book_id, d.titre, t.periode FROM tempoborrowing t JOIN document d ON t.book_id = d.bid WHERE t.person_id = %s", (user_id,))
            demands = cursor.fetchall()

            cursor.execute("SELECT l.book_id, d.titre, p.nom, p.prenom, l.periode, l.statu_s, l.posi FROM borrowing l JOIN document d ON l.book_id = d.bid JOIN inscription p ON l.person_id = p.id WHERE l.person_id = %s", (user_id,))
            loans = cursor.fetchall()

            return render_template("home.html", user=full_name, documents=documents, demands=demands, loans=loans)

    return redirect(url_for('auth.login'))







@auth.route('/reservations', methods=['GET', 'POST'])
def reservations():
    cursor = db.cursor()

    if request.method == 'POST':
        titre = request.form.get('book-title')
        period = request.form.get('duration')
        nom = request.form.get('Nom')
        return_date = request.form.get('return_date')

        cursor.execute("SELECT id, rolll, score, regularization_request FROM inscription WHERE nom = %s", (nom,))
        person_row = cursor.fetchone()
        
        if person_row is not None:
            person_id, rolll, person_points, regularization_request = person_row
        else:
            flash('Person not found.', 'error')
            return redirect(url_for('auth.reservations'))

        cursor.execute("SELECT bid, Empruntable FROM document WHERE titre = %s", (titre,))
        document_row = cursor.fetchone()
        
        if document_row is not None:
            book_id, empruntable = document_row
        else:
            flash('Document not found.', 'error')
            return redirect(url_for('auth.reservations'))

        if empruntable == 'non':
            flash("This document cannot be reserved.", 'error')
            return redirect(url_for('auth.reservations'))

        if rolll == 'student':
            cursor.execute("SELECT COUNT(*) FROM borrowing WHERE person_id = %s AND posi = 'Active'", (person_id,))
            active_loans = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tempoborrowing WHERE person_id = %s", (person_id,))
            temp_reservations = cursor.fetchone()[0]
            max_reservations = 2

            if active_loans + temp_reservations >= max_reservations:
                flash("You have reached the maximum reservation limit or have active loans.", 'error')
                return redirect(url_for('auth.reservations'))

        elif rolll == 'teacher':
            cursor.execute("SELECT COUNT(*) FROM borrowing WHERE person_id = %s AND posi = 'Active'", (person_id,))
            active_loans = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tempoborrowing WHERE person_id = %s", (person_id,))
            temp_reservations = cursor.fetchone()[0]
            max_reservations = 5

            if active_loans + temp_reservations >= max_reservations:
               flash("You have reached the maximum reservation limit or have active loans.", 'error')
               return redirect(url_for('auth.reservations'))

        if person_points <= 0:
            if regularization_request is not None:
                flash("Your points are insufficient for making a reservation.", 'error')
                return render_template('regularization.html', user=current_user, nom=nom)
            else:
                return render_template('regularization.html', user=current_user, nom=nom)

        query = "INSERT INTO tempoborrowing (book_id, person_id, periode, date_debut, date_fin) VALUES (%s, %s, %s, %s, %s)"
        values = (book_id, person_id, period, datetime.now(), return_date)
        cursor.execute(query, values)
        db.commit()

        flash('Reservation made successfully!', 'success')

        # Retrieve the reservation data for the PDF template
        reservation_info = [(cursor.lastrowid, book_id, person_id, period, datetime.now())]

        # Render the template with the reservation information
        rendered_template = render_template(
            'pdf_template.html',
            reservation_info=reservation_info,
            configuration=config
        )

        # Generate the PDF file from the rendered template
        pdfkit.from_string(rendered_template, 'reservation_receipt.pdf', configuration=config)

    cursor.execute("SELECT * FROM tempoborrowing")
    reservations = cursor.fetchall()

    return render_template('reservations.html', user=current_user, reservations=reservations)





@auth.route('/admin')
def admin():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM inscription")
    inscriptions = cursor.fetchall()

    crs = db.cursor()
    crs.execute("SELECT * FROM document")
    documents = crs.fetchall()

    cursor.execute("SELECT * FROM tempoborrowing")
    reservations = cursor.fetchall()
    
    return render_template("admin.html", inscriptions=inscriptions, documents = documents, reservations=reservations)


@auth.route('/Test')
def show_test_table():
    cursor = db.cursor()
    cursor.execute('SELECT * FROM person')
    data = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    return render_template('test.html', data=data, columns=columns)



@auth.route('/delete_person/<int:person_id>', methods=['POST'])
def delete_person(person_id):
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM borrowing WHERE person_id = %s", (person_id,))
    
    cursor.execute("DELETE FROM inscription WHERE id = %s", (person_id,))
    
    db.commit()

    flash('Person deleted successfully!', 'success')

    return redirect(url_for('auth.admin'))



@auth.route('/Ajoutlivre', methods=['GET', 'POST'])
def ajout():
    if request.method == 'POST':
        title = request.form.get('title')
        type = request.form.get('type')
        isbn = request.form.get('isbn')
        place = request.form.get('place')
        author = request.form.get('author')
        release_year = request.form.get('releaseYear')
        num_copies = request.form.get('numCopies')
        borrowable = request.form.get('borrowable')
        if borrowable == "1" :
            borrowable = 'oui'
        else:
            borrowable = 'non'
        cursor = db.cursor()
        
        
        cursor.execute("SELECT MAX(bid) FROM document")
        max_bid = cursor.fetchone()[0]
        
        if max_bid is None:
            max_bid = 0
        
        
        bid = max_bid + 1
        
        query = "INSERT INTO document (bid, titre, TYPE, ISBN, Place, Auteur, Date_sortie, Numero_copie, Empruntable) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (bid, title, type, isbn, place, author, release_year, num_copies, borrowable)
        cursor.execute(query, values)

        db.commit()

        flash('Document added successfully!', 'success')

    return render_template('add_book.html')


@auth.route('/delete_document', methods=['POST'])
def delete_document():
    titre = request.form.get('titre')
    cursor = db.cursor()

    # Perform the deletion logic
    cursor.execute("DELETE FROM document WHERE bid = %s", (titre,))
    db.commit()

    flash('Document deleted successfully!', 'success')

    return redirect(url_for('auth.admin'))



@auth.route('/approved', methods=['POST'])
def approved():
    demande_id = request.form.get('demande_id')
    demande_id1 = request.form.get('demande_id1')

    if demande_id is not None:
        demande_id = int(demande_id)
        # Get the details of the demand from the database using the demande_id
        cursor = db.cursor()
        cursor.execute("SELECT book_id, person_id, periode FROM tempoborrowing WHERE emprunt_id = %s", (demande_id,))
        demand = cursor.fetchone()

        if demand:
            book_id = demand[0]
            person_id = demand[1]
            periode = demand[2]
            crsr = db.cursor()
            crsr.execute("SELECT prenom, nom FROM inscription WHERE id = %s", (person_id,))
            perso = crsr.fetchone()
            nom = perso[0]
            prenom = perso[1]
            
            # Insert the approved demand into the borrowing table
            cursor.execute("INSERT INTO borrowing (book_id, person_id, periode, statu_s, nom, prenom) VALUES (%s, %s, %s, 'approved', %s, %s)", (book_id, person_id, periode, nom, prenom))
            cursor.execute("DELETE FROM tempoborrowing WHERE emprunt_id = %s", (demande_id,))
            db.commit()
            db.commit()
            flash('Demand approved successfully!', 'success')
        else:
            flash('Demand not found!', 'error')

    elif demande_id1 is not None:
        demande_id1 = int(demande_id1)
        # Get the details of the demand from the database using the demande_id
        cursor = db.cursor()
        cursor.execute("SELECT book_id, person_id, periode FROM tempoborrowing WHERE emprunt_id = %s", (demande_id1,))
        demand = cursor.fetchone()
        
        if demand:
            book_id = demand[0]
            person_id = demand[1]
            periode = demand[2]
            crsr = db.cursor()
            crsr.execute("SELECT prenom, nom FROM inscription WHERE id = %s", (person_id,))
            perso = crsr.fetchone()
            nom = perso[0]
            prenom = perso[1]
            
            # Insert the not approved demand into the borrowing table
            cursor.execute("INSERT INTO borrowing (book_id, person_id, periode, statu_s, nom, prenom) VALUES (%s, %s, %s, 'not approved', %s, %s)", (book_id, person_id, periode, nom, prenom))
            cursor.execute("DELETE FROM tempoborrowing WHERE emprunt_id = %s", (demande_id1,))
            db.commit()
            flash('Demand not approved!', 'success')
            
    return redirect(url_for('auth.admin'))







@auth.route('/return_book/<int:loan_id>', methods=['POST'])
def return_book(loan_id):
    loan_id = request.form.get('loan_id')
    cursor = db.cursor()

    if loan_id is not None:
        loan_id = int(loan_id)
        cursor.execute("SELECT person_id, date_fin FROM borrowing WHERE book_id = %s", (loan_id,))
        loan_data = cursor.fetchone()

        # Consume any unread results from the previous query
        cursor.fetchall()

        if loan_data:
            person_id, due_date = loan_data
            today = date.today()

            if due_date is not None and today > due_date:
                # Calculate the number of days late
                days_late = (today - due_date).days

                # Deduct points based on the number of days late
                points_to_deduct = days_late // 7  # Deduct 1 point for every 7 days late
                if points_to_deduct > 0:
                    cursor.execute("UPDATE inscription SET points = points - %s WHERE id = %s", (points_to_deduct, person_id))
                    db.commit()
                    flash(f'{points_to_deduct} point(s) deducted for late return.', 'info')

        cursor.execute(" UPDATE borrowing SET posi = %s WHERE book_id = %s", ('Returned',loan_id,))


        db.commit()
        flash('Book returned successfully!', 'success')

        if loan_data is None:
            # The loan record does not exist
            flash('Failed to return the book. Please try again.', 'error')

    cursor.close()
    return redirect(url_for('auth.home'))







@auth.route('/update_score/<int:person_id>', methods=['POST'])
def update_score(person_id):
    cursor = db.cursor()
    new_score = int(request.form.get('score'))

    # Update the score in the inscription table
    cursor.execute("UPDATE inscription SET score = %s WHERE id = %s", (new_score, person_id))
    db.commit()

    flash('Score updated successfully!', 'success')
    return redirect(url_for('auth.admin'))



@auth.route('/submit_regularization', methods=['POST'])
def submit_regularization():
    cursor = db.cursor()

    if request.method == 'POST':
        # Get the user ID from the session or any other means
        user_id = session.get('user_id')  # Modify this line according to your session management

        # Get the regularization request form data
        motif1 = request.form.get('motif1')
        motif2 = request.form.get('motif2')
        motif3 = request.form.get('motif3')

        # Update the regularization_request column in the inscription table
        query = "UPDATE inscription SET regularization_request = %s WHERE id = %s"
        values = (f"{motif1}\n{motif2}\n{motif3}", user_id)
        cursor.execute(query, values)
        db.commit()

        flash('Regularization request submitted successfully!', 'success')

    return redirect(url_for('auth.reservations'))

@auth.route('/regularization', methods=['POST'])
def regularization():
    person_id = request.form.get('person_id')
    regularization_text = request.form.get('regularization_text')

    cursor = db.cursor()
    query = "UPDATE inscription SET regularization_request = %s WHERE id = %s"
    values = (regularization_text, person_id)
    cursor.execute(query, values)
    db.commit()

    flash('Regularization request submitted successfully!', 'success')
    return redirect(url_for('auth.reservations'))



@auth.route('/delete_regularization/<int:inscription_id>', methods=['POST'])
def delete_regularization(inscription_id):
    cursor = db.cursor()

    # Delete the regularization request from the database
    query = "UPDATE inscription SET regularization_request = NULL WHERE id = %s"
    cursor.execute(query, (inscription_id,))
    db.commit()

    flash('Regularization request deleted successfully!', 'success')
    return redirect(url_for('auth.admin'))










import pdfkit
from flask import render_template, make_response
import pdfkit


@auth.route('/generate_pdf', methods=['POST','GET'])
def generate_pdf():
    # Retrieve the reservation information from the request
    reservation_info = request.get_json()

    # Render the HTML template with the reservation information
    pdf_content = render_template('pdf_template.html', reservation_info=reservation_info)

    # Configure PDFkit options (optional)
    options = {
        'page-size': 'A4',
        'encoding': 'UTF-8',
    }

    # Generate the PDF file from the HTML content
    pdf_file = pdfkit.from_string(pdf_content, False, options=options)

    # Return the PDF file as a response
    response = make_response(pdf_file)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename="recu_demande.pdf"'
    return response




@auth.route('/commande', methods=['GET', 'POST'])
def commande():
    if request.method == 'POST':
        fournisseur = request.form.get('fournisseur')
        prix_totale = request.form.get('prix_totale')

        if prix_totale is None or prix_totale == '':
            flash('Please enter the total price.', category='error')
            return redirect(url_for('auth.commande'))

        try:
            prix_totale = float(prix_totale)
        except ValueError:
            flash('Invalid total price. Please enter a valid number.', category='error')
            return redirect(url_for('auth.commande'))

        # Insert the command record into the database
        cursor = db.cursor()
        query = "INSERT INTO commande (fournisseur, commande_date, prix_totale) VALUES (%s, CURDATE(), %s)"
        values = (fournisseur, prix_totale)
        cursor.execute(query, values)
        db.commit()

        
        products = []
        total_price = 0.0

        for i in range(1, 6):
            product_name = request.form.get(f'product{i}')
            product_price = request.form.get(f'price{i}')

            if product_name and product_price:
                products.append({'name': product_name, 'price': float(product_price)})
                total_price += float(product_price)

        
        html = render_template('receipt.html', fournisseur=fournisseur, products=products, total_price=total_price, configuration=config)

        
        pdf = pdfkit.from_string(html, False,configuration=config)

        
        file_path = 'C:/Users/Hamza/Desktop/receipt.pdf'
        with open(file_path, 'wb') as f:
            f.write(pdf)

        flash('Command created successfully!', category='success')
        return redirect(url_for('auth.commande'))

    return render_template('commande.html')







def generate_receipt_pdf(fournisseur, products, total_price):
    # Render the receipt HTML template with the provided data
    rendered_template = render_template(
        'receipt.html',
        fournisseur=fournisseur,
        products=products,
        total_price=total_price,
        configuration=config
    )

    # Set up PDF options
    options = {
        'page-size': 'A4',
        'encoding': 'UTF-8',
        'no-outline': None
    }

    # Generate PDF from the rendered template
    pdf = pdfkit.from_string(rendered_template, False, options=options,configuration=config)

    return pdf


@auth.route('/changepassword/<int:person_id>', methods=['POST'])
def changepassword(person_id):
    cursor = db.cursor()
    update_query = "UPDATE inscription SET password = CONCAT(nom, prenom) WHERE id = %s"
    cursor.execute(update_query, (person_id,))

    cursor.fetchall()
    db.commit()
    flash('Passwords changed successfully!', category='success')
    return redirect(url_for('auth.admin'))