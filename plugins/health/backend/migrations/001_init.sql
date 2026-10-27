CREATE TABLE plg_health_days (
    day TEXT PRIMARY KEY,
    steps INTEGER NOT NULL CHECK (steps BETWEEN 0 AND 200000),
    updated_at TEXT NOT NULL
);
