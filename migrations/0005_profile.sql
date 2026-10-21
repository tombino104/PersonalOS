CREATE TABLE profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    display_name TEXT,
    about TEXT,
    birth_year INTEGER CHECK (birth_year BETWEEN 1900 AND 2100),
    photo BLOB,
    photo_type TEXT,
    updated_at TEXT NOT NULL
);
