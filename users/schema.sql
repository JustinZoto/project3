DROP TABLE IF EXISTS user;

CREATE TABLE user(
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    username TEXT UNIQUE,
    email TEXT,
    hash TEXT,
    salt TEXT,
    driver BOOLEAN,
    deposit TEXT
);
DROP TABLE IF EXISTS ratings;

CREATE TABLE ratings(
    driver TEXT,
    rater TEXT,
    rating INTEGER
);