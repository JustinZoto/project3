import sqlite3
import os
import hashlib
import json
import hmac
import base64
from flask import Flask, request

# part of this, reuses code from my Project 2 submission for CSE 380.
# Additional code come from instructor-provided checkpoint examples and lecture slides.

app = Flask(__name__)

DB_NAME = "users.db"
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



def generate_token(username):
   
    with open("key.txt", "r") as key_file:
        secret = key_file.read().strip().encode()

    header = '{"alg": "HS256", "typ": "JWT"}'
    payload = '{"username": "' + username + '"}'

    header_b64 = base64.b64encode(header.encode()).decode()
    payload_b64 = base64.b64encode(payload.encode()).decode()

    signing_input = header_b64 + "." + payload_b64

   
    signature = hmac.new(secret, signing_input.encode(), hashlib.sha256).hexdigest()

    token = signing_input + "." + signature
    return token
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
        print("[DEBUG] TOKEN USERNAME:", username)
        return username
    except Exception as e:
        return None



@app.route("/clear", methods=["GET", "POST"])
def clear():
    global db_initialized

    try:
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
            print("[DEBUG] DB REMOVED")
        db_initialized = False
        return {"status": 1}
    except Exception as e:
        print("[DEBUG CLEAR ERROR]:", e)
        return {"status": 2}


@app.route("/create_user", methods=["POST"])
def create_user():

  
    required = ["username", "password", "salt", "deposit", "driver"]
    for field in required:
        if request.form.get(field) is None:
            return {"status": 2}

    conn = get_db()
    cur = conn.cursor()

    username = request.form["username"]
    password = request.form["password"]
    salt     = request.form["salt"]
    deposit  = request.form["deposit"]
    driver   = request.form["driver"]

   
    hash_val = hashlib.sha256((password + salt).encode()).hexdigest()

    cur.execute(
        """
        INSERT INTO user(first_name,last_name,username,email,hash,salt,driver,deposit)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            request.form.get("first_name",""),
            request.form.get("last_name",""),
            username,
            request.form.get("email_address",""),
            hash_val,
            salt,
            driver,
            deposit
        )
    )

    conn.commit()
    conn.close()
    return {"status": 1}



@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username")
    password = request.form.get("password")

    if username is None or password is None:
        return {"status": 2, "jwt": "NULL"}

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT hash, salt FROM user WHERE username=?", (username,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return {"status": 2, "jwt": "NULL"}

    stored_hash, salt = row
    if not stored_hash or not salt:
        conn.close()
        return {"status": 2, "jwt": "NULL"}

    check_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    if check_hash != stored_hash:
        conn.close()
        return {"status": 2, "jwt": "NULL"}

    conn.close()

   
    jwt_token = generate_token(username)


    return {"status": 1, "jwt": jwt_token}
def get_username_from_auth():
    auth = request.headers.get("Authorization")
    if not auth:
        return None

    try:
        parts = auth.split(".")
        if len(parts) != 3:
            return None

        payload_b64 = parts[1]
        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_json = base64.b64decode(payload_b64 + padding).decode()

        payload = json.loads(payload_json)
        return payload.get("username")

    except:
        return None
@app.route("/rate", methods=["POST"])
def rate():

    auth = request.headers.get("Authorization")
    rater = validate_token(auth)
    if not rater:
        return {"status": 2}

   
    target = request.form.get("username") or request.form.get("driver")
    rating_str = request.form.get("rating")

    if not target or rating_str is None:
        return {"status": 2}

    try:
        rating = int(rating_str)
    except ValueError:
        return {"status": 2}

 
    if rating < 1 or rating > 5:
        return {"status": 2}

    conn = get_db()
    cur = conn.cursor()


    cur.execute("SELECT username FROM user WHERE username = ?", (target,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"status": 2}

    try:
        cur.execute(
            "INSERT INTO ratings(driver, rater, rating) VALUES(?,?,?)",
            (target, rater, rating)
        )
        conn.commit()
        conn.close()
        return {"status": 1}
    except Exception as e:
        conn.close()
        return {"status": 2}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=False, use_reloader=False)


