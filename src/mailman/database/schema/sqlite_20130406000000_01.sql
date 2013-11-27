-- This file contains the SQLite schema migration from
-- 3.0b3 to 3.0b4
--
-- After 3.0b4 is released you may not edit this file.

-- For SQLite3 migration strategy, see
-- http://sqlite.org/faq.html#q11

-- ADD listarchiver table.

-- REMOVALs from the bounceevent table:
-- REM list_name

-- ADDs to the bounceevent table:
-- ADD list_id

-- ADDs to the mailinglist table:
-- ADD archiver_id

CREATE TABLE bounceevent_backup (
    id INTEGER NOT NULL,
    email TEXT,
    'timestamp' TIMESTAMP,
    message_id TEXT,
    context INTEGER,
    processed BOOLEAN,
    PRIMARY KEY (id)
    );

INSERT INTO bounceevent_backup SELECT
    id, email, "timestamp", message_id,
    context, processed
    FROM bounceevent;

ALTER TABLE bounceevent_backup ADD COLUMN list_id TEXT;

CREATE TABLE listarchiver (
    id INTEGER NOT NULL,
    mailing_list_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    _is_enabled BOOLEAN,
    PRIMARY KEY (id)
    );

CREATE INDEX ix_listarchiver_mailing_list_id
    ON listarchiver(mailing_list_id);
