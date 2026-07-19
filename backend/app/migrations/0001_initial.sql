CREATE TABLE works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_work_id TEXT NOT NULL,
    series_name TEXT NOT NULL,
    series_cover TEXT NOT NULL DEFAULT '',
    series_intro TEXT NOT NULL DEFAULT '',
    detail_url TEXT NOT NULL DEFAULT '',
    episode_right_text TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    celebrities_json TEXT NOT NULL DEFAULT '[]',
    episode_count INTEGER NOT NULL DEFAULT 0 CHECK (episode_count >= 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'removed')),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (source, source_work_id)
);

CREATE INDEX idx_works_status_updated ON works(status, updated_at DESC);
CREATE INDEX idx_works_series_name ON works(series_name);

CREATE TABLE episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    source_episode_id TEXT NOT NULL,
    episode_index INTEGER NOT NULL CHECK (episode_index >= 1),
    title TEXT NOT NULL DEFAULT '',
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    updated_at TEXT NOT NULL,
    UNIQUE (work_id, source_episode_id)
);

CREATE INDEX idx_episodes_work_index ON episodes(work_id, episode_index, id);

CREATE TABLE media_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    local_path TEXT NOT NULL DEFAULT '',
    file_size INTEGER CHECK (file_size IS NULL OR file_size >= 0),
    mime_type TEXT NOT NULL DEFAULT '',
    checksum TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    resolved_url TEXT NOT NULL DEFAULT '',
    resolved_headers_json TEXT NOT NULL DEFAULT '{}',
    expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (episode_id)
);

CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'interrupted')),
    progress REAL NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 1),
    message TEXT NOT NULL DEFAULT '',
    params_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_tasks_status_created ON tasks(status, created_at);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
