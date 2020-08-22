import os
import requests
import urllib.parse

import sqlite3

from flask import redirect, render_template, request, session
from functools import wraps

import time

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


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


def lookup(symbol):
    """Look up quote for symbol."""

    # Connect to database
    with sqlite3.connect('prices.db') as conn:
        conn.row_factory = sqlite3.Row

        # Query price
        rows = conn.execute(
            'SELECT price, time FROM prices WHERE symbol=:symbol',
            {'symbol': symbol}
        ).fetchall()

        # If result exists and belongs to less than a day prior
        if (exists := len(rows) == 1) and time.time() - rows[0]['time'] < 86400:
            print(time.time() - rows[0]['time'])
            return {
                'price': rows[0]['price'],
                'symbol': symbol
            }

        # Contact API
        try:
            api_key = os.environ.get("API_KEY")
            response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
            response.raise_for_status()
        except requests.RequestException:
            return None

        # Parse response
        try:
            quote = response.json()

            price = float(quote["latestPrice"])

            # Update/insert into db
            if exists:
                conn.execute(
                    'UPDATE prices SET price=?, time=? WHERE symbol=?',
                    (
                        price,
                        time.time(),
                        symbol
                    )
                )
            else:
                conn.execute(
                    'INSERT INTO prices VALUES (?, ?, ?)',
                    (
                        symbol,
                        price,
                        time.time()
                    )
                )

            return {
                "name": quote["companyName"],
                "price": price,
                "symbol": quote["symbol"]
            }
        except (KeyError, TypeError, ValueError):
            return None


def usd(value):
    """Format value as USD."""
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"-${-value:,.2f}"

# format_time dependency
days = [
    'Mon',
    'Tue',
    'Wed',
    'Thu',
    'Fri',
    'Sat',
    'Sun'
]

def format_time(t):
    """
    Change the time from seconds since EPOC to the folloeing format:
        hh:mm, wday dd/mm/yyyy
    """

    t = time.localtime(t)

    return "%02i:%02i, %s %02i/%02i/%i" % (
        t.tm_hour,
        t.tm_min,
        days[t.tm_wday],
        t.tm_mday,
        t.tm_mon,
        t.tm_year
    )
