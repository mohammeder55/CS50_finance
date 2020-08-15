import os

import sqlite3

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, format_time

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


# Shows the profile of owned stocks
@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Connect to the database
    with sqlite3.connect('finance.db') as conn:
        conn.row_factory = sqlite3.Row

        # TODO: Change the statement
        result = conn.execute(
            "SELECT id, cash FROM users"
        )

    return render_template(
        'index_table.html',
        rows = result,
        header = ['id', 'cash'],
        title = 'Home'
    )


# Let's the user buy stocks
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # Get the stock's price
    # Check if the user can afford it

    # Update stocks table
    # Update transactions table
    # Update User's cash

    return apology("TODO")


# Shows the history of transactions
@app.route("/history")
# @login_required
def history():
    """Show history of transactions"""

    rows = [
        {'ID': 5, 'Symbol': 'AAPL', 'Shares': 5, 'Price': 50, 'Time': 1597530727.044325},
        {'ID': 652, 'Symbol': 'AAPL', 'Shares': -4, 'Price': 51, 'Time': 1597501907.1454823}
    ]

    for row in rows:
        row['Time'] = format_time(row["Time"])

    return render_template(
        'history_table.html',
        # header = ['ID', 'Symbol', 'Shares', 'Amount', 'Time'],
        header = ['ID', 'Symbol', 'Shares', 'Price', 'Time'],
        rows = rows,
        title = 'History'
    )


# Let's the user sign in
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        print("-"*50)

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Connect to the database
        with sqlite3.connect('finance.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query database for username
            rows = cursor.execute(
                "SELECT * FROM users WHERE username = :username",
                {'username': request.form.get("username")}
            )

            # Get the first row
            row = rows.fetchone()


        # Ensure username exists and password is correct
        if row == None or not check_password_hash(row["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = row["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


# Let's the user log out
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


# Give stock quote
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == 'GET':
        # Serve the page
        return render_template('quote.html')

    else:
        # Look up the price
        pass

    return apology("TODO")


# Register a new user
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    else:
        print("|"*50)

        # Ensure username exists
        if not request.form.get('username'):
            return apology('Username can\'t be empty', 902)

        # Ensure password & confirmation exist
        if not request.form.get('password') or not request.form.get('confirmation'):
            return apology('a password can\'t be empty', 902)

        # Ensure password matches confirmation
        if request.form.get('password') != request.form.get('confirmation'):
            return apology("PASSWORDS MUST MATCH!!", 901)

        # Connect to the database
        with sqlite3.connect('finance.db') as conn:
            cursor = conn.cursor()

            # Check if the username is already in the database
            result = cursor.execute(
                "SELECT id FROM users WHERE username=?",
                (request.form.get('username'),)
            )
            # .. if it does
            if result.fetchone() != None:
                return apology("username already used", 903)

            # Insert the user
            result = cursor.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                (
                    request.form.get('username'),
                    generate_password_hash(request.form.get('password'))
                )
            )

        print(result)

        return redirect("/")

    # return apology("TODO")


# Sell stocks
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Query database for owned stocks of that symbol

    # Ensure the user don't own less than what he's selling

    # Update stocks table
    # Update transactions table
    # Update user's cash

    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
