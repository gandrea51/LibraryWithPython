import tempfile, re
from .models import Utente
from werkzeug.security import generate_password_hash, check_password_hash
from xhtml2pdf import pisa

def checkpassword(password : str):
    if len(password) < 8:
        return False, "The password must contain at least 8 characters."
    elif not re.search("[a-z]", password):
        return False, "The password must contain at least one lower case letter."
    elif not re.search("[A-Z]", password):
        return False, "The password must contain at least one capital letter."
    elif not re.search("[0-9]", password):
        return False, "The password must contain at least one number."
    elif not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): 
        return False, "The password must contain at least one symbol."
    return True, ""

def checkemail(email : str):
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
