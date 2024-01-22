import os
from flask import Flask, render_template, request, make_response, redirect, url_for
from random import randint
from flask_sqlalchemy import SQLAlchemy
import uuid
import hashlib
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///localhost.sqlite")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    email = db.Column(db.String, unique=True)
    secret_number = db.Column(db.Integer, unique=False)
    password = db.Column(db.String)
    session_token = db.Column(db.String)
    best_score = db.Column(db.Integer, default=0)

class Guess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    guess_number = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@app.route("/")
def index():
    session_token = request.cookies.get("session_token")

    if session_token:
        user = User.query.filter_by(session_token=session_token).first()
    else:
        user = None

    return render_template("index.html", user=user)

@app.route("/login", methods=["POST"])
def login():
    name = request.form.get("user-name")
    email = request.form.get("user-email")
    password = request.form.get("user-password")

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    secret_number = randint(1, 20)

    user = User.query.filter_by(email=email).first()

    if not user:
        user = User(name=name, email=email, secret_number=secret_number, password=hashed_password)
        db.session.add(user)
        db.session.commit()

    if hashed_password != user.password:
        return "Wrong password!"
    elif hashed_password == user.password:
        session_token = str(uuid.uuid4())
        user.session_token = session_token
        db.session.add(user)
        db.session.commit()

    response = make_response(redirect(url_for('index')))
    response.set_cookie("session_token", session_token, httponly=True, samesite='Strict')

    return response

@app.route("/logout")
def logout():
    response = make_response(redirect(url_for('index')))
    response.delete_cookie("session_token")
    return response

@app.route("/result", methods=["POST"])
def result():
    guess = int(request.form.get("guess"))
    session_token = request.cookies.get("session_token")

    user = User.query.filter_by(session_token=session_token).first()

    if guess == user.secret_number:
        
        new_secret = randint(1, 30)
        user.secret_number = new_secret
        db.session.add(user)
        db.session.commit()

        if guess > user.best_score:
            user.best_score = guess
            db.session.add(user)
            db.session.commit()

        new_guess = Guess(user_id=user.id, user_name=user.name, guess_number=guess)
        db.session.add(new_guess)
        db.session.commit()

        
        message = "Correct! The secret number is {0}".format(str(guess))



    elif guess > user.secret_number:
        message = "Your guess is not correct... try something smaller."
    elif guess < user.secret_number:
        message = "Your guess is not correct... try something bigger."

    return render_template("result.html", message=message, logout_link=url_for('logout'))

@app.route("/attempts")
def attempts():
    attempts = (
        Guess.query
        .join(User)
        .order_by(Guess.timestamp)
        .limit(10)
        .all()
     )
    return render_template("attempts.html", attempts=attempts)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(use_reloader=True)
