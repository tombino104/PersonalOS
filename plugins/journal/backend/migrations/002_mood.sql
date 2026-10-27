ALTER TABLE plg_journal_entries ADD COLUMN mood INTEGER;

CREATE TRIGGER plg_journal_entries_mood_insert
BEFORE INSERT ON plg_journal_entries
WHEN NEW.mood IS NOT NULL AND (typeof(NEW.mood) != 'integer' OR NEW.mood NOT BETWEEN 1 AND 5)
BEGIN
    SELECT RAISE(ABORT, 'mood must be between 1 and 5');
END;

CREATE TRIGGER plg_journal_entries_mood_update
BEFORE UPDATE OF mood ON plg_journal_entries
WHEN NEW.mood IS NOT NULL AND (typeof(NEW.mood) != 'integer' OR NEW.mood NOT BETWEEN 1 AND 5)
BEGIN
    SELECT RAISE(ABORT, 'mood must be between 1 and 5');
END;
