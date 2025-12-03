import sqlite3
import os
import hashlib
import hmac
import base64
import json
from flask import Flask, request

# part of this, reuses code from my Project 2 submission for CSE 380.
# Additional code come from instructor-provided checkpoint examples and lecture

app = Flask(__name__)

DB_NAME = "reservations.db"
SCHEMA_FILE = "schema.sql"
db_initialized = False


def create_db():
    global db_initialized

    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_FILE, "r") as f:
        conn.executescript(f.read())

    conn.commit()
    conn.close()

    db_initialized = True


def get_db():
    global db_initialized

    if not db_initialized:
        create_db()

    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def validate_token(token):

    try:
        if token is None:
            return None

        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature = parts

        with open("key.txt", "r") as key_file:
            key = key_file.read().strip()

        msg = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(key.encode(), msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return None

        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        username = payload.get("username")
        return username
    except Exception as e:
        return None

@app.route("/clear", methods=["GET", "POST"])
def clear():
    global db_initialized

    try:
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)

        db_initialized = False
        return {"status": 1}

    except Exception as e:
        return {"status": 2}


@app.route("/reserve", methods=["POST"])
def reserve():

    auth = request.headers.get("Authorization")
    username = validate_token(auth)

    if not username:
        return {"status": 2}

    listingid = request.form.get("listingid")
    if not listingid:
        return {"status": 2}

    import urllib.request
    import urllib.parse

    try:
        
        url = f"http://127.0.0.1:9001/search?day=__all__&listingid={listingid}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            _ = resp.read()  

    
        conn_av = sqlite3.connect("../availability/availability.db")
        cur_av = conn_av.cursor()
        cur_av.execute(
            "SELECT day, price, username FROM availability WHERE listingid=?",
            (listingid,)
        )
        row = cur_av.fetchone()
        conn_av.close()

        if not row:
            print("[DEBUG] Listing not found")
            return {"status": 2}

        day, price_str, driver = row
        price = float(price_str)
        conn_user = sqlite3.connect("../users/users.db")
        cur_user = conn_user.cursor()
        cur_user.execute("SELECT deposit FROM user WHERE username=?", (username,))
        user_row = cur_user.fetchone()

        if not user_row:
            conn_user.close()
            return {"status": 2}

        balance = float(user_row[0])
        if balance < price:
            conn_user.close()
            return {"status": 3}
        new_balance = balance - price
        cur_user.execute(
            "UPDATE user SET deposit=? WHERE username=?",
            (f"{new_balance:.2f}", username),
        )
        conn_user.commit()
        conn_user.close()
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reservations(listingid, day, driver, renter)
            VALUES(?,?,?,?)
            """,
            (listingid, day, driver, username)
        )
        conn.commit()
        conn.close()

        return {"status": 1}

    except Exception as e:
        return {"status": 2}
@app.route("/view", methods=["GET"])
def view_reservation():
    auth = request.headers.get("Authorization")
    username = validate_token(auth)
    if not username:
        return {"status": 2}

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT reservation_id, listingid, day, driver, renter
        FROM reservations
        WHERE renter = ? OR driver = ?
        ORDER BY reservation_id DESC
        LIMIT 1
        """,
        (username, username)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return {"status": 1, "data": {}}

    reservation_id, listingid, day, driver, renter = row

    try:
        conn_av = sqlite3.connect("../availability/availability.db")
        cur_av = conn_av.cursor()
        cur_av.execute(
            "SELECT price FROM availability WHERE listingid = ?",
            (listingid,)
        )
        row_av = cur_av.fetchone()
        conn_av.close()
        price = row_av[0] if row_av else "0.00"
    except:
        price = "0.00"

    if username == renter:
        other_user = driver
        driver_to_rate = driver
        rater = username
    else:
        other_user = renter
        driver_to_rate = renter
        rater = username

    rating_val = 0.0
    try:
        conn_users = sqlite3.connect("../users/users.db")
        cur_u = conn_users.cursor()
        cur_u.execute(
            "SELECT AVG(rating) FROM ratings WHERE driver = ? AND rater = ?",
            (driver_to_rate, rater)
        )
        row_r = cur_u.fetchone()
        conn_users.close()
        if row_r and row_r[0] is not None:
            rating_val = float(row_r[0])
    except:
        pass

    return {
        "status": 1,
        "data": {
            "listingid": listingid,
            "price": f"{float(price):.2f}",
            "user": other_user,
            "rating": f"{rating_val:.2f}",
        },
    }
if __name__ == "__main__":
 
    app.run(host="0.0.0.0", port=9002, debug=False, use_reloader=False)
