CREATE TABLE playback_resolutions (
    episode_id INTEGER PRIMARY KEY REFERENCES episodes(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    source_url TEXT NOT NULL,
    headers_json TEXT NOT NULL DEFAULT '{}',
    mime_type TEXT NOT NULL DEFAULT '',
    allow_direct INTEGER NOT NULL DEFAULT 0 CHECK (allow_direct IN (0, 1)),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_playback_resolutions_expires
    ON playback_resolutions(expires_at);
