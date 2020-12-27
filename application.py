import os
import time

from cs50 import SQL

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
#import redis

from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from functions import login_required, convert_speech

#redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
#redis = redis.from_url(redis_url)

UPLOAD_FOLDER = 'static/uploads/'

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure file and folder upload
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Configure session to use filesystem (instead of signed cookies)
app.secret_key = "$H:eDQ~hSd0'y,X.]!~bSBE8%xGhP%"
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Open Database File
db = SQL("sqlite:///binder.db")
#db = SQL(os.getenv("binder.db"))

@app.route("/", methods=["GET", "POST"])
def index():

    try:
        tag_db = db.execute("SELECT DISTINCT tag FROM tag WHERE (user_id = 1 OR user_id = :user_id) ORDER BY tag = :tag ASC, tag", user_id = session['user_id'], tag="favourites")
    except:
        tag_db = db.execute("SELECT DISTINCT tag FROM tag WHERE user_id = 1 ORDER BY tag")

    tags = ["all"]
    images = []
    active_tag = "all"

    for tag in tag_db:
        tags.append(tag['tag'])

    return render_template("index.html", tags=tags, active_tag = active_tag)

@app.route("/iwant")
def iwant():
    return render_template("iwant.html")

@app.route("/firstthen")
def firstthen():
    return render_template("firstthen.html")


@app.route("/PECS")
def PECS():

    tag_db = db.execute("SELECT DISTINCT tag FROM tag ORDER BY tag")
    tags = ["all"]
    images = []
    active_tag = "all"

    for tag in tag_db:
        tags.append(tag['tag'])

    if request.args.get("cat") and request.args.get("cat") != "all":
        cat = request.args.get("cat")
        active_tag = cat

        try:
            PECS_db = db.execute("SELECT id, name, desc FROM img JOIN tag ON image_id = id WHERE tag = :tag AND (user_id = 1 OR user_id = :user_id) ORDER BY name", user_id = session['user_id'], tag = cat)
        except:
            PECS_db = db.execute("SELECT id, name, desc FROM img JOIN tag ON image_id = id WHERE (tag = :tag AND user_id = 1) ORDER BY name", tag = cat)

        for image in PECS_db:
            images.append(image)

    else:

        try:
            PECS_db = db.execute("SELECT id, name, desc FROM img JOIN tag ON image_id = id WHERE user_id = 1 OR user_id = :user_id ORDER BY tag", user_id = session['user_id'])
        except:
            PECS_db = db.execute("SELECT id, name, desc FROM img JOIN tag ON image_id = id WHERE user_id = 1 ORDER BY tag")

        for image in PECS_db:
            images.append(image)

    return render_template("PECS.html", images=images, active_tag=active_tag)

