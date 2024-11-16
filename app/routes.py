from flask import Blueprint, flash, jsonify, render_template, redirect, send_file, url_for, request
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from .models import Utente, Libro, Corso, Prestito, Booking, Review, Ratings, Message
from .utils import check_email, check_password, convert
from . import db
from datetime import date, datetime, timedelta
import math

main = Blueprint('main', __name__)

@main.context_processor
def inject():
    if current_user.is_authenticated:
        return {'current_user': current_user}
    return {'current_user': None}

# Sezione Errori
@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_message='La pagina che stai cercando non esiste.'), 404

@main.app_errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_code=500, error_message='Errore interno del server. Per favore riprova più tardi.'), 500

@main.app_errorhandler(403)
def forbidden(e):
    return render_template('error.html', error_code=403, error_message='Accesso negato. Non hai i permessi necessari per accedere a questa pagina.'), 403

# Welcome page: Pagina di Benvenuto
@main.route('/', methods=["GET"])
def welcome():
    return render_template('welcome.html')

# Pagina informatica e per i contatti
@main.route('/doc', methods=["GET"])
def doc():
    return render_template('doc.html')

# Home page una volta loggato
@main.route('/home', methods=["GET"])
@login_required
def home():
    messages = Message.query.order_by(Message.msgdate.desc()).limit(5)
    if current_user.ruolo == "Manager":
        user_count = Utente.query.filter_by(ruolo='Partner').count()
        return render_template('home.html', user=current_user, user_count=user_count, messages=messages)
    else:
        return render_template('home.html', user=current_user, messages=messages)
    
# Registrazione
@main.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    nome = request.form.get('nome')
    genere = request.form.get('genere')
    email = request.form.get('email')
    is_valid, error_message = check_email(email)
    if not is_valid:
        flash(error_message, 'danger')
        return redirect(url_for('main.register'))
    password = request.form.get('password')
    is_valid, error_message = check_password(password)
    if not is_valid:
        flash(error_message, 'danger')
        return redirect(url_for('main.register'))
    phone = request.form.get('telefono')
    role = request.form.get('ruolo')

    password = generate_password_hash(password)
    user = Utente(nome=nome, email=email, password=password, telefono=phone, ruolo=role, genere=genere)
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('main.welcome'))

# Login
@main.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    email = request.form.get('email')
    password = request.fore.get('password')

    user = Utente.query.filter_by(email=email).first()
    if user and check_password_hash(Utente.password, password):
        login_user(user)
        return redirect(url_for('main.home'))
    
# Logout
@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main_welcome'))

# MY profile
@main.route('/user/<int:id>', methods=["GET"])
@login_required
def uprofile(id):
    user = db.session.get(Utente, id)
    mloan, mbook = "", ""
    if not user:
        return render_template('error.html', error_message="L'utente richiesto non è stato trovato.")
        
    if not Prestito.query.filter_by(utente_id=user.id, terminato="No")*all():
        mloan = "Non hai ancora effettuato prestiti.<br><br>Scopri la nostra selezione di titoli e approfitta delle offerte esclusive per il tuo prossimo progetto!"
    
    if not Booking.query.filter_by(utente_id=user.id).all():
        mbook = "Non hai ancora effettuato prenotazioni.<br><br>Erplora i corsi disponibili e prenota subito le tue lezioni per approfittare delle offerte speciali!"

    loans = Prestito.query.filter_by(utente_id=user.id, terminato="No").all()
    bookings = Booking.query.filter_by(utente_id=user.id).all()
    return render_template('uprofile.html', user=user, mloan=mloan, loans=loans, booKings=bookings, mbook=mbook)

# Reset della Passwopd
@main.route('/password', methods=["GET" , "POST"])
def password():
    if request.method == 'GET':
        return render_template('password.html')
    
    old = request.form.get('vecchia')
    new = request.form.get('nuova')
    is_valid, error_message = check_password(new)
    if not is_valid:
        flash(error_message, 'danger')
        return redirect(url_for('main.password'))
    
    if not check_password_hash(current_user.password, old):
        return redirect(url_for('main.password'))
    
    new = generate_password_hash(new)
    current_user.password = new
    db.session.commit()
    return redirect(url_for('main.home'))

