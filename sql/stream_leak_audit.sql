CREATE TABLE IF NOT EXISTS stream_leaks (stream_id TEXT PRIMARY KEY, leaked_bytes INTEGER, split_trigger INTEGER);
SELECT SUM(leaked_bytes) FROM stream_leaks;