@app.route("/search")
def search():

    return render_template("search.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():

    tag_db = db.execute("SELECT DISTINCT tag FROM tag WHERE user_id = 1 ORDER BY tag")
    tags=[]
    for tag in tag_db:
        tags.append(tag['tag'])

    if request.method == "POST":
        file = request.files['file']
        desc = request.form.get('desc').lower()
        tag = request.form.get('tag').lower()
        filename = secure_filename(file.filename).lower()
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_id = db.execute("INSERT INTO img (name, desc) VALUES(:name, :desc)", name=filename, desc=desc)
        convert_speech(desc, str(image_id))
        db.execute("INSERT INTO tag (image_id, user_id, tag) VALUES(:image_id, :user_id, :tag)", image_id=image_id, user_id=session['user_id'], tag=tag)
        flash("File Uploaded Successfully")
        return render_template("upload.html", filename=filename, tags=tags, desc=desc, tag=tag)

    else:

        return render_template("upload.html", tags=tags)

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():

    if request.method == "POST":

        if request.form.get('desc'):

            img_id = int(request.form.get('id'))
            desc = request.form.get('desc').lower()
            convert_speech(desc, request.form.get('id'))
            db.execute("UPDATE img SET desc = :desc WHERE id = :img_id", desc=desc, img_id=img_id )

        if request.form.get('tag'):

            img_id = int(request.form.get('id'))
            tag = request.form.get('tag')

            db.execute("UPDATE tag SET tag = :tag WHERE image_id = :img_id", tag=tag, img_id=img_id)

        if request.form.get('del'):

            img_id = int(request.form.get('id'))

            db_img= db.execute("SELECT * FROM img WHERE id = :img_id", img_id=img_id)

            print(db_img)

            for img in db_img:
                os.remove("static/uploads/" + img['name'])
                os.remove("static/audio/" + str(img['id']) + ".mp3")

            db.execute("DELETE FROM tag WHERE image_id = :img_id", img_id=img_id)
            db.execute("DELETE FROM img WHERE id = :img_id", img_id=img_id)

            PECS_db = db.execute("SELECT id, name, desc, tag FROM img JOIN tag ON image_id = id WHERE user_id = :user_id ORDER BY id", user_id = session['user_id'])

            if len(PECS_db) < 0:
                return redirect("/edit")

        return "0"

    else:

        PECS_db = db.execute("SELECT id, name, desc, tag FROM img JOIN tag ON image_id = id WHERE user_id = :user_id AND tag != :tag ORDER BY id", user_id = session['user_id'], tag="favourites")
        tag_db = db.execute("SELECT DISTINCT tag FROM tag WHERE tag != :tag ORDER BY tag", tag = "favourites")
        tags=[]
        for tag in tag_db:
            tags.append(tag['tag'])

        return render_template("edit.html", PECS_db=PECS_db, tags=tags)

@app.route("/fave", methods=["GET", "POST"])
@login_required
def fave():

    if request.method == "POST":

        if request.form.get('fav'):
            op = request.form.get('fav')
            img_id = int(request.form.get('id'))

            if op == "add":
                db.execute("INSERT INTO tag (image_id, user_id, tag) VALUES(:img_id, :user_id, :tag)", img_id=img_id, user_id=session['user_id'], tag="favourites")
            else:
                db.execute("DELETE FROM tag WHERE user_id = :user_id AND (image_id = :img_id AND tag = :tag)", img_id=img_id, user_id=session['user_id'], tag="favourites")
            return "0"
        else:
            db.execute("DELETE FROM tag WHERE tag = :tag AND user_id = :user_id", tag="favourites", user_id=session['user_id'])
            return redirect("/fave")


    else:

        images = []
        tags = []
        PECS_db = db.execute("SELECT id, name, desc FROM img JOIN tag ON image_id = id WHERE (user_id = 1 OR user_id = :user_id) AND tag != :fav  ORDER BY name", user_id = session['user_id'], fav="favourites")
        tag_db = db.execute("SELECT id FROM img JOIN tag ON image_id = id WHERE (user_id = 1 OR user_id = :user_id) AND tag = :fav", user_id = session['user_id'], fav="favourites")

        for image in PECS_db:
            images.append(image)

        for tag in tag_db:
            tags.append(tag['id'])
        print(tags)
        return render_template("fave.html", images=images, tags=tags)

@app.route("/convert", methods=["GET", "POST"])
@login_required
def convert():

    if request.method == "POST":
        text = request.form.get('text')
        image_id = request.form.get('img_id')
        convert_speech(text, image_id)
        flash("Convertion successful...")
        return redirect("/convert")
    else:
        return render_template("convert.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        db_username = db.execute("SELECT username FROM users")
        return render_template("register.html", db_username=db_username)

    else:
        username = request.form.get("username")
        password = request.form.get("password")

        # Remember which user has logged in
        session["user_id"] = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hashed)",
        username=username, hashed=generate_password_hash(password))

        session["name"] = username

        # Redirect user to home page
        flash("Successfully Registered! Thank you for Registering!")
        return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username LIKE :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", err="error")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["name"] = rows[0]["username"]
        # Redirect user to home page
        flash("Login Successful! Welcome " + session["name"] + "!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    flash("Successfully Logged Out")
    return redirect("/")