# Reset della Email
@main.route('/email', methods=["GET", "POST"])
def email():
    if request.method == 'GET':
        return render_template('email.html')
    
    old = request.form.get('vecchia')
    new = request.form.get('nuova')
    is_valid, error_message = check_email(new)
    if not is_valid:
        flash(error_message, 'danger')
        return redirect(url_for('main.email'))

    if not current_user.email == old:
        return redirect(url_for('main.email'))
    
    current_user.email = new
    db.session.commit()
    return redirect(url_for('main.home'))

# Reset del Telefono
@main.route('/phone', methods=["GET", "POST"])
def phone():
    if request.method == 'GET':
        return render_template('phone.html')
    
    old = request.form.get('vecchio')
    new = request.form.get('nuovo')

    if not current_user.telefono == old:
        return redirect(url_for('main.phone'))
    
    current_user.telefono = new
    db.session.commit()
    return redirect(url_for('main.home'))

# Tutti gli utenti
@main.route('/user', methods=["GET"])
@login_required
def uindex():
    users = Utente.query.all()
    for user in users:
        user.lcount = Prestito.query.filter_by(utente_id=user.id).count()
        user.bcount = Booking.query.filter_by(utente_id=user.id).count()
    return render_template('uindex.html', users=users)

# Modifica di un utente
@main.route('/user/<int:id>/edit', methods=["GET", "POST"])
@login_required
def uedit(id):
    user = db.session.get(Utente, id)
    if not user:
        return jsonify({"error": "L'utente richiesto non è stato trovato."}), 404

    if request.method == 'POST':
        user.genere = request.form['genere']
        user.email = request.form['email']
        user.telefono = request.form['telefono']
        user.ruolo = request.form['ruolo']
        db.session.commit()
        return redirect(url_for('main.uindex'))

    if request.method == 'GET':
        return jsonify({
            'id': user.id,
            'genere': user.genere,
            'email': user.email,
            'telefono': user.telefono,
            'ruolo': user.ruolo
        })

# Drop di un utente 
@main.route('/user/<int:id>/delete', methods=["POST"])
@login_required
def udrop(id):
    user = db.session.get(Utente, id) 
    if not user:
        return render_template('error.html', error_message="L'utente richiesto non è stato trovato.")
    
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('main.uindex'))

# Utenti in PDF
@main.route('/user/print', methods=["GET"])
@login_required
def uprint():
    users = Utente.query.all()
    for user in users:
        user.lcount = Prestito.query.filter_by(utente_id=user.id).count()
        user.bcount = Booking.query.filter_by(utente_id=user.id).count()
    html = render_template('uprint.html', users=users)
    pdf = convert(html)
    return send_file(pdf, as_attachment=True)

# Tutti i messaggi
@main.route('/message', methods=["GET"])
@login_required
def mindex():
    messages = Message.query.order_by(Message.msgdate.desc()).all()
    return render_template('mindex.html', messages=messages)

# Crea un nuovo messaggio
@main.route('/message/create', methods=["GET", "POST"])
@login_required
def mcreate():
    if request.method == 'GET':
        return render_template('mcreate.html')
    
    titolo = request.form['titolo']
    corpo = request.form['corpo']
    msgdate = date.today()
    msg = Message(titolo=titolo, corpo=corpo, msgdate=msgdate)
    
    db.session.add(msg)
    db.session.commit()
    return redirect(url_for('main.home'))
    
# Edit un messaggio
@main.route('/message/<int:id>/edit', methods=["GET", "POST"])
@login_required
def medit(id):
    message = db.session.get(Message, id)
    if not message:
        return render_template('error.html', error_message="Il messaggio richiesto non è stato trovato.") 
    
    if request.method == 'POST':
        message.titolo = request.form['titolo']
        message.corpo = request.form['corpo']
        message.msgdate = request.form['msgdate']
        db.session.commit()
        return redirect(url_for('main.mindex'))

    if request.method == 'GET':
        return jsonify({
            'id': message.id,
            'titolo': message.titolo,
            'corpo': message.corpo,
            'msgdate': message.msgdate
        })
    
