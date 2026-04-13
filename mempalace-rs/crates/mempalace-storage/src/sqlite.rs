use std::path::{Path, PathBuf};

use rusqlite::{Connection, OptionalExtension, params};
use time::OffsetDateTime;

use crate::error::{Result, StorageError};
use crate::types::{
    ConfigEntry, EntityRecord, GraphDocument, IngestManifestEntry, IngestRun, IngestRunStatus,
    RetryableRun, ToolStateEntry,
};
use mempalace_core::DrawerId;

const MIGRATIONS: &[(&str, &str)] = &[(
    "0001_initial_storage",
    r#"
CREATE TABLE IF NOT EXISTS migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingest_kind TEXT NOT NULL,
    source_key TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    failed_reason TEXT,
    UNIQUE(ingest_kind, source_key, created_at)
);

CREATE TABLE IF NOT EXISTS ingest_manifests (
    run_id INTEGER NOT NULL,
    drawer_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (run_id, drawer_id),
    FOREIGN KEY (run_id) REFERENCES ingest_runs(id)
);

CREATE TABLE IF NOT EXISTS ingest_files (
    source_file TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    last_ingested_at TEXT NOT NULL,
    ingest_kind TEXT NOT NULL,
    drawer_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_registry (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS graph_state (
    graph_key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_state (
    tool_name TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
    "#,
)];

pub trait IngestManifestStore {
    fn ensure_schema(&self) -> Result<()>;
    fn create_pending_run(
        &self,
        ingest_kind: &str,
        source_key: &str,
        entries: &[IngestManifestEntry],
        created_at: OffsetDateTime,
    ) -> Result<IngestRun>;
    fn mark_run_committed(
        &self,
        run_id: i64,
        source_file: &str,
        content_hash: &str,
        drawer_count: usize,
        committed_at: OffsetDateTime,
    ) -> Result<()>;
    fn stale_pending_runs(&self, older_than: OffsetDateTime) -> Result<Vec<RetryableRun>>;
    fn mark_run_failed(&self, run_id: i64, reason: &str, failed_at: OffsetDateTime) -> Result<()>;
    fn committed_drawer_ids(&self) -> Result<Vec<DrawerId>>;
}

pub trait EntityRegistryStore {
    fn upsert_entity(&self, entity: &EntityRecord) -> Result<()>;
    fn get_entity(&self, entity_id: &str) -> Result<Option<EntityRecord>>;
}

pub trait GraphStore {
    fn put_graph_document(&self, graph: &GraphDocument) -> Result<()>;
    fn get_graph_document(&self, graph_key: &str) -> Result<Option<GraphDocument>>;
}

pub trait ToolStateStore {
    fn put_tool_state(&self, state: &ToolStateEntry) -> Result<()>;
    fn get_tool_state(&self, tool_name: &str) -> Result<Option<ToolStateEntry>>;
    fn put_config(&self, entry: &ConfigEntry) -> Result<()>;
    fn get_config(&self, key: &str) -> Result<Option<ConfigEntry>>;
}

#[derive(Debug, Clone)]
pub struct SqliteOperationalStore {
    path: PathBuf,
}

impl SqliteOperationalStore {
    pub fn new(path: impl AsRef<Path>) -> Self {
        Self { path: path.as_ref().to_path_buf() }
    }

    pub fn migration_names() -> &'static [&'static str] {
        &["0001_initial_storage"]
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn ensure_schema_with_migrations(&self, migrations: &[(&str, &str)]) -> Result<()> {
        if let Some(parent) = self.path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|source| StorageError::Io { path: parent.to_path_buf(), source })?;
        }

        let mut connection = self.open_connection()?;
        let transaction = connection.transaction()?;
        transaction.execute_batch(
            "PRAGMA foreign_keys = ON;
             CREATE TABLE IF NOT EXISTS migrations (
                 version TEXT PRIMARY KEY,
                 applied_at TEXT NOT NULL
             );",
        )?;

        for (version, sql) in migrations {
            let already_applied = transaction
                .query_row("SELECT 1 FROM migrations WHERE version = ?1", [version], |_| Ok(()))
                .optional()?
                .is_some();

            if already_applied {
                continue;
            }

            transaction.execute_batch(sql)?;
            transaction.execute(
                "INSERT INTO migrations (version, applied_at) VALUES (?1, ?2)",
                params![
                    version,
                    OffsetDateTime::now_utc()
                        .format(&time::format_description::well_known::Rfc3339)
                        .map_err(|err| StorageError::Invariant(err.to_string()))?
                ],
            )?;
        }

        transaction.commit()?;
        Ok(())
    }

    fn open_connection(&self) -> Result<Connection> {
        let connection = Connection::open(&self.path)?;
        connection.execute_batch(
            "PRAGMA foreign_keys = ON;
             PRAGMA journal_mode = WAL;
             PRAGMA synchronous = NORMAL;",
        )?;
        Ok(connection)
    }
}

impl IngestManifestStore for SqliteOperationalStore {
    fn ensure_schema(&self) -> Result<()> {
        self.ensure_schema_with_migrations(MIGRATIONS)
    }

    fn create_pending_run(
        &self,
        ingest_kind: &str,
        source_key: &str,
        entries: &[IngestManifestEntry],
        created_at: OffsetDateTime,
    ) -> Result<IngestRun> {
        let mut connection = self.open_connection()?;
        let transaction = connection.transaction()?;
        let timestamp = encode_time(created_at);
        transaction.execute(
            "INSERT INTO ingest_runs (ingest_kind, source_key, status, created_at, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?4)",
            params![ingest_kind, source_key, IngestRunStatus::Pending.as_str(), timestamp],
        )?;
        let run_id = transaction.last_insert_rowid();

        for entry in entries {
            transaction.execute(
                "INSERT INTO ingest_manifests (run_id, drawer_id, source_file, content_hash, status)
                 VALUES (?1, ?2, ?3, ?4, ?5)",
                params![
                    run_id,
                    entry.drawer_id.as_ref(),
                    entry.source_file,
                    entry.content_hash,
                    IngestRunStatus::Pending.as_str()
                ],
            )?;
        }

        transaction.commit()?;
        Ok(IngestRun {
            id: run_id,
            ingest_kind: ingest_kind.to_owned(),
            source_key: source_key.to_owned(),
            status: IngestRunStatus::Pending,
            created_at,
            updated_at: created_at,
            failed_reason: None,
        })
    }

    fn mark_run_committed(
        &self,
        run_id: i64,
        source_file: &str,
        content_hash: &str,
        drawer_count: usize,
        committed_at: OffsetDateTime,
    ) -> Result<()> {
        let mut connection = self.open_connection()?;
        let transaction = connection.transaction()?;
        let timestamp = encode_time(committed_at);

        transaction.execute(
            "UPDATE ingest_manifests SET status = ?2 WHERE run_id = ?1",
            params![run_id, IngestRunStatus::Committed.as_str()],
        )?;
        transaction.execute(
            "UPDATE ingest_runs SET status = ?2, updated_at = ?3, failed_reason = NULL WHERE id = ?1",
            params![run_id, IngestRunStatus::Committed.as_str(), timestamp],
        )?;

        let ingest_kind: String = transaction.query_row(
            "SELECT ingest_kind FROM ingest_runs WHERE id = ?1",
            [run_id],
            |row| row.get(0),
        )?;

        transaction.execute(
            "INSERT INTO ingest_files (source_file, content_hash, last_ingested_at, ingest_kind, drawer_count)
             VALUES (?1, ?2, ?3, ?4, ?5)
             ON CONFLICT(source_file) DO UPDATE SET
                 content_hash = excluded.content_hash,
                 last_ingested_at = excluded.last_ingested_at,
                 ingest_kind = excluded.ingest_kind,
                 drawer_count = excluded.drawer_count",
            params![source_file, content_hash, timestamp, ingest_kind, drawer_count as i64],
        )?;

        transaction.commit()?;
        Ok(())
    }

    fn stale_pending_runs(&self, older_than: OffsetDateTime) -> Result<Vec<RetryableRun>> {
        let connection = self.open_connection()?;
        let mut statement = connection.prepare(
            "SELECT id, ingest_kind, source_key, status, created_at, updated_at, failed_reason
             FROM ingest_runs
             WHERE status = ?1 AND updated_at < ?2
             ORDER BY id ASC",
        )?;

        let runs = statement
            .query_map(
                params![IngestRunStatus::Pending.as_str(), encode_time(older_than)],
                |row| {
                    Ok(IngestRun {
                        id: row.get(0)?,
                        ingest_kind: row.get(1)?,
                        source_key: row.get(2)?,
                        status: parse_status(row.get::<_, String>(3)?)?,
                        created_at: decode_time(row.get(4)?)?,
                        updated_at: decode_time(row.get(5)?)?,
                        failed_reason: row.get(6)?,
                    })
                },
            )?
            .collect::<std::result::Result<Vec<_>, _>>()?;

        let mut retryable = Vec::with_capacity(runs.len());
        for run in runs {
            let mut manifest_statement = connection.prepare(
                "SELECT drawer_id FROM ingest_manifests WHERE run_id = ?1 ORDER BY drawer_id ASC",
            )?;
            let chunk_ids = manifest_statement
                .query_map([run.id], |row| {
                    let raw: String = row.get(0)?;
                    DrawerId::new(raw).map_err(|err| {
                        rusqlite::Error::FromSqlConversionFailure(
                            0,
                            rusqlite::types::Type::Text,
                            Box::new(err),
                        )
                    })
                })?
                .collect::<std::result::Result<Vec<_>, _>>()?;

            retryable.push(RetryableRun { run, chunk_ids });
        }

        Ok(retryable)
    }

    fn mark_run_failed(&self, run_id: i64, reason: &str, failed_at: OffsetDateTime) -> Result<()> {
        let mut connection = self.open_connection()?;
        let transaction = connection.transaction()?;
        let timestamp = encode_time(failed_at);
        transaction.execute(
            "UPDATE ingest_manifests SET status = ?2 WHERE run_id = ?1",
            params![run_id, IngestRunStatus::Failed.as_str()],
        )?;
        transaction.execute(
            "UPDATE ingest_runs
             SET status = ?2, updated_at = ?3, failed_reason = ?4
             WHERE id = ?1",
            params![run_id, IngestRunStatus::Failed.as_str(), timestamp, reason],
        )?;
        transaction.commit()?;
        Ok(())
    }

    fn committed_drawer_ids(&self) -> Result<Vec<DrawerId>> {
        let connection = self.open_connection()?;
        let mut statement = connection.prepare(
            "SELECT drawer_id
             FROM ingest_manifests
             WHERE status = ?1
             ORDER BY drawer_id ASC",
        )?;
        statement
            .query_map([IngestRunStatus::Committed.as_str()], |row| {
                let raw: String = row.get(0)?;
                DrawerId::new(raw).map_err(|err| {
                    rusqlite::Error::FromSqlConversionFailure(
                        0,
                        rusqlite::types::Type::Text,
                        Box::new(err),
                    )
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()
            .map_err(StorageError::from)
    }
}

impl EntityRegistryStore for SqliteOperationalStore {
    fn upsert_entity(&self, entity: &EntityRecord) -> Result<()> {
        let connection = self.open_connection()?;
        connection.execute(
            "INSERT INTO entity_registry (entity_id, entity_type, payload_json, updated_at)
             VALUES (?1, ?2, ?3, ?4)
             ON CONFLICT(entity_id) DO UPDATE SET
                 entity_type = excluded.entity_type,
                 payload_json = excluded.payload_json,
                 updated_at = excluded.updated_at",
            params![
                entity.entity_id,
                entity.entity_type,
                serde_json::to_string(&entity.payload)?,
                encode_time(entity.updated_at)
            ],
        )?;
        Ok(())
    }

    fn get_entity(&self, entity_id: &str) -> Result<Option<EntityRecord>> {
        let connection = self.open_connection()?;
        connection
            .query_row(
                "SELECT entity_id, entity_type, payload_json, updated_at
                 FROM entity_registry WHERE entity_id = ?1",
                [entity_id],
                |row| {
                    Ok(EntityRecord {
                        entity_id: row.get(0)?,
                        entity_type: row.get(1)?,
                        payload: serde_json::from_str(&row.get::<_, String>(2)?).map_err(
                            |err| {
                                rusqlite::Error::FromSqlConversionFailure(
                                    2,
                                    rusqlite::types::Type::Text,
                                    Box::new(err),
                                )
                            },
                        )?,
                        updated_at: decode_time(row.get(3)?).map_err(|err| {
                            rusqlite::Error::FromSqlConversionFailure(
                                3,
                                rusqlite::types::Type::Text,
                                Box::new(err),
                            )
                        })?,
                    })
                },
            )
            .optional()
            .map_err(StorageError::from)
    }
}

impl GraphStore for SqliteOperationalStore {
    fn put_graph_document(&self, graph: &GraphDocument) -> Result<()> {
        let connection = self.open_connection()?;
        connection.execute(
            "INSERT INTO graph_state (graph_key, payload_json, updated_at)
             VALUES (?1, ?2, ?3)
             ON CONFLICT(graph_key) DO UPDATE SET
                 payload_json = excluded.payload_json,
                 updated_at = excluded.updated_at",
            params![
                graph.graph_key,
                serde_json::to_string(&graph.payload)?,
                encode_time(graph.updated_at)
            ],
        )?;
        Ok(())
    }

    fn get_graph_document(&self, graph_key: &str) -> Result<Option<GraphDocument>> {
        let connection = self.open_connection()?;
        connection
            .query_row(
                "SELECT graph_key, payload_json, updated_at
                 FROM graph_state WHERE graph_key = ?1",
                [graph_key],
                |row| {
                    Ok(GraphDocument {
                        graph_key: row.get(0)?,
                        payload: serde_json::from_str(&row.get::<_, String>(1)?).map_err(
                            |err| {
                                rusqlite::Error::FromSqlConversionFailure(
                                    1,
                                    rusqlite::types::Type::Text,
                                    Box::new(err),
                                )
                            },
                        )?,
                        updated_at: decode_time(row.get(2)?).map_err(|err| {
                            rusqlite::Error::FromSqlConversionFailure(
                                2,
                                rusqlite::types::Type::Text,
                                Box::new(err),
                            )
                        })?,
                    })
                },
            )
            .optional()
            .map_err(StorageError::from)
    }
}

impl ToolStateStore for SqliteOperationalStore {
    fn put_tool_state(&self, state: &ToolStateEntry) -> Result<()> {
        let connection = self.open_connection()?;
        connection.execute(
            "INSERT INTO tool_state (tool_name, payload_json, updated_at)
             VALUES (?1, ?2, ?3)
             ON CONFLICT(tool_name) DO UPDATE SET
                 payload_json = excluded.payload_json,
                 updated_at = excluded.updated_at",
            params![state.tool_name, state.payload, encode_time(state.updated_at)],
        )?;
        Ok(())
    }

    fn get_tool_state(&self, tool_name: &str) -> Result<Option<ToolStateEntry>> {
        let connection = self.open_connection()?;
        connection
            .query_row(
                "SELECT tool_name, payload_json, updated_at
                 FROM tool_state WHERE tool_name = ?1",
                [tool_name],
                |row| {
                    Ok(ToolStateEntry {
                        tool_name: row.get(0)?,
                        payload: row.get(1)?,
                        updated_at: decode_time(row.get(2)?).map_err(|err| {
                            rusqlite::Error::FromSqlConversionFailure(
                                2,
                                rusqlite::types::Type::Text,
                                Box::new(err),
                            )
                        })?,
                    })
                },
            )
            .optional()
            .map_err(StorageError::from)
    }

    fn put_config(&self, entry: &ConfigEntry) -> Result<()> {
        let connection = self.open_connection()?;
        connection.execute(
            "INSERT INTO config (config_key, config_value)
             VALUES (?1, ?2)
             ON CONFLICT(config_key) DO UPDATE SET config_value = excluded.config_value",
            params![entry.config_key, entry.config_value],
        )?;
        Ok(())
    }

    fn get_config(&self, key: &str) -> Result<Option<ConfigEntry>> {
        let connection = self.open_connection()?;
        connection
            .query_row(
                "SELECT config_key, config_value FROM config WHERE config_key = ?1",
                [key],
                |row| Ok(ConfigEntry { config_key: row.get(0)?, config_value: row.get(1)? }),
            )
            .optional()
            .map_err(StorageError::from)
    }
}

fn parse_status(raw: String) -> rusqlite::Result<IngestRunStatus> {
    match raw.as_str() {
        "pending" => Ok(IngestRunStatus::Pending),
        "committed" => Ok(IngestRunStatus::Committed),
        "failed" => Ok(IngestRunStatus::Failed),
        _ => Err(rusqlite::Error::FromSqlConversionFailure(
            0,
            rusqlite::types::Type::Text,
            Box::new(StorageError::Invariant(format!("unknown ingest status `{raw}`"))),
        )),
    }
}

fn encode_time(value: OffsetDateTime) -> String {
    value
        .format(&time::format_description::well_known::Rfc3339)
        .unwrap_or_else(|_| value.unix_timestamp().to_string())
}

fn decode_time(raw: String) -> Result<OffsetDateTime> {
    OffsetDateTime::parse(&raw, &time::format_description::well_known::Rfc3339)
        .map_err(|err| StorageError::Invariant(err.to_string()))
}

#[cfg(test)]
mod tests {
    use tempfile::tempdir;
    use time::macros::datetime;

    use super::{
        EntityRegistryStore, GraphStore, IngestManifestStore, MIGRATIONS, SqliteOperationalStore,
        ToolStateStore,
    };
    use crate::types::{
        ConfigEntry, EntityRecord, GraphDocument, IngestManifestEntry, IngestRunStatus,
        ToolStateEntry,
    };
    use mempalace_core::DrawerId;
    use serde_json::json;

    #[test]
    fn applies_all_migrations() {
        let tempdir = tempdir().unwrap();
        let store = SqliteOperationalStore::new(tempdir.path().join("storage.sqlite3"));

        store.ensure_schema().unwrap();

        let connection = rusqlite::Connection::open(store.path()).unwrap();
        let count: i64 =
            connection.query_row("SELECT COUNT(*) FROM migrations", [], |row| row.get(0)).unwrap();
        assert_eq!(count as usize, MIGRATIONS.len());
    }

    #[test]
    fn rolls_back_failed_migrations() {
        let tempdir = tempdir().unwrap();
        let store = SqliteOperationalStore::new(tempdir.path().join("storage.sqlite3"));

        let result = store.ensure_schema_with_migrations(&[
            ("0001_ok", "CREATE TABLE IF NOT EXISTS ok_table(id INTEGER PRIMARY KEY);"),
            ("0002_bad", "CREATE TABLE broken("),
        ]);
        assert!(result.is_err());

        let connection = rusqlite::Connection::open(store.path()).unwrap();
        let exists = connection
            .query_row(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ok_table'",
                [],
                |_| Ok(()),
            )
            .optional()
            .unwrap()
            .is_some();
        assert!(!exists);
    }

    #[test]
    fn tracks_pending_and_stale_runs() {
        let tempdir = tempdir().unwrap();
        let store = SqliteOperationalStore::new(tempdir.path().join("storage.sqlite3"));
        store.ensure_schema().unwrap();

        let run = store
            .create_pending_run(
                "projects",
                "project_alpha",
                &[IngestManifestEntry {
                    run_id: 0,
                    drawer_id: DrawerId::new("project_alpha/backend/0001").unwrap(),
                    source_file: "auth.py".to_owned(),
                    content_hash: "hash-a".to_owned(),
                    status: IngestRunStatus::Pending,
                }],
                datetime!(2026-04-10 00:00:00 UTC),
            )
            .unwrap();

        let stale = store.stale_pending_runs(datetime!(2026-04-11 00:00:00 UTC)).unwrap();
        assert_eq!(stale.len(), 1);
        assert_eq!(stale[0].run.id, run.id);

        store.mark_run_failed(run.id, "interrupted", datetime!(2026-04-11 00:05:00 UTC)).unwrap();
        let stale_after = store.stale_pending_runs(datetime!(2026-04-12 00:00:00 UTC)).unwrap();
        assert!(stale_after.is_empty());
    }

    #[test]
    fn stores_tool_state_and_config() {
        let tempdir = tempdir().unwrap();
        let store = SqliteOperationalStore::new(tempdir.path().join("storage.sqlite3"));
        store.ensure_schema().unwrap();

        store
            .put_tool_state(&ToolStateEntry {
                tool_name: "mcp".to_owned(),
                payload: "{\"ok\":true}".to_owned(),
                updated_at: datetime!(2026-04-11 09:00:00 UTC),
            })
            .unwrap();
        store
            .put_config(&ConfigEntry {
                config_key: "profile".to_owned(),
                config_value: "balanced".to_owned(),
            })
            .unwrap();

        assert_eq!(store.get_tool_state("mcp").unwrap().unwrap().payload, "{\"ok\":true}");
        assert_eq!(store.get_config("profile").unwrap().unwrap().config_value, "balanced");
    }

    #[test]
    fn stores_entities_and_graph_documents() {
        let tempdir = tempdir().unwrap();
        let store = SqliteOperationalStore::new(tempdir.path().join("storage.sqlite3"));
        store.ensure_schema().unwrap();

        store
            .upsert_entity(&EntityRecord {
                entity_id: "person:kai".to_owned(),
                entity_type: "person".to_owned(),
                payload: json!({ "name": "Kai" }),
                updated_at: datetime!(2026-04-11 11:00:00 UTC),
            })
            .unwrap();
        store
            .put_graph_document(&GraphDocument {
                graph_key: "palace".to_owned(),
                payload: json!({ "rooms": ["backend"] }),
                updated_at: datetime!(2026-04-11 11:05:00 UTC),
            })
            .unwrap();

        assert_eq!(
            store.get_entity("person:kai").unwrap().unwrap().payload,
            json!({ "name": "Kai" })
        );
        assert_eq!(
            store.get_graph_document("palace").unwrap().unwrap().payload,
            json!({ "rooms": ["backend"] })
        );
    }
}
