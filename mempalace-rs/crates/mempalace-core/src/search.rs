use serde::{Deserialize, Serialize};
use time::{Date, OffsetDateTime};

use crate::{DrawerId, EmbeddingProfile, RoomId, WingId};

/// Canonical drawer row shape for future storage adapters.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DrawerRecord {
    pub id: DrawerId,
    pub wing: WingId,
    pub room: RoomId,
    pub hall: Option<String>,
    pub date: Option<Date>,
    pub source_file: String,
    pub chunk_index: i32,
    pub ingest_mode: String,
    pub extract_mode: Option<String>,
    pub added_by: String,
    pub filed_at: OffsetDateTime,
    pub importance: Option<f32>,
    pub emotional_weight: Option<f32>,
    pub weight: Option<f32>,
    pub content: String,
    pub content_hash: String,
}

/// Search request contract shared by CLI, MCP, and library APIs.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SearchQuery {
    pub text: String,
    pub wing: Option<WingId>,
    pub room: Option<RoomId>,
    pub limit: usize,
    pub profile: EmbeddingProfile,
}

/// Search result contract shared by CLI, MCP, and library APIs.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SearchResult {
    pub drawer_id: DrawerId,
    pub wing: WingId,
    pub room: RoomId,
    pub score: f32,
    pub content: String,
    pub source_file: String,
}