# Elimina un messaggio
@main.route('/message/<int:id>/delete', methods=["POST"])
@login_required
def mdrop(id):
    message = db.session.get(Message, id)
    if not message:
        return render_template('error.html', error_message="Il messaggio richiesto non è stato trovato.")
    
    db.session.delete(message)
    db.session.commit()
    return redirect(url_for('main.mindex'))

# Index dei libri
@main.route('/book', methods=["GET"])
def book():
    if current_user.is_authenticated:
        genres = Libro.query.with_entities(Libro.genere, func.count(Libro.genere)).group_by(Libro.genere).order_by(Libro.genere).all()
        # Statistiche
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

# Reading Group
@main.route('/group', methods=["GET"])
@login_required
def group():
    month = Libro.query.filter_by(libro_mese='Si').first()
    return render_template('group.html', month=month)

# Book of a certain Genre
@main.route('/book/genere', methods=["POST"])
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

# Book of Genre Print
@main.route('/book/<genere>/print', methods=["GET"])
@login_required
def bprint(genere):
    books = Libro.query.filter_by(genere=genere).order_by(Libro.titolo).all()
    html = render_template('bprint.html', books=books, genre=genere)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

# Book Scheda
@main.route('/book/<int:id>/download', methods=["GET"])
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

# Book related
@main.route('/book/<int:id>/related', methods=["GET"])
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

# Book Stats
@main.route('/book/<int:id>/stats', methods=["GET"])
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

# Area manager per i libri
@main.route('/book/manager', methods=["GET"])
@login_required
def bmanager():
    books = Libro.query.all()
    return render_template('bmanager.html', books=books)

# Book Create
@main.route('/book/create', methods=["GET", "POST"])
@login_required
def bcreate():
    if request.method == 'GET':
        return render_template('bcreate.html')
    
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

# Book edit
@main.route('/book/<int:id>/edit', methods=["GET", "POST"])
@login_required
def bedit(id):
    book = Libro.query.get(id)
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")    
    
    if request.method == 'GET':
        return render_template('bedit.html', book=book)
    
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
    
# Book drop
@main.route('/book/<int:id>/delete', methods=["POST"])
@login_required
def bdrop(id):
    book = Libro.query.get(id)
    
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('main.book'))

# Ricerche 
@main.route('/book/search/titolo', methods=["POST"])
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

@main.route('/book/search/autore', methods=["POST"])
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

@main.route('/book/search/genere', methods=["POST"])
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

# Area manager per i prestiti
@main.route('/loan', methods=["GET"])
@login_required
def lindex():
    return render_template('lindex.html')

# Suggerimento titoli
@main.route('/suggest', methods=["GET"])
def suggest():
    query = request.args.get('query', '')
    suggestions = []
    
    if query:
        books = Libro.query.filter(Libro.titolo.like(f'%{query}%')).all()
        suggestions = [book.titolo for book in books]
    return jsonify(suggestions) 

# Creazione del prestito
@main.route('/loan/create', methods=["GET", "POST"])
@login_required
def lcreate():
    if request.method == 'GET':
        return render_template('lcreate.html')
    
    titolo = request.form.get('titolo')
    uscita = datetime.strptime(request.form.get('uscita'), '%Y-%m-%d')
    
    book = Libro.query.filter(Libro.titolo.like('%' + titolo + '%')).first()
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    
    rientro = uscita + timedelta(days = 30 if book.rivista == 'No' else 15)
    
    loan = Prestito(uscita=uscita, rientro=rientro, terminato='No', restituito="No", prorogato='No', libro_id=book.id, utente_id=current_user.id)
    db.session.add(loan)
    
    book.copie -= 1
    if book.copie == 0:
        book.disponibile = 'No'
    db.session.commit()        
    
    if current_user.ruolo == "Manager":
        return redirect(url_for('main.lindex')) 
    return redirect(url_for('main.uprofile', id=current_user.id))

# Tutti i prestiti
@main.route('/loan/all', methods=["GET"])
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

