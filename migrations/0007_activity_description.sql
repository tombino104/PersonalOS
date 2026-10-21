ALTER TABLE activities ADD COLUMN description TEXT CHECK (description IS NULL OR length(description) <= 300);
