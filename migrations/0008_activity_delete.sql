ALTER TABLE activities ADD COLUMN deleted_at TEXT;

DROP TRIGGER IF EXISTS activities_no_delete;

CREATE TRIGGER activities_no_delete BEFORE DELETE ON activities
WHEN EXISTS (SELECT 1 FROM completions WHERE activity_id = OLD.id)
BEGIN
    SELECT RAISE(ABORT, 'activities used in reports are never deleted');
END;
