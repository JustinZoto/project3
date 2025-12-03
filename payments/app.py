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

DB_NAME = "payments.db"
SCHEMA_FILE = "schema.sql"
db_initialized = False


def create_db():
    global db_initialized

    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys=ON")

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
    conn.execute("PRAGMA foreign_keys=ON")
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


@app.route("/add", methods=["POST"])
def add():
    auth = request.headers.get("Authorization")
    username = validate_token(auth)
    if username is None:
        return {"status": 2}

    amount_str = request.form.get("amount")
    if amount_str is None:
        return {"status": 2}

    try:
        amount = float(amount_str)
    except ValueError:
        return {"status": 2}


    if amount <= 0:
        return {"status": 2}


    try:
        conn_users = sqlite3.connect("../users/users.db")
        cur_users = conn_users.cursor()

        cur_users.execute("SELECT deposit FROM user WHERE username=?", (username,))
        row = cur_users.fetchone()
        if not row:
            conn_users.close()
            return {"status": 2}

        current_str = row[0] if row[0] is not None else "0.00"
        try:
            current = float(current_str)
        except ValueError:
            current = 0.0

        new_balance = current + amount
        new_balance_str = f"{new_balance:.2f}"

        cur_users.execute(
            "UPDATE user SET deposit=? WHERE username=?",
            (new_balance_str, username)
        )
        conn_users.commit()
        conn_users.close()

   
        conn_pay = get_db()
        cur_pay = conn_pay.cursor()
        cur_pay.execute(
            "INSERT INTO payments(username, amount) VALUES(?, ?)",
            (username, amount_str)
        )
        conn_pay.commit()
        conn_pay.close()

        return {"status": 1}
    except Exception as e:
        return {"status": 2}


@app.route("/view", methods=["GET"])
def view():
    auth = request.headers.get("Authorization")
    username = validate_token(auth)
    if username is None:
        return {"status": 2, "balance": "0.00"}

    try:
        conn_users = sqlite3.connect("../users/users.db")
        cur_users = conn_users.cursor()

        cur_users.execute("SELECT deposit FROM user WHERE username=?", (username,))
        row = cur_users.fetchone()
        conn_users.close()

        if not row:
            return {"status": 2, "balance": "0.00"}

        deposit_str = row[0] if row[0] is not None else "0.00"
        try:
            bal = float(deposit_str)
        except ValueError:
            bal = 0.0

        balance_out = f"{bal:.2f}"
        return {"status": 1, "balance": balance_out}
    except Exception as e:
        return {"status": 2, "balance": "0.00"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9003, debug=False, use_reloader=False)
