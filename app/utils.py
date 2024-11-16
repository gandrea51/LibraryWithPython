from xhtml2pdf import pisa
from .models import Utente, Ratings
import tempfile, re

def check_password(password : str):
    if len(password) < 8:
        return False, "The password must contain at least 8 characters."
    elif not re.search("[a-z]", password):
        return False, "The password must contain at least one lower case letter."
    elif not re.search("[A-Z]", password):
        return False, "The password must contain at least one upper case letter."
    elif not re.search("[0-9]", password):
        return False, "The password must contain at least one number."
    elif not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): 
        return False, "The password must contain at least one symbol."
    return True, ""

def check_email(email : str):
    if Utente.query.filter_by(email=email).first():
        return False, "The email address already exist."
    return True, ""


def convert(source):
    pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pisa_status = pisa.CreatePDF(source, dest=pdf)
    if pisa_status.err:
        print("Errore durante la creazione del PDF:", pisa_status.err)
    pdf.close()
    return pdf.name

def calculate_average_rating(course_id):
    # Recupera tutte le valutazioni per il corso specificato
    ratings = Ratings.query.filter_by(corso_id=course_id).all()
    if ratings:
        avg_rating = sum([r.rating for r in ratings]) / len(ratings)
        return round(avg_rating, 2)
    return None