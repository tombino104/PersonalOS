CREATE TABLE plg_calendar_events (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    day TEXT NOT NULL,
    time TEXT,
    category TEXT NOT NULL DEFAULT 'personal',
    notes TEXT,
    repeat TEXT NOT NULL DEFAULT 'none',
    until TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX plg_calendar_events_day ON plg_calendar_events (day);
