from datetime import date, datetime, timedelta
import math
from flask import Blueprint, flash, jsonify, render_template, redirect, send_file, url_for, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from .models import Utente, Libro, Prestito, Corso, Review
from werkzeug.security import generate_password_hash, check_password_hash
from .utils import convert, checkpassword, checkemail
from . import db

main = Blueprint('main', __name__)

@main.context_processor
def inject():
    if current_user.is_authenticated:
        return {'current_user': current_user}
    return {'current_user': None}

''' ERRORS '''
@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_message="La pagina che stai cercando non esiste."), 404

@main.app_errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_code=500, error_message="Errore interno del server. Per favore riprova più tardi."), 500

@main.app_errorhandler(403)
def forbidden(e):
    return render_template('error.html', error_code=403, error_message="Accesso negato. Non hai i permessi necessari per accedere a questa pagina."), 403

''' INTERFACE '''
@main.route('/')
def welcome():
    return render_template('welcome.html')

@main.route('/doc')
@login_required
def doc():
    return render_template('doc.html')

@main.route('/home')
@login_required
def home():
    if current_user.ruolo == 'Amministratore':
        user_count = Utente.query.filter_by(ruolo='Socio').count()
        return render_template('home.html', utente=current_user, user_count=user_count)
    else:
        return render_template('home.html', utente=current_user)

''' USER FUNCTIONS '''
@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.welcome'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        is_valid, error_message = checkemail(email)
        if not is_valid:
            flash(error_message, 'danger')
            return redirect(url_for('main.register'))
        
        password = request.form.get('password')
        is_valid, error_message = checkpassword(password)
        if not is_valid:
            flash(error_message, 'danger')
            return redirect(url_for('main.register'))
        password = generate_password_hash(password)
        
        telefono = request.form.get('telefono')
        ruolo = request.form.get('ruolo')

        user = Utente(nome=nome, email=email, password=password, telefono=telefono, ruolo=ruolo)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main.welcome'))

    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = Utente.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.home'))

    return render_template('login.html')

@main.route('/user/<int:id>')
@login_required
def uprofile(id):      
    user = db.session.get(Utente, id)  
    if not user:
        return render_template('error.html', error_message="L'utente richiesto non è stato trovato.")
    mloan, mbook = "", ""
    loans, bookings = [], []
    pr = Prestito.query.filter_by(utente_id=user.id, terminato="No").all()
    if pr:
        loans = pr
    else:
        mloan = "Non hai ancora effettuato prestiti.<br><br>Scopri la nostra selezione di titoli e approfitta delle offerte esclusive per il tuo prossimo prestito!"
    
    # Ottieni gli ID dei libri che l'utente ha già recensito
    reviewed_books_ids = db.session.query(Review.libro_id).filter_by(utente_id=user.id).all()
    reviewed_books_ids = [r.libro_id for r in reviewed_books_ids]

    return render_template('uprofile.html', user=user, mloan=mloan, loans=loans, reviewed_books_ids=reviewed_books_ids)

@main.route('/password', methods=['GET', 'POST'])
def password():
    if request.method == 'POST':
        old = request.form.get('vecchia')
        new = request.form.get('nuova')
        is_valid, error_message = checkpassword(new)
        if not is_valid:
            flash(error_message, 'danger')
            return redirect(url_for('main.password'))
        new = generate_password_hash(new)

        # Verifica che la vecchia password sia corretta
        if check_password_hash(current_user.password, old):
            current_user.password = new
            db.session.commit()
            return redirect(url_for('main.home'))
        else:
           return redirect(url_for('main.home'))

    return render_template('password.html')

@main.route('/email', methods=['GET', 'POST'])
def email():
    if request.method == 'POST':
        old = request.form.get('vecchia')
        new = request.form.get('nuova')

        is_valid, error_message = checkemail(new)
        if not is_valid:
            flash(error_message, 'danger')
            return redirect(url_for('main.email'))

        if current_user.email == old:
            current_user.email = new
            db.session.commit()
            return redirect(url_for('main.home'))
        else:
            return redirect(url_for('main.home'))

    return render_template('email.html')