# Prestiti in Scadenza
@main.route('/loan/expiring', methods=["GET"])
@login_required
def lexpiring():
    today = datetime.today()
    limit = today + timedelta(days=7)
    loans = Prestito.query.filter(Prestito.rientro <= limit, Prestito.rientro >= today).all()
    
    return render_template('lexpiring.html', loans=loans)

# Seleziona la cronologia
@main.route('/loan/history', methods=["GET", "POST"])
def lshistory():
    if request.method == 'GET':
        return render_template('lshistory.html')
    
    id = request.form.get('id')
    history_type = request.form.get('history_type')        
    
    if history_type == 'book':
        return redirect(url_for('main.lbhistory', id = id))
    return redirect(url_for('main.luhistory', id = id))    
    
# Cronologia per Libro
@main.route('/loan/history/book/<int:id>', methods=["GET"])
def lbhistory(id):
    book = Libro.query.get(id)    
    if not book:
        return render_template('error.html', error_message="Il libro richiesto non è stato trovato.")
    loans = Prestito.query.filter_by(libro_id=id).all()

    return render_template('lbhistory.html', loans=loans, book=book)

# Cronologia per Utente
@main.route('/loan/history/user/<int:id>', methods=["GET"])
def luhistory(id):
    user = db.session.get(Utente, id) 
    if not user:
        return render_template('error.html', error_message="L'utente richiesto non è stato trovato.")
    loans = Prestito.query.filter_by(utente_id=id).all()
    
    return render_template('luhistory.html', loans=loans, user=user)

# Prestiti non rientrati
@main.route('/loan/overdue', methods=["GET"])
def loverdue():
    loans = Prestito.query.filter(Prestito.rientro < datetime.today().date(), Prestito.restituito == "No").all()
    
    return render_template('loverdue.html', loans=loans)

# Loan Stats
@main.route('/loan/stats', methods=["GET"])
def lstats():
    tloans = Prestito.query.count()
    loans = Prestito.query.all()
    total_duration = sum([(loan.uscita - loan.rientro).days for loan in loans])
    average_duration = total_duration / len(loans) if loans else 0
    
    overdue_loans_count = Prestito.query.filter(Prestito.rientro < datetime.today().date(), Prestito.restituito == "No").count()
    current_loans_count = Prestito.query.filter(Prestito.rientro >= datetime.today().date()).count()

    return render_template('lstats.html', tloans=tloans, average_duration=average_duration,
        overdue_loans_count=overdue_loans_count, current_loans_count=current_loans_count)

# Loan strani
@main.route('/loan/reports/alerts', methods=["GET"])
def lalerts():
    # Prestiti con durata insolita (es. più di 90 giorni)
    unusual_duration_loans = Prestito.query.filter((Prestito.rientro - Prestito.uscita) > timedelta(days=90)).all()
    # Prestiti non restituiti (scaduti e non terminati)
    overdue_loans = Prestito.query.filter(Prestito.rientro < datetime.today().date(), Prestito.restituito == "No").all()
    
    return render_template('lalert.html', unusual_duration_loans=unusual_duration_loans, overdue_loans=overdue_loans)

# Terminazione
@main.route('/loan/<int:id>/term', methods=["GET"])
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

# Drop loan 
@main.route('/loan/<int:id>/delete', methods=["POST"])
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

# Extension
@main.route('/loan/<int:id>/extend', methods=["GET"])
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
    return redirect(url_for('main.lindex'))  

# Print my loans
@main.route('/loan/print', methods=["GET"])
@login_required
def lprint():
    loans = Prestito.query.filter_by(utente_id = current_user.id).all()
    html = render_template('lprint.html', loans=loans)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

# Print all loans
@main.route('/loan/download', methods=["GET"])
@login_required
def ldownload():
    loans = Prestito.query.all()
    html = render_template('ldownload.html', loans=loans)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

