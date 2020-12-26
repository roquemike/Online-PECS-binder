import os.path
import requests

from flask import redirect, render_template, request, session
from gtts import gTTS
from functools import wraps

def convert_speech(text, name):
#    if not os.path.isfile("static/audio/" + text + ".mp3"):
        myobj = gTTS(text=text, lang='en')
        myobj.save("static/audio/" + name + ".mp3")
        return 0

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