@main.route('/phone', methods=['GET', 'POST'])
def phone():
    if request.method == 'POST':
        new = request.form.get('nuovo')
        current_user.telefono = new
        db.session.commit()
        return redirect(url_for('main.home'))

    return render_template('telefono.html')

@main.route('/user', methods=['GET'])
@login_required
def uindex():
    users = Utente.query.all()
    for user in users:
        user.lcount = Prestito.query.filter_by(utente_id = user.id).count()
    return render_template('uindex.html', users=users)

@main.route('/user/pdf')
@login_required
def udownload():    
    users = Utente.query.all()
    for user in users:
        user.lcount = Prestito.query.filter_by(utente_id = user.id).count()
    html = render_template('udownload.html', users=users)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

@main.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def uedit(id):
    user = db.session.get(Utente, id)
    if not user:
        return jsonify({"error": "L'utente richiesto non è stato trovato."}), 404

    if request.method == 'POST':
        user.email = request.form['email']
        user.telefono = request.form['telefono']
        user.ruolo = request.form['ruolo']
        db.session.commit()
        return redirect(url_for('main.uindex'))

    # Aggiungiamo una risposta JSON per la richiesta AJAX
    if request.method == 'GET':
        return jsonify({
            'id': user.id,
            'email': user.email,
            'telefono': user.telefono,
            'ruolo': user.ruolo
        })

@main.route('/user/<int:id>/delete', methods=['POST'])
@login_required
def udrop(id):     
    user = db.session.get(Utente, id) 
    if not user:
        return render_template('error.html', error_message="L'utente richiesto non è stato trovato.")
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('main.uindex'))

''' REVIEW FUNCTION '''
@main.route('/review/<int:id>/create', methods=['GET', 'POST'])
def rcreate(id):
    user = db.session.get(Utente, current_user.id)    
    if not user:
        return render_template('error.html', error_message="Utente inesistente.")
    book = db.session.get(Libro, id)    
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
        
    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']
        
        review = Review(rating = rating, comment = comment, libro_id = id, utente_id = user.id)
        db.session.add(review)
        db.session.commit()
        return redirect(url_for('main.uprofile', id=current_user.id))
    return render_template('rcreate.html', book=book)

