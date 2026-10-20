CREATE TABLE plugins (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'error')),
    consecutive_errors INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    installed_at TEXT NOT NULL
);

CREATE TABLE plugin_migrations (
    plugin TEXT NOT NULL,
    version TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    PRIMARY KEY (plugin, version)
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX audit_log_at ON audit_log (at);
