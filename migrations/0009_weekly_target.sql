ALTER TABLE activities ADD COLUMN times_per_week INTEGER
    CHECK (times_per_week IS NULL OR times_per_week BETWEEN 1 AND 7);

ALTER TABLE completions ADD COLUMN target_at_time INTEGER
    CHECK (target_at_time IS NULL OR target_at_time BETWEEN 1 AND 7);