@main.route('/review/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def redit(id):
    review = Review.query.get(id)
    if not review:
        return render_template('error.html', error_message="La recensione richiesta non è stata trovata.")    
    if request.method == 'POST':
        review.rating = request.form['rating']
        review.comment = request.form['comment']

        db.session.commit()        
        return redirect(url_for('main.book'))
    
    return render_template('redit.html', review=review)

''' BOOK FUNCTIONS '''
@main.route('/book')
def book():
    if current_user.is_authenticated:
        genres = Libro.query.with_entities(Libro.genere, func.count(Libro.genere)).group_by(Libro.genere).order_by(Libro.genere).all()
        tbooks = Libro.query.count()
        tviews = db.session.query(db.func.sum(Libro.viste)).scalar() or 0
        tdowns = db.session.query(db.func.sum(Libro.download)).scalar() or 0
        mbooks = Libro.query.order_by(Libro.viste.desc()).limit(5).all()
        stats = {'tbooks': tbooks, 'tviews': tviews, 'tdowns': tdowns, 'mbooks': mbooks}
        month = Libro.query.filter_by(libro_mese = "Si").first()
        return render_template('bindex.html', genres=genres, stats=stats, month=month)
    else:
        genres = Libro.query.with_entities(Libro.genere, func.count(Libro.genere)).group_by(Libro.genere).order_by(Libro.genere).all()
        books = {}
        for genre in genres:
            b = Libro.query.filter_by(genere = genre[0]).order_by(Libro.id).limit(5).all()
            books[genre[0]] = b
        return render_template('bnull.html', genres=genres, books=books)

@main.route('/group')
@login_required
def group():
    month = Libro.query.filter_by(libro_mese = 'Si').first()
    return render_template('group.html', month=month)

@main.route('/book/<int:id>/reviews')
def breviews(id):
    book = db.session.get(Libro, id)    
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    reviews = Review.query.filter_by(libro_id = id).all()
    return render_template('breviews.html', book=book, reviews=reviews)

@main.route('/book/genere', methods=['POST'])
@login_required
def bview():
    genre = request.form.get('genere')
    books = Libro.query.filter(Libro.genere.like(f'%{genre}%')).order_by(Libro.titolo).all()
    ends = {}
    reviews = {}
    for book in books:
        loans = Prestito.query.filter_by(libro_id = book.id).all()
        end = ''
        for loan in loans:
            if loan.terminato == "No":
                end = loan.rientro.strftime('%d-%m-%Y')
        ends[book.id] = end
        revs = Review.query.filter_by(libro_id = book.id).all()
        reviews[book.id] = revs
    return render_template('bview.html', books=books, genre=genre, ends=ends, reviews=reviews)

@main.route('/book/<genere>/print', methods=['GET'])
@login_required
def bprint(genere):
    books = Libro.query.filter_by(genere = genere).order_by(Libro.titolo).all()
    html = render_template('bprint.html', books=books, genre=genere)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

@main.route('/book/<int:id>/pdf')
@login_required
def bdownload(id):
    book = db.session.get(Libro, id)    
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    book.download += 1
    db.session.commit()
    html = render_template('bdownload.html', book=book)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

@main.route('/book/genere/update', methods=['POST'])
@login_required
def bedit():
    old_genere = request.form.get('old_genere')
    new_genere = request.form.get('new_genere')

    books = Libro.query.filter(Libro.genere.like(f'%{old_genere}%')).all()
    for book in books:
        book.genere = new_genere
    
    db.session.commit()
    return redirect(url_for('main.book'))

@main.route('/book/<int:id>/related')
def brelated(id):
    book = db.session.get(Libro, id)    
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    book.viste += 1
    db.session.commit()
    related_by_genre = Libro.query.filter(Libro.genere == book.genere, Libro.id != id).limit(5).all()
    related_by_author = Libro.query.filter(Libro.autore == book.autore, Libro.id != id).limit(5).all()
    books = {book.id: book for book in related_by_genre + related_by_author}.values() 
    return render_template('brelated.html', book=book, books=books)

@main.route('/book/search/titolo', methods=['POST'])
@login_required
def btitle():
    title = request.form.get('titolo')
    books = Libro.query.filter(Libro.titolo.like(f'%{title}%')).all()
    ends = {}
    reviews = {}
    for book in books:
        loans = Prestito.query.filter_by(libro_id = book.id).all()
        end = ''
        for loan in loans:
            if loan.terminato == "No":
                end = loan.rientro.strftime('%d-%m-%Y')
        ends[book.id] = end
        
        revs = Review.query.filter_by(libro_id = book.id).all()
        reviews[book.id] = revs
    return render_template('bsearch.html', books=books, hidden="Titolo", ends=ends, reviews=reviews)

@main.route('/book/search/autore', methods=['POST'])
@login_required
def bauthor():
    author = request.form.get('autore')
    books = Libro.query.filter(Libro.autore.like(f'%{author}%')).all()
    ends = {}
    reviews = {}
    for book in books:
        loans = Prestito.query.filter_by(libro_id = book.id).all()
        end = ''
        for loan in loans:
            if loan.terminato == "No":
                end = loan.rientro.strftime('%d-%m-%Y')
        ends[book.id] = end
        
        revs = Review.query.filter_by(libro_id = book.id).all()
        reviews[book.id] = revs
    return render_template('bsearch.html', books=books, hidden="Autore", ends=ends, reviews=reviews)

@main.route('/book/search/genere', methods=['POST'])
@login_required
def bgenre():
    genre = request.form.get('genere')
    books = Libro.query.filter(Libro.genere.like(f'%{genre}%')).all()
    ends = {}
    reviews = {}
    for book in books:
        loans = Prestito.query.filter_by(libro_id = book.id).all()
        end = ''
        for loan in loans:
            if loan.terminato == "No":
                end = loan.rientro.strftime('%d-%m-%Y')
        ends[book.id] = end
        
        revs = Review.query.filter_by(libro_id = book.id).all()
        reviews[book.id] = revs
    return render_template('bsearch.html', books=books, hidden="Genere", ends=ends, reviews=reviews)

@main.route('/book/<int:id>/stats')
@login_required
def bstats(id):
    book = db.session.get(Libro, id)    
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
   
    total_loans = Prestito.query.filter_by(libro_id=id).count()
    reviews = Review.query.filter_by(libro_id=id).all()
    if reviews:
        average_rating = sum(review.rating for review in reviews) / len(reviews)
        rating_distribution = {i: 0 for i in range(1, 6)}
        for review in reviews:
            rating_distribution[review.rating] += 1
    else:
        average_rating = 0
        rating_distribution = {i: 0 for i in range(1, 6)}

    loan_dates = Prestito.query.filter_by(libro_id = id).all()
    monthly_loans = {}
    for loan in loan_dates:
        month = loan.uscita.strftime('%Y-%m')
        if month not in monthly_loans:
            monthly_loans[month] = 0
        monthly_loans[month] += 1
    return render_template('bstats.html', book=book, total_loans=total_loans, average_rating=average_rating,
        rating_distribution=rating_distribution, monthly_loans=monthly_loans)

@main.route('/book/create', methods=['GET', 'POST'])
@login_required
def bcreate():
    if request.method == 'POST':
        book = Libro(
            titolo = request.form['titolo'],
            anno = request.form['anno'],
            classificazione = request.form['classificazione'],
            posizione = request.form['posizione'],
            autore = request.form['autore'],
            genere = request.form['genere'],
            collana = request.form['collana'],
            editore = request.form['editore'],
            note = request.form['note'],
            copie = request.form['copie'],
            disponibile = request.form['disponibile'],
            libro_mese = request.form['libro_mese'],
            rivista = request.form['rivista'],
            viste = 0,
            download = 0
        )

        db.session.add(book)
        db.session.commit()        
        return redirect(url_for('main.book'))
    
    return render_template('bcreate.html')

@main.route('/book/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def bookedit(id):
    book = Libro.query.get(id)
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")    
    if request.method == 'POST':
        book.titolo = request.form['titolo']
        book.anno = request.form['anno']
        book.classificazione = request.form['classificazione']
        book.posizione = request.form['posizione']
        book.autore = request.form['autore']
        book.genere = request.form['genere']
        book.collana = request.form['collana']
        book.editore = request.form['editore']
        book.note = request.form['note']
        book.copie = request.form['copie']
        book.disponibile = request.form['disponibile']
        book.libro_mese = request.form['libro_mese']
        book.rivista = request.form['rivista']
        book.viste = request.form['viste']
        book.download = request.form['download']

        db.session.commit()        
        return redirect(url_for('main.book'))
    
    return render_template('bedit.html', book=book)

@main.route('/book/<int:id>/delete', methods=['POST'])
@login_required
def bdrop(id):
    book = Libro.query.get(id)
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('main.book'))


''' LOAN FUNCTIONS '''
@main.route('/loan')
@login_required
def lindex():
    return render_template('lindex.html')

@main.route('/suggest', methods=['GET'])
def suggest():
    query = request.args.get('query', '')
    suggestions = []
    if query:
        books = Libro.query.filter(Libro.titolo.like(f'%{query}%')).all()
        suggestions = [book.titolo for book in books]
    return jsonify(suggestions) 

@main.route('/loan/create', methods=['GET', 'POST'])
@login_required
def lcreate():
    if request.method == 'POST':
        titolo = request.form.get('titolo')
        uscita = datetime.strptime(request.form.get('uscita'), '%Y-%m-%d')
        book = Libro.query.filter(Libro.titolo.like('%' + titolo + '%')).first()
        if not book:
            return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
        rientro = uscita + timedelta(days = 30 if book.rivista == 'No' else 15)
        loan = Prestito( uscita=uscita, rientro=rientro, terminato='No', restituito="No", prorogato='No', libro_id=book.id, utente_id=current_user.id)
        db.session.add(loan)
        book.copie -= 1
        if book.copie == 0:
            book.disponibile = 'No'
        db.session.commit()        
        if current_user.ruolo == "Socio":
            return redirect(url_for('main.uprofile', id=current_user.id))
        else:
            return redirect(url_for('main.lindex'))  
    
    return render_template('lcreate.html')

@main.route('/loan/<int:id>/extend')
@login_required
def lextend(id):
    loan = db.session.get(Prestito, id)    
    if not loan:
        return render_template('error.html', error_message="Il prestito richiesto non è stato trovato.")
    if loan.prorogato == "Si":
        flash('Il prestito per il libro "{}" è stato già prorogato.'.format(loan.libro.titolo), 'error')
        return redirect(url_for('main.uprofile', id=current_user.id))
    loan.rientro = loan.rientro + timedelta(days=15)
    loan.terminato = "No"
    loan.prorogato = "Si"
    db.session.commit()
    if current_user.ruolo == "Partner":
        return redirect(url_for('main.uprofile', id=current_user.id))
    else:
        return redirect(url_for('main.lindex'))  

@main.route('/loan/print')
@login_required
def lprint():
    loans = Prestito.query.filter_by(utente_id = current_user.id).all()
    html = render_template('lprint.html', loans=loans)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

@main.route('/loan/download')
@login_required
def ldownload():
    loans = Prestito.query.all()
    html = render_template('ldownload.html', loans=loans)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

@main.route('/loan/all')
@login_required
def lall():
    loans = Prestito.query.all()
    day = {}
    for loan in loans:
        if loan.terminato == "Si":
            day[loan.id] = loan.rientro.strftime('%d-%m-%Y')
        else:
            now = datetime.today().date()
            end = loan.rientro
            day[loan.id] = math.ceil((end - now).days)    
    return render_template('lall.html', loans=loans, day=day)

@main.route('/loan/<int:id>/term')
@login_required
def lterm(id):
    loan = db.session.get(Prestito, id)    
    if not loan:
        return render_template('error.html', error_message="Il prestito richiesto non è stato trovato.")
    loan.terminato = "Si"
    loan.rientro = date.today()
    loan.restituito = "Si"
    book = db.session.get(Libro, loan.libro_id)
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    book.copie += 1
    if book.copie > 0:
        book.disponibile = "Si"
    db.session.commit()    
    return redirect(url_for('main.lindex'))
    
@main.route('/loan/<int:id>/delete', methods=['POST'])
@login_required
def ldrop(id):
    loan = db.session.get(Prestito, id)    
    if not loan:
        return render_template('error.html', error_message="Il prestito richiesto non è stato trovato.")
    book = db.session.get(Libro, loan.libro_id)
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    if loan.terminato == 'No':
        book.copie += 1
        if book.copie > 0:
            book.disponibile = 'Si'
    db.session.delete(loan)
    db.session.commit()    
    return redirect(url_for('main.lindex'))
    
@main.route('/loan/expiring')
@login_required
def lexpiring():
    today = datetime.today()
    limit = today + timedelta(days=7)
    loans = Prestito.query.filter(Prestito.rientro <= limit, Prestito.rientro >= today).all()
    return render_template('lexpiring.html', loans=loans)

@main.route('/loan/history', methods=['GET', 'POST'])
def lshistory():
    if request.method == 'POST':
        id = request.form.get('id')
        history_type = request.form.get('history_type')        
        if history_type == 'book':
            return redirect(url_for('main.lbhistory', id = id))
        elif history_type == 'user':
            return redirect(url_for('main.luhistory', id = id))    
    return render_template('lshistory.html')

@main.route('/loan/history/book/<int:id>')
def lbhistory(id):
    loans = Prestito.query.filter_by(libro_id=id).all()
    book = Libro.query.get(id)    
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    return render_template('lbhistory.html', loans=loans, book=book)

@main.route('/loan/history/user/<int:id>')
def luhistory(id):
    loans = Prestito.query.filter_by(utente_id=id).all()
    user = db.session.get(Utente, id) 
    if not user:
        return render_template('error.html', error_message="L'utente richiesto non è stato trovato.")
    return render_template('luhistory.html', loans=loans, user=user)

@main.route('/loan/overdue')
def loverdue():
    loans = Prestito.query.filter(Prestito.rientro < datetime.today().date(), Prestito.restituito == "No").all()
    return render_template('loverdue.html', loans=loans)

@main.route('/loan/stats')
def lstats():
    tloans = Prestito.query.count()
    loans = Prestito.query.all()
    total_duration = sum([(loan.uscita - loan.rientro).days for loan in loans])
    average_duration = total_duration / len(loans) if loans else 0
    
    overdue_loans_count = Prestito.query.filter(Prestito.rientro < datetime.today().date(), Prestito.restituito == "No").count()
    current_loans_count = Prestito.query.filter(Prestito.rientro >= datetime.today().date()).count()

    return render_template('lstats.html', tloans=tloans, average_duration=average_duration,
        overdue_loans_count=overdue_loans_count, current_loans_count=current_loans_count)

@main.route('/loan/reports/alerts')
def lalerts():
    # Prestiti con durata insolita (es. più di 90 giorni)
    unusual_duration_loans = Prestito.query.filter((Prestito.rientro - Prestito.uscita) > timedelta(days=90)).all()
    # Prestiti non restituiti (scaduti e non terminati)
    overdue_loans = Prestito.query.filter(Prestito.rientro < datetime.today().date(), Prestito.restituito == "No").all()
    return render_template('lalert.html', unusual_duration_loans=unusual_duration_loans, overdue_loans=overdue_loans)

''' COURSE FUNCTIONS '''
@main.route('/course')
def cindex():
    if current_user.is_authenticated:
        courses = Corso.query.all()
        for course in courses:
            course.place = course.massimo - course.prenotazioni
        tview = db.session.query(db.func.sum(Corso.viste)).scalar() or 0
        mcourses = Corso.query.order_by(Corso.viste.desc()).limit(3).all()
        stats = {'tview': tview, 'mcourses': mcourses}
        return render_template('cindex.html', courses=courses, stats=stats)
    else:
        courses = Corso.query.all()        
        return render_template('cnull.html', courses=courses)

@main.route('/course/pdf')
@login_required
def cpdf():
    courses = Corso.query.all()  
    html = render_template('cpdf.html', courses=courses)
    pdf= convert(html)
    return send_file(pdf, as_attachment=True)

@main.route('/course/create', methods=['GET', 'POST'])
@login_required
def ccreate():
    if request.method == 'POST':        
        course = Corso(
            nome = request.form['nome'],
            programma = request.form['programma'],
            docente = request.form['docente'],
            giorno = request.form['giorno'],
            lezioni = request.form['lezioni'],
            note = request.form['note'],
            inizio = request.form['partenza'],
            minimo = request.form['minimo'],
            massimo = request.form['massimo'],
            prezzo = request.form['contributo'],
            tessera = request.form['tessera'],
            prenotazioni = request.form['prenotazioni'],
            iscrizioni = request.form['iscrizioni'],
            viste = 0
        )
        db.session.add(course)
        db.session.commit() 

        return redirect(url_for('main.cindex'))
    
    return render_template('ccreate.html')

@main.route('/course/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def cedit(id):
    course = db.session.get(Corso, id)
    if not course:
        return render_template('error.html', error_message="Il corso richiesto non è stato trovato.")
    if request.method == 'POST':
        course.nome = request.form['nome'],
        course.programma = request.form['programma'],
        course.docente = request.form['docente'],
        course.giorno = request.form['giorno'],
        course.lezioni = request.form['lezioni'],
        course.note = request.form['note'],
        course.partenza = request.form['partenza'],       
        course.minimo = request.form['minimo'],
        course.massimo = request.form['massimo'],
        course.contributo = request.form['contributo'],
        course.tessera = request.form['tessera'],
        course.prenotazioni = request.form['prenotazioni'],
        course.iscrizioni = request.form['iscrizioni'],
        course.viste = request.form['viste']

        db.session.commit()        
        return redirect(url_for('main.cindex'))
    
    return render_template('cedit.html', course=course)

@main.route('/course/<int:id>/delete', methods=['POST'])
@login_required
def cdrop(id):
    course = db.session.get(Corso, id)
    if not course:
        return render_template('error.html', error_message="Il corso richiesto non è stato trovato.")
    db.session.delete(course)
    db.session.commit()    
    return redirect(url_for('main.cindex'))