# Course
@main.route('/course', methods=["GET"])
def cindex():
    if current_user.is_authenticated:
        courses = Corso.query.all()
        for course in courses:
            course.place = course.massimo - course.prenotazioni
        tview = db.session.query(db.func.sum(Corso.viste)).scalar() or 0
        mcourses = Corso.query.order_by(Corso.viste.desc()).limit(3).all()
        stats = {'tview': tview, 'mcourses': mcourses}        
        ratings = Ratings.query.filter_by(corso_id = course.id).all()
       
        return render_template('cindex.html', courses=courses, stats=stats, ratings=ratings)
    else:
        courses = Corso.query.all()        
        
        return render_template('cnull.html', courses=courses)

# Area manager per i corsi
@main.route('/course/manager', methods=["GET"])
@login_required
def cmanager():
    courses = Corso.query.all()
    return render_template('cmanager.html', courses=courses)

# Create course
@main.route('/course/create', methods=["GET", "POST"])
@login_required
def ccreate():
    if request.method == 'GET':   
        return render_template('ccreate.html')     
    course = Corso(
        nome = request.form['nome'],
        programma = request.form['programma'],
        docente = request.form['docente'],
        giorno = request.form['giorno'],
        lezioni = request.form['lezioni'],
        note = request.form['note'],
        inizio = request.form['inizio'],
        minimo = request.form['minimo'],
        massimo = request.form['massimo'],
        prezzo = request.form['prezzo'],
        tessera = request.form['tessera'],
        prenotazioni = 0,
        iscrizioni = 0,
        viste = 0
    )
    db.session.add(course)
    db.session.commit() 

    return redirect(url_for('main.cindex'))

# Corse edit    
@main.route('/course/<int:id>/edit', methods=["GET", "POST"])
@login_required
def cedit(id):
    course = db.session.get(Corso, id)
    if not course:
        return render_template('error.html', error_message="Il corso richiesto non è stato trovato.")
    
    if request.method == 'GET':
        return render_template('cedit.html', course=course)
    
    course.nome = request.form['nome'],
    course.programma = request.form['programma'],
    course.docente = request.form['docente'],
    course.giorno = request.form['giorno'],
    course.lezioni = request.form['lezioni'],
    course.note = request.form['note'],
    course.inizio = request.form['inizio'],       
    course.minimo = request.form['minimo'],
    course.massimo = request.form['massimo'],
    course.prezzo = request.form['prezzo'],
    course.tessera = request.form['tessera'],
    course.prenotazioni = request.form['prenotazioni'],
    course.iscrizioni = request.form['iscrizioni'],
    course.viste = request.form['viste']

    db.session.commit()
    return redirect(url_for('main.cindex'))
    
# Cours edrop
@main.route('/course/<int:id>/delete', methods=["POST"])
@login_required
def cdrop(id):
    course = db.session.get(Corso, id)
    if not course:
        return render_template('error.html', error_message="Il corso richiesto non è stato trovato.")
    
    db.session.delete(course)
    db.session.commit()    
    return redirect(url_for('main.cindex'))

# Print the course
@main.route('/course/print', methods=["GET"])
@login_required
def cprint():
    courses = Corso.query.all()  
    html = render_template('cprint.html', courses=courses)
    pdf= convert(html)
    return send_file(pdf, as_attachment=True)

# Booking
@main.route('/booking', methods=["GET"])
@login_required
def pindex():
    return render_template('pindex.html')

# Suggerimento nomi
@main.route('/suggests', methods=["GET"])
def suggests():
    query = request.args.get('query', '')
    suggestions = []
    
    if query:
        courses = Corso.query.filter(Corso.nome.like(f'%{query}%')).all()
        suggestions = [course.nome for course in courses]
    
    return jsonify(suggestions) 

# Booking create
@main.route('/booking/create', methods=["GET", "POST"])
@login_required
def pcreate():
    if request.method == 'GET':
        return render_template('pcreate.html')
    
    name = request.form.get('name')
    course = Corso.query.filter(Corso.nome.like('%' + name + '%')).first()
    if not course:
        return render_template('error.html', error_message="Il corso richiesto non è stato trovato.")
    
    booking = Booking(state="Pending", bdate=date.today(), corso_id=course.id, utente_id=current_user.id)
    db.session.add(booking)
    
    course.prenotazioni += 1
    db.session.commit()        
    
    if current_user.ruolo == "Manager":
        return redirect(url_for('main.pindex'))  
    return redirect(url_for('main.uprofile', id=current_user.id))

