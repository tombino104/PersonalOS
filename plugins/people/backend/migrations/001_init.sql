CREATE TABLE plg_people_people (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    birth_month INTEGER,
    birth_day INTEGER,
    birth_year INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK ((birth_month IS NULL) = (birth_day IS NULL)),
    CHECK (birth_month IS NULL OR birth_month BETWEEN 1 AND 12),
    CHECK (birth_day IS NULL OR birth_day BETWEEN 1 AND 31)
);
