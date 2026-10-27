CREATE TABLE plg_mood_journal (
    entry_id INTEGER PRIMARY KEY,
    day TEXT NOT NULL,
    value INTEGER NOT NULL CHECK (value BETWEEN 1 AND 5)
);

CREATE INDEX plg_mood_journal_day ON plg_mood_journal (day);
