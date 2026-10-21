CREATE TABLE plg_mood_entries (
    report_id INTEGER PRIMARY KEY REFERENCES reports (id),
    day TEXT NOT NULL UNIQUE,
    value INTEGER CHECK (value BETWEEN 1 AND 5),
    note TEXT,
    updated_at TEXT NOT NULL,
    CHECK (value IS NOT NULL OR note IS NOT NULL)
);
