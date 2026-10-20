CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE areas (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    position INTEGER NOT NULL,
    color_token TEXT NOT NULL
);

CREATE TABLE activities (
    id INTEGER PRIMARY KEY,
    area_id INTEGER NOT NULL REFERENCES areas (id),
    name TEXT NOT NULL,
    weight INTEGER NOT NULL CHECK (weight BETWEEN 1 AND 3),
    cadence TEXT NOT NULL DEFAULT 'daily' CHECK (cadence IN ('daily', 'weekly')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    archived_at TEXT
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    day TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    completed_at TEXT,
    editable_until TEXT NOT NULL,
    UNIQUE (user_id, day)
);

CREATE TABLE completions (
    id INTEGER PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES reports (id),
    activity_id INTEGER NOT NULL REFERENCES activities (id),
    name_at_time TEXT NOT NULL,
    weight_at_time INTEGER NOT NULL CHECK (weight_at_time BETWEEN 1 AND 3),
    area_id INTEGER NOT NULL REFERENCES areas (id),
    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    UNIQUE (report_id, activity_id)
);

CREATE TABLE daily_scores (
    report_id INTEGER NOT NULL REFERENCES reports (id),
    area_id INTEGER NOT NULL REFERENCES areas (id),
    maximum INTEGER NOT NULL CHECK (maximum >= 0),
    obtained INTEGER NOT NULL CHECK (obtained >= 0 AND obtained <= maximum),
    PRIMARY KEY (report_id, area_id)
);

CREATE TRIGGER activities_no_delete BEFORE DELETE ON activities
BEGIN
    SELECT RAISE(ABORT, 'activities are archived, never deleted');
END;

CREATE TRIGGER reports_no_delete BEFORE DELETE ON reports
BEGIN
    SELECT RAISE(ABORT, 'reports are never deleted');
END;

INSERT INTO areas (slug, name, position, color_token) VALUES
    ('physical', 'Physical', 1, 'area-physical'),
    ('discipline', 'Discipline', 2, 'area-discipline'),
    ('social', 'Social', 3, 'area-social'),
    ('intellect', 'Intellect', 4, 'area-intellect'),
    ('career', 'Career', 5, 'area-career'),
    ('mindset', 'Mindset', 6, 'area-mindset');

INSERT INTO settings (key, value) VALUES
    ('timezone', '"Europe/Rome"'),
    ('day_cutoff', '"04:00"');
