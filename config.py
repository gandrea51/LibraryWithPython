import os

class Config: 
    SECRET_KEY = os.getenv('SECRET_KEY', 'why would I tell you my secret key?')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql://andrea:password@localhost/Biblioteca')
    SQLALCHEMY_TRACK_MODIFICATIONS = False