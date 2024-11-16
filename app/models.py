from flask_login import UserMixin
from . import db

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(100), nullable=False)
    corpo = db.Column(db.Text, nullable=False)
    msgdate = db.Column(db.DateTime, nullable=False)

class Utente(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(256))
    telefono = db.Column(db.String(100))
    ruolo = db.Column(db.String(100))
    genere = db.Column(db.String(1))

class Libro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(255), nullable=False)
    anno = db.Column(db.String(255), nullable=False)
    classificazione = db.Column(db.String(255), nullable=False)
    posizione = db.Column(db.String(255), nullable=False)
    autore = db.Column(db.String(255), nullable=False)
    genere = db.Column(db.String(255), nullable=False)
    collana = db.Column(db.String(255))
    editore = db.Column(db.String(255), nullable=False)
    note = db.Column(db.Text)
    copie = db.Column(db.Integer, nullable=False)
    disponibile = db.Column(db.String(255), nullable=False)
    libro_mese = db.Column(db.String(255), nullable=False)
    rivista = db.Column(db.String(255), nullable=False)
    viste = db.Column(db.Integer, nullable=False)
    download = db.Column(db.Integer, nullable=False)

class Corso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False, unique=True)
    programma = db.Column(db.Text, nullable=False)
    docente = db.Column(db.String(255), nullable=False)
    giorno = db.Column(db.String(255), nullable=False)
    lezioni = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text)
    inizio = db.Column(db.Date)
    minimo = db.Column(db.Integer, nullable=False)
    massimo = db.Column(db.Integer, nullable=False)
    prezzo = db.Column(db.Numeric(5,2), nullable=False)
    tessera = db.Column(db.Numeric(5,2), nullable=False)
    prenotazioni = db.Column(db.Integer, nullable=False)
    iscrizioni = db.Column(db.Integer, nullable=False)
    viste = db.Column(db.Integer, nullable=False)

class Prestito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uscita = db.Column(db.Date, nullable=False)
    rientro = db.Column(db.Date, nullable=False)
    terminato = db.Column(db.String(2), nullable=False)
    restituito = db.Column(db.String(2), nullable=False)
    prorogato = db.Column(db.String(2), nullable=False)
    libro_id = db.Column(db.BigInteger, db.ForeignKey('libro.id'), nullable=False)
    utente_id = db.Column(db.BigInteger, db.ForeignKey('utente.id'), nullable=False)

    libro = db.relationship('Libro', backref=db.backref('prestiti', lazy=True))
    utente = db.relationship('Utente', backref=db.backref('prestiti', lazy=True))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(255), nullable=False)
    bdate = db.Column(db.Date, nullable=False)
    corso_id = db.Column(db.Integer, db.ForeignKey('corso.id'), nullable=False)
    utente_id = db.Column(db.Integer, db.ForeignKey('utente.id'), nullable=False)

    corso = db.relationship('Corso', backref=db.backref('booking_course', lazy=True))
    utente = db.relationship('Utente', backref=db.backref('booking_user', lazy=True))
    
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    libro_id = db.Column(db.Integer, db.ForeignKey('libro.id'), nullable=False)
    utente_id = db.Column(db.Integer, db.ForeignKey('utente.id'), nullable=False)

    libro = db.relationship('Libro', backref=db.backref('reviews', lazy=True))
    utente = db.relationship('Utente', backref=db.backref('reviews', lazy=True))

class Ratings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    utente_id = db.Column(db.Integer, db.ForeignKey('utente.id'), nullable=False)
    corso_id = db.Column(db.Integer, db.ForeignKey('corso.id'), nullable=False)

    utente = db.relationship('Utente', backref=db.backref('ratings', lazy=True))
    corso = db.relationship('Corso', backref=db.backref('ratings', lazy=True))