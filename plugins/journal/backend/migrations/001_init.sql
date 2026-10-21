CREATE TABLE plg_journal_entries (
    id INTEGER PRIMARY KEY,
    day TEXT NOT NULL,
    title TEXT,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX plg_journal_entries_day ON plg_journal_entries (day);
