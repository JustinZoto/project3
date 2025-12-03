DROP TABLE IF EXISTS reservations;

CREATE TABLE reservations(
    reservation_id INTEGER PRIMARY KEY,
    listingid INTEGER,
    day TEXT,
    driver TEXT,
    renter TEXT
);