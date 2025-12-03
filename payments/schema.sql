DROP TABLE IF EXISTS payments;

CREATE TABLE payments(
    paymentid INTEGER PRIMARY KEY,
    username  TEXT,
    amount    TEXT
);