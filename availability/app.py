import sqlite3
import os
import base64
import json
import hmac
import hashlib
from flask import Flask, request

app = Flask(__name__)

DB_NAME = "availability.db"
SCHEMA_FILE = "schema.sql"
db_initialized = False

# part of this, reuses code from my Project 2 submission for CSE 380.
# Additional code come from instructor-provided checkpoint examples and lecture.

def create_db():
    global db_initialized
    conn = sqlite3.connect(DB_NAME)
    with open(SCHEMA_FILE, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    db_initialized = True

def get_db():
    global db_initialized
    if not db_initialized:
        create_db()
    return sqlite3.connect(DB_NAME)

def validate_token(token):
    try:
        if token is None:
            return None

        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature = parts

        with open("key.txt", "r") as f:
            key = f.read().strip()

        msg = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(key.encode(), msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return None

        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)
        return payload.get("username")
    except:
        return None

def extract_username(token):
    try:
        parts = token.split(".")
        payload_b64 = parts[1]
        payload_json = base64.b64decode(payload_b64 + "==").decode()
        payload = json.loads(payload_json)
        return payload["username"]
    except:
        return None

@app.route("/clear", methods=["GET", "POST"])
def clear():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    global db_initialized
    db_initialized = False
    return {"status": 1}

@app.route("/listing", methods=["POST"])
def listing():
    token = request.headers.get("Authorization")
    if not token:
        return {"status": 2}

    username = extract_username(token)
    if not username:
        return {"status": 2}

    try:
        conn_users = sqlite3.connect("../users/users.db")
        cur_users = conn_users.cursor()
        cur_users.execute(
            "SELECT driver FROM user WHERE username=?", (username,)
        )
        row = cur_users.fetchone()
        conn_users.close()

        if not row or row[0] != "True":
            return {"status": 2}
    except:
        return {"status": 2}

    data = request.form
    listingid = data.get("listingid")
    day = data.get("day")
    price = data.get("price")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO availability(listingid, username, day, price) VALUES(?,?,?,?)",
        (listingid, username, day, price)
    )
    conn.commit()
    conn.close()

    return {"status": 1}

@app.route("/search", methods=["GET"])
def search():
    auth = request.headers.get("Authorization")
    username = validate_token(auth)
    if not username:
        return {"status": 2}

    day = request.args.get("day")

    conn = get_db()
    cur = conn.cursor()
    if day:
        cur.execute(
            "SELECT listingid, price, username FROM availability WHERE day = ?",
            (day,)
        )
    else:
        cur.execute(
            "SELECT listingid, price, username FROM availability"
        )

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {"status": 1, "data": []}

    drivers = {row[2] for row in rows}
    rating_map = {}

    try:
        conn_users = sqlite3.connect("../users/users.db")
        cur_u = conn_users.cursor()
        if drivers:
            placeholders = ",".join("?" * len(drivers))
            cur_u.execute(
                f"SELECT driver, AVG(rating) "
                f"FROM ratings "
                f"WHERE driver IN ({placeholders}) "
                f"GROUP BY driver",
                tuple(drivers)
            )
            for d, avg in cur_u.fetchall():
                rating_map[d] = avg
        conn_users.close()
    except:
        pass

    data = []
    for listingid, price, driver in rows:
        avg = rating_map.get(driver, 0.0)
        data.append(
            {
                "listingid": listingid,
                "price": f"{float(price):.2f}",
                "driver": driver,
                "rating": f"{float(avg):.2f}",
            }
        )

    data.sort(key=lambda x: float(x["price"]), reverse=True)
    return {"status": 1, "data": data}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9001, debug=False, use_reloader=False)



