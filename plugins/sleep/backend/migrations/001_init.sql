CREATE TABLE plg_sleep_nights (
    day TEXT PRIMARY KEY,
    lights_off TEXT,
    woke_up TEXT,
    updated_at TEXT NOT NULL,
    CHECK (lights_off IS NOT NULL OR woke_up IS NOT NULL)
);

CREATE TABLE plg_sleep_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    target_minutes INTEGER NOT NULL CHECK (target_minutes BETWEEN 240 AND 840)
);