# Print my booking     
@main.route('/booking/print', methods=["GET"])
@login_required
def pprint():
    bookings = Booking.query.filter_by(utente_id=current_user.id).all()
    html = render_template('pprint.html', bookings=bookings)
    pdf = convert(html)    
    return send_file(pdf, as_attachment=True)

# Booking confirm  
@main.route('/booking/<int:id>/confirm', methods=["GET"])
@login_required
def pconfirm(id):
    booking = db.session.get(Booking, id)
    
    if not booking:
        return render_template('error.html', error_message="La prenotazione richiesta non è stata trovata.")
    
    booking.state = "Confirmed"
    db.session.commit()    
    
    course = db.session.get(Corso, booking.corso_id)
    if not course:
        return render_template('error.html', error_message="Il corso richiesto non è stato trovato.")
    
    course.prenotazioni -= 1
    course.iscrizioni += 1
    db.session.commit()    
    return redirect(url_for('main.pindex'))

# Booking reject
@main.route('/booking/<int:id>/reject', methods=["GET"])
def preject(id):
    booking = db.session.get(Booking, id)
    if not booking:
        return render_template('error.html', error_message="La prenotazione richiesta non è stata trovata.")

    booking.state = 'Rejected'
    
    course = db.session.get(Corso, booking.corso_id)
    if not course:
        return render_template('error.html', error_message="Il corso richiesto non è stato trovato.")
    course.prenotazioni -= 1
    db.session.commit()
    
    return redirect(url_for('main.pindex'))

# Booking payments
@main.route('/booking/payments', methods=["GET"])
def ppayments():
    bookings = Booking.query.all()
    payments = []

    for booking in bookings:
        corso = booking.corso
        utente = booking.utente

        # Simuliamo uno stato di pagamento in base a condizioni arbitrarie
        # Potresti avere un campo separato nella tabella per lo stato del pagamento
        has_paid = "Sì" if booking.state == "Confirmed" else "No"

        payments.append({
            'utente': utente.nome,
            'email': utente.email,
            'corso': corso.nome,
            'prezzo': corso.prezzo,
            'tessera': corso.tessera,
            'data_prenotazione': booking.bdate,
            'pagato': has_paid
        })
        
    return render_template('ppayments.html', payments=payments)

# Bookking pending
@main.route('/booking/pending', methods=["GET"])
def ppending():
    # Ottieni le prenotazioni in attesa (stato = 'in attesa')
    pending_bookings = Booking.query.filter_by(state='Pending').all()

    return render_template('ppending.html', bookings=pending_bookings)

@main.route('/booking/stats', methods=["GET"])
def pstats():
    corsi = Corso.query.all()
    total_bookings = Booking.query.count()  # Numero totale di prenotazioni
    stats = []

    for corso in corsi:
        bookings_for_course = Booking.query.filter_by(corso_id=corso.id).count()  # Prenotazioni per corso
        fill_rate = (corso.iscrizioni / corso.massimo) * 100  # Percentuale di riempimento
        stats.append({
            'corso': corso.nome,
            'prenotazioni': bookings_for_course,
            'iscrizioni': corso.iscrizioni,
            'posti_max': corso.massimo,
            'riempimento': round(fill_rate, 2),  # Arrotonda al 2 decimali
            'viste': corso.viste  # Numero di visualizzazioni
        })

    return render_template('pstats.html', stats=stats, total_bookings=total_bookings)

@main.route('/booking/users', methods=["GET"])
def pusers():
    users = Utente.query.all()
    
    return render_template('pusers.html', users=users)

@main.route('/booking/user', methods=["POST"])
def puser():
    user_email = request.form.get('user')  # Qui stai ricevendo l'email o un campo simile
    user = Utente.query.filter_by(email=user_email).first()  # Cerca l'utente tramite email
    bookings = Booking.query.filter_by(utente_id=user.id).all()  # Cerca tutte le prenotazioni per l'ID dell'utente
    
    return render_template('puser.html', user=user, bookings=bookings)
