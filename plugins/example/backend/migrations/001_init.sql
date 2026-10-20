CREATE TABLE plg_example_notes (
    report_id INTEGER PRIMARY KEY REFERENCES reports (id),
    text TEXT NOT NULL
);
