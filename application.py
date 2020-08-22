import os

import sqlite3
from time import time

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, lookup, usd, format_time

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

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Connect to the database
    with sqlite3.connect('finance.db') as conn:
        conn.row_factory = sqlite3.Row

        # Query cash
        result = conn.execute(
            'SELECT cash FROM users WHERE id=:id',
            {'id': session['user_id']}
        ).fetchall()
        # Store cash in session
        session['cash'] = result[0]['cash']

        # Query stock count
        result = conn.execute(
            "SELECT symbol, SUM(count) as count FROM transactions WHERE user_id=:id GROUP BY symbol",
            {'id': session['user_id']}
        )

    # Get the result as a list of dictionaries
    # As Row class does not support assignment
    rows = [dict(row) for row in result]
    # Initialize net owned
    net = session['cash']

    for row in rows:
        # Look up the symbol
        quote = lookup(row['symbol'])
        # Ensure proper result came back
        if quote == None:
            flash('Sorry, Unable to get stock prices')
            return render_template('layout.html')

        # Append price
        row['price'] = quote['price']

        # Append total price
        row['total'] = row['count'] * row['price']
        # .. add it to the net
        net += row['total']

        # Format prices
        row['price'] = usd(row['price'])
        row['total'] = usd(row['total'])

    # Cash row
    rows.append({
        'symbol': 'CASH',
        'total': usd(session['cash'])
    })

    # Total row
    rows.append({
        'total': usd(net)
    })

    # Make the template
    return render_template(
        'index.html',
        rows = rows,
        header = ['symbol', 'price', 'count', 'total']
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == 'POST':

        # Lookup the symbol
        quote = lookup(request.form.get('symbol'))

        # Ensure Proper result came back
        if quote == None:
            flash("Make sure the sumbol is valid and try again later")
            return redirect('/buy')

        # Connect to the database
        with sqlite3.connect('finance.db') as conn:
            conn.row_factory = sqlite3.Row

            cash = session['cash']

            total_price = int(request.form.get('count')) * quote['price']

            # Ensure user can afford it
            if cash < total_price:
                flash(f"That costs {usd(total_price)}")
                return redirect('/buy')

            # Make the transaction
            conn.execute(
                'INSERT INTO transactions (user_id, symbol, count, price, time) VALUES (?, ?, ?, ?, ?)',
                (
                    session['user_id'],
                    request.form.get('symbol'),
                    request.form.get('count'),
                    quote['price'],
                    time()
                )
            )

            # Update cash
            conn.execute(
                'UPDATE users SET cash=? WHERE id=?',
                (
                    cash - total_price,
                    session['user_id']
                )
            )

        # Let the user know it is done
        flash("Bought %s of %s for %s" % (
            request.form.get('count'), request.form.get('symbol'), usd(total_price)
        ))

        return redirect('/')

    else:
        return render_template(
            "buy.html",
            cash = usd(session['cash'])
        )


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Connect to the database
    with sqlite3.connect('finance.db') as conn:
        conn.row_factory = sqlite3.Row

        # Query the database
        result = conn.execute(
            'SELECT id, symbol, count, price, time FROM transactions WHERE user_id=:id',
            {'id': session['user_id']}
        )

    # Get the result as a list of dictionaries
    # As Row class does not support assignment
    rows = [dict(row) for row in result]

    # Iterate over rows
    for row in rows:
        # Format time
        row['time'] = format_time(row["time"])

        # Calculate total price
        row['total price'] = usd(
            row['count'] * row['price']
        )

        # Format id
        row['id'] = '#%04i' % (row['id'])

    # Render the table
    return render_template(
        'history_table.html',
        header = ['id', 'symbol', 'count', 'total price', 'time'],
        rows = rows,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Connect to the database
        with sqlite3.connect('finance.db') as conn:
            conn.row_factory = sqlite3.Row

            # Query database for username
            rows = conn.execute(
                "SELECT * FROM users WHERE username = :username",
                {'username': request.form.get("username")}
            ).fetchall()

        # Ensure username exists
        if len(rows) == 0:
            flash('Username does not exist')
            return render_template('login.html')

        # Ensure username and password matches
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash('Invalid username and/or password')
            return render_template('login.html')

        # Remember user's id
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # If reached with POST
    if request.method == 'POST':
        # Lookup the symbol
        qoute = lookup(request.form.get('symbol'))

        if qoute == None:
            flash("Make sure the sumbol is valid and try again later")
        else:
            flash(
                '%s: %s' % (qoute['symbol'], usd(qoute['price']))
            )

    return render_template('quote.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user"""

    if request.method == 'GET':
        return render_template('register.html')

    else:
        # Ensure username exists
        if not request.form.get('username'):
            flash("Username can't be empty")
            return render_template('register.html')

        # Ensure password & confirmation exist
        if not request.form.get('password') or not request.form.get('confirmation'):
            flash("A password can't be empty")
            return render_template('register.html')

        # Ensure password matches confirmation
        if request.form.get('password') != request.form.get('confirmation'):
            flash("Passwords must match")
            return render_template('register.html')

        # Connect to the database
        with sqlite3.connect('finance.db') as conn:
            # Check if the username is already in the database
            rows = conn.execute(
                "SELECT id FROM users WHERE username=?",
                (request.form.get('username'),)
            ).fetchall()
            # .. if it does
            if len(rows) != 0:
                flash("Username already used")
                return render_template('register.html')

            # Insert the user
            conn.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                (
                    request.form.get('username'),
                    generate_password_hash(request.form.get('password'))
                )
            )

        return redirect("/login")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == 'POST':

        # Lookup the symbol
        quote = lookup(request.form.get('symbol'))

        # Ensure Proper result came back
        if quote == None:
            flash("Make sure the sumbol is valid and try again later")
            return render_template('buy.html')

        # Connect to the database
        with sqlite3.connect('finance.db') as conn:
            conn.row_factory = sqlite3.Row

            # Get shares count
            rows = conn.execute(
                'SELECT SUM(count) as sum FROM transactions WHERE user_id=? AND SYMBOL=?',
                (
                    session['user_id'],
                    request.form.get('symbol')
                )
            ).fetchall()
            owned = y if (y := rows[0]['sum']) != None else 0

            # Ensure user has enough shares
            if int(request.form.get('count')) > owned:
                flash(f"You do not own {request.form.get('count')} shares")
                return render_template('sell.html')

            # Make the transaction
            conn.execute(
                'INSERT INTO transactions (user_id, symbol, count, price, time) VALUES (?, ?, ?, ?, ?)',
                (
                    session['user_id'],
                    request.form.get('symbol'),
                    -int(request.form.get('count')),
                    quote['price'],
                    time()
                )
            )

            total_price = int(request.form.get('count')) * quote['price']

            # Update cash
            conn.execute(
                'UPDATE users SET cash = ? WHERE id = ?',
                (
                    session['cash'] + total_price,
                    session['user_id']
                )
            )

        # Let the user know it is done
        flash("Sold %s of %s for %s" % (
            request.form.get('count'), request.form.get('symbol'), usd(total_price)
        ))

    return render_template('sell.html')


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
