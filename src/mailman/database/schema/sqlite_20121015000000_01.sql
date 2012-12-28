-- THIS FILE CONTAINS THE SQLITE3 SCHEMA MIGRATION FROM
-- 3.0b2 TO 3.0b3
--
-- AFTER 3.0b3 IS RELEASED YOU MAY NOT EDIT THIS FILE.

-- REMOVALS from the ban table.
-- REM mailing_list

-- ADDS to the ban table.
-- ADD list_id

CREATE TABLE ban_backup (
    id INTEGER NOT NULL,
    email TEXT,
    PRIMARY KEY (id)
    );

INSERT INTO ban_backup SELECT
    id, email
    FROM ban;

ALTER TABLE ban_backup ADD COLUMN list_id TEXT;
ALTER TABLE mailinglist ADD COLUMN style_name TEXT;
