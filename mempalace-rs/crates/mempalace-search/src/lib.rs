#![allow(missing_docs)]

use std::cmp::Ordering;
use std::fs;
use std::path::{Path, PathBuf};

pub use mempalace_core as core;
pub use mempalace_embeddings as embeddings;
pub use mempalace_storage as storage;

use mempalace_core::{DrawerRecord, SearchQuery, SearchResult};
use mempalace_embeddings::{EmbeddingProvider, EmbeddingRequest};
use mempalace_storage::{DrawerFilter, DrawerMatch, DrawerStore, SearchRequest};
use thiserror::Error;

const DEFAULT_LAYER1_MAX_DRAWERS: usize = 15;
const DEFAULT_LAYER1_MAX_CHARS: usize = 3_200;
const LAYER1_SNIPPET_LIMIT: usize = 200;
const LAYER2_SNIPPET_LIMIT: usize = 300;

pub type Result<T> = std::result::Result<T, SearchError>;

#[derive(Debug, Error)]
pub enum SearchError {
    #[error(transparent)]
    Core(#[from] mempalace_core::MempalaceError),
    #[error(transparent)]
    Embeddings(#[from] mempalace_embeddings::EmbeddingError),
    #[error(transparent)]
    Storage(#[from] mempalace_storage::StorageError),
    #[error(
        "search query requested embedding profile `{query}`, but runtime is configured for `{provider}`"
    )]
    ProfileMismatch { query: &'static str, provider: &'static str },
    #[error("search query text cannot be blank")]
    BlankQuery,
    #[error("failed to read identity at {path}: {source}")]
    IdentityRead {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Layer1Config {
    pub max_drawers: usize,
    pub max_chars: usize,
}

impl Default for Layer1Config {
    fn default() -> Self {
        Self { max_drawers: DEFAULT_LAYER1_MAX_DRAWERS, max_chars: DEFAULT_LAYER1_MAX_CHARS }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WakeUpRequest {
    pub wing: Option<mempalace_core::WingId>,
    pub identity: IdentitySource,
    pub layer1: Layer1Config,
}

impl Default for WakeUpRequest {
    fn default() -> Self {
        Self {
            wing: None,
            identity: IdentitySource::MissingDefault,
            layer1: Layer1Config::default(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IdentitySource {
    Inline(String),
    Path(PathBuf),
    MissingDefault,
}

impl IdentitySource {
    pub fn render(&self) -> Result<String> {
        match self {
            Self::Inline(value) => Ok(value.trim().to_owned()),
            Self::Path(path) => fs::read_to_string(path)
                .map(|text| text.trim().to_owned())
                .map_err(|source| SearchError::IdentityRead { path: path.clone(), source }),
            Self::MissingDefault => Ok(
                "## L0 - IDENTITY\nNo identity configured. Create ~/.mempalace/identity.txt"
                    .to_owned(),
            ),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct LayerRetrieveRequest {
    pub wing: Option<mempalace_core::WingId>,
    pub room: Option<mempalace_core::RoomId>,
    pub limit: usize,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SearchRuntime<P> {
    provider: P,
}

impl<P> SearchRuntime<P>
where
    P: EmbeddingProvider,
{
    pub fn new(provider: P) -> Self {
        Self { provider }
    }

    pub fn provider(&self) -> &P {
        &self.provider
    }

    pub fn provider_mut(&mut self) -> &mut P {
        &mut self.provider
    }

    pub async fn search<S>(&mut self, store: &S, query: &SearchQuery) -> Result<Vec<SearchResult>>
    where
        S: DrawerStore,
    {
        let provider_profile = self.provider.profile().profile;
        if provider_profile != query.profile {
            return Err(SearchError::ProfileMismatch {
                query: query.profile.as_str(),
                provider: provider_profile.as_str(),
            });
        }

        if query.text.trim().is_empty() {
            return Err(SearchError::BlankQuery);
        }

        if query.limit == 0 {
            return Ok(Vec::new());
        }

        let request = EmbeddingRequest::new(vec![query.text.clone()])?;
        let response = self.provider.embed(&request)?;
        let query_embedding = response
            .vectors()
            .first()
            .cloned()
            .ok_or_else(|| {
                SearchError::Embeddings(mempalace_embeddings::EmbeddingError::ProviderContract(
                    "provider returned no vector for a non-empty search query".to_owned(),
                ))
            })?;

        let matches = store
            .search_drawers(&SearchRequest {
                embedding: query_embedding,
                limit: query.limit,
                filter: DrawerFilter {
                    wing: query.wing.clone(),
                    room: query.room.clone(),
                    ..DrawerFilter::default()
                },
            })
            .await?;

        Ok(rank_matches(matches, query.limit)
            .into_iter()
            .map(|entry| SearchResult {
                drawer_id: None,
                wing: entry.record.wing.clone(),
                room: entry.record.room.clone(),
                score: entry.score,
                content: entry.record.content.clone(),
                source_file: source_label(&entry.record.source_file),
            })
            .collect())
    }

    pub async fn search_text<S>(&mut self, store: &S, query: &SearchQuery) -> Result<String>
    where
        S: DrawerStore,
    {
        let results = self.search(store, query).await?;
        Ok(render_search_results(&query.text, &results, query.wing.as_ref(), query.room.as_ref()))
    }

    pub async fn recall<S>(&self, store: &S, request: &LayerRetrieveRequest) -> Result<String>
    where
        S: DrawerStore,
    {
        let limit = if request.limit == 0 { 10 } else { request.limit };
        let mut drawers = store
            .list_drawers(&DrawerFilter {
                wing: request.wing.clone(),
                room: request.room.clone(),
                ..DrawerFilter::default()
            })
            .await?;

        order_layer_drawers(&mut drawers);

        if drawers.is_empty() {
            let mut label = String::new();
            if let Some(wing) = &request.wing {
                label.push_str("wing=");
                label.push_str(wing.as_str());
            }
            if let Some(room) = &request.room {
                if !label.is_empty() {
                    label.push(' ');
                }
                label.push_str("room=");
                label.push_str(room.as_str());
            }

            return Ok(if label.is_empty() {
                "No drawers found.".to_owned()
            } else {
                format!("No drawers found for {label}.")
            });
        }

        let mut lines = vec![format!("## L2 — ON-DEMAND ({}) drawers", drawers.len().min(limit))];
        for record in drawers.iter().take(limit) {
            let snippet = flatten_and_truncate(&record.content, LAYER2_SNIPPET_LIMIT);
            let mut entry = format!("  [{}] {}", record.room.as_str(), snippet);
            let source = source_label(&record.source_file);
            if !source.is_empty() {
                entry.push_str("  (");
                entry.push_str(&source);
                entry.push(')');
            }
            lines.push(entry);
        }

        Ok(lines.join("\n"))
    }

    pub async fn wake_up<S>(&self, store: &S, request: &WakeUpRequest) -> Result<String>
    where
        S: DrawerStore,
    {
        let identity = request.identity.render()?;
        let story = generate_layer1(
            store,
            request.wing.clone(),
            request.layer1.clone(),
        )
        .await?;

        Ok(format!("{identity}\n\n{story}"))
    }
}

pub fn render_search_results(
    query: &str,
    results: &[SearchResult],
    wing: Option<&mempalace_core::WingId>,
    room: Option<&mempalace_core::RoomId>,
) -> String {
    if results.is_empty() {
        return format!("\n  No results found for: \"{query}\"");
    }

    let mut lines = vec![
        String::new(),
        "============================================================".to_owned(),
        format!("  Results for: \"{query}\""),
    ];

    if let Some(wing) = wing {
        lines.push(format!("  Wing: {}", wing.as_str()));
    }
    if let Some(room) = room {
        lines.push(format!("  Room: {}", room.as_str()));
    }

    lines.push("============================================================".to_owned());
    lines.push(String::new());

    for (index, result) in results.iter().enumerate() {
        lines.push(format!("  [{}] {} / {}", index + 1, result.wing.as_str(), result.room.as_str()));
        lines.push(format!("      Source: {}", result.source_file));
        lines.push(format!("      Match:  {}", trim_similarity(result.score)));
        lines.push(String::new());

        for line in result.content.trim().lines() {
            lines.push(format!("      {line}"));
        }

        lines.push(String::new());
        lines.push("  ────────────────────────────────────────────────────────".to_owned());
    }

    lines.push(String::new());
    lines.join("\n")
}

pub async fn generate_layer1<S>(
    store: &S,
    wing: Option<mempalace_core::WingId>,
    config: Layer1Config,
) -> Result<String>
where
    S: DrawerStore,
{
    let mut drawers = store
        .list_drawers(&DrawerFilter { wing, ..DrawerFilter::default() })
        .await?;

    if drawers.is_empty() {
        return Ok("## L1 — No memories yet.".to_owned());
    }

    order_layer_drawers(&mut drawers);
    let top = drawers.into_iter().take(config.max_drawers).collect::<Vec<_>>();

    let mut grouped = std::collections::BTreeMap::<String, Vec<DrawerRecord>>::new();
    for record in top {
        grouped.entry(record.room.as_str().to_owned()).or_default().push(record);
    }

    let mut lines = vec!["## L1 — ESSENTIAL STORY".to_owned()];
    let mut total_len = lines[0].len();

    for (room, records) in grouped {
        let room_line = format!("\n[{room}]");
        lines.push(room_line.clone());
        total_len += room_line.len();

        for record in records {
            let snippet = flatten_and_truncate(&record.content, LAYER1_SNIPPET_LIMIT);
            let source = source_label(&record.source_file);

            let mut entry = format!("  - {snippet}");
            if !source.is_empty() {
                entry.push_str("  (");
                entry.push_str(&source);
                entry.push(')');
            }

            if total_len + entry.len() > config.max_chars {
                lines.push("  ... (more in L3 search)".to_owned());
                return Ok(lines.join("\n"));
            }

            total_len += entry.len();
            lines.push(entry);
        }
    }

    Ok(lines.join("\n"))
}

fn rank_matches(matches: Vec<DrawerMatch>, limit: usize) -> Vec<RankedMatch> {
    let mut ranked = matches
        .into_iter()
        .map(|matched| RankedMatch {
            score: normalize_score(matched.distance),
            distance: matched.distance,
            record: matched.record,
        })
        .collect::<Vec<_>>();

    ranked.sort_by(compare_ranked_matches);
    ranked.truncate(limit);
    ranked
}

fn compare_ranked_matches(left: &RankedMatch, right: &RankedMatch) -> Ordering {
    right
        .score
        .partial_cmp(&left.score)
        .unwrap_or(Ordering::Equal)
        .then_with(|| compare_distance(left.distance, right.distance))
        .then_with(|| left.record.wing.as_str().cmp(right.record.wing.as_str()))
        .then_with(|| left.record.room.as_str().cmp(right.record.room.as_str()))
        .then_with(|| source_label(&left.record.source_file).cmp(&source_label(&right.record.source_file)))
        .then_with(|| left.record.chunk_index.cmp(&right.record.chunk_index))
        .then_with(|| left.record.id.as_str().cmp(right.record.id.as_str()))
}

fn compare_distance(left: Option<f32>, right: Option<f32>) -> Ordering {
    match (left, right) {
        (Some(left), Some(right)) => left.partial_cmp(&right).unwrap_or(Ordering::Equal),
        (Some(_), None) => Ordering::Less,
        (None, Some(_)) => Ordering::Greater,
        (None, None) => Ordering::Equal,
    }
}

fn order_layer_drawers(drawers: &mut [DrawerRecord]) {
    drawers.sort_by(|left, right| {
        right
            .layer_weight()
            .partial_cmp(&left.layer_weight())
            .unwrap_or(Ordering::Equal)
            .then_with(|| left.room.as_str().cmp(right.room.as_str()))
            .then_with(|| compare_option_dates(right.date, left.date))
            .then_with(|| right.filed_at.cmp(&left.filed_at))
            .then_with(|| source_label(&left.source_file).cmp(&source_label(&right.source_file)))
            .then_with(|| left.chunk_index.cmp(&right.chunk_index))
            .then_with(|| left.id.as_str().cmp(right.id.as_str()))
    });
}

fn compare_option_dates(
    left: Option<time::Date>,
    right: Option<time::Date>,
) -> Ordering {
    match (left, right) {
        (Some(left), Some(right)) => left.cmp(&right),
        (Some(_), None) => Ordering::Greater,
        (None, Some(_)) => Ordering::Less,
        (None, None) => Ordering::Equal,
    }
}

fn normalize_score(distance: Option<f32>) -> f32 {
    distance.map_or(0.0, |value| 1.0 - value)
}

fn trim_similarity(score: f32) -> String {
    let rounded = (score * 1_000.0).round() / 1_000.0;
    if rounded.fract() == 0.0 {
        format!("{rounded:.0}")
    } else if ((rounded * 10.0).round() - (rounded * 10.0)).abs() < f32::EPSILON {
        format!("{rounded:.1}")
    } else if ((rounded * 100.0).round() - (rounded * 100.0)).abs() < f32::EPSILON {
        format!("{rounded:.2}")
    } else {
        format!("{rounded:.3}")
    }
}

fn flatten_and_truncate(content: &str, limit: usize) -> String {
    let flattened = content
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");

    if flattened.chars().count() <= limit {
        flattened
    } else {
        flattened.chars().take(limit.saturating_sub(3)).collect::<String>() + "..."
    }
}

fn source_label(source_file: &str) -> String {
    Path::new(source_file)
        .file_name()
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_else(|| source_file.to_owned())
}

trait LayerWeight {
    fn layer_weight(&self) -> f32;
}

impl LayerWeight for DrawerRecord {
    fn layer_weight(&self) -> f32 {
        self.importance
            .or(self.emotional_weight)
            .or(self.weight)
            .unwrap_or(3.0)
    }
}

#[derive(Debug, Clone, PartialEq)]
struct RankedMatch {
    score: f32,
    distance: Option<f32>,
    record: DrawerRecord,
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::{
        IdentitySource, Layer1Config, LayerRetrieveRequest, SearchRuntime, WakeUpRequest,
        generate_layer1, render_search_results,
    };
    use async_trait::async_trait;
    use mempalace_core::{DrawerId, DrawerRecord, EmbeddingProfile, RoomId, SearchQuery, WingId};
    use mempalace_embeddings::{
        EmbeddingProvider, EmbeddingRequest, EmbeddingResponse, StartupValidation,
        StartupValidationStatus,
    };
    use mempalace_storage::{
        DrawerFilter, DrawerMatch, DrawerStore, DuplicateStrategy, SearchRequest, StorageError,
    };
    use std::path::PathBuf;
    use time::macros::{date, datetime};

    fn embedding(value: f32) -> Vec<f32> {
        vec![value; EmbeddingProfile::Balanced.metadata().dimensions]
    }

    fn record(
        id: &str,
        wing: &str,
        room: &str,
        source_file: &str,
        content: &str,
        score: Option<f32>,
        filed_at: time::OffsetDateTime,
    ) -> DrawerRecord {
        DrawerRecord {
            id: DrawerId::new(id).unwrap(),
            wing: WingId::new(wing).unwrap(),
            room: RoomId::new(room).unwrap(),
            hall: Some("facts".to_owned()),
            date: Some(date!(2026 - 04 - 11)),
            source_file: source_file.to_owned(),
            chunk_index: 0,
            ingest_mode: "projects".to_owned(),
            extract_mode: Some("full".to_owned()),
            added_by: "tester".to_owned(),
            filed_at,
            importance: score,
            emotional_weight: None,
            weight: None,
            content: content.to_owned(),
            content_hash: format!("hash-{id}"),
            embedding: embedding(
                score.unwrap_or(0.0),
            ),
        }
    }

    #[derive(Debug, Clone)]
    struct StubProvider {
        response: Vec<Vec<f32>>,
    }

    impl EmbeddingProvider for StubProvider {
        fn profile(&self) -> &'static mempalace_core::EmbeddingProfileMetadata {
            EmbeddingProfile::Balanced.metadata()
        }

        fn startup_validation(&self) -> mempalace_embeddings::Result<StartupValidation> {
            Ok(StartupValidation {
                status: StartupValidationStatus::Ready,
                cache_root: PathBuf::from("/tmp"),
                model_id: EmbeddingProfile::Balanced.metadata().model_id,
                detail: "ok".to_owned(),
            })
        }

        fn embed(
            &mut self,
            request: &EmbeddingRequest,
        ) -> mempalace_embeddings::Result<EmbeddingResponse> {
            let vectors = self.response.iter().take(request.len()).cloned().collect::<Vec<_>>();
            EmbeddingResponse::from_vectors(
                vectors,
                EmbeddingProfile::Balanced.metadata().dimensions,
                EmbeddingProfile::Balanced,
                EmbeddingProfile::Balanced.metadata().model_id,
            )
        }
    }

    #[derive(Debug, Clone)]
    struct StubStore {
        drawers: Vec<DrawerRecord>,
    }

    #[async_trait]
    impl DrawerStore for StubStore {
        async fn ensure_schema(&self) -> Result<(), StorageError> {
            Ok(())
        }

        async fn put_drawers(
            &self,
            _drawers: &[DrawerRecord],
            _strategy: DuplicateStrategy,
        ) -> Result<(), StorageError> {
            unreachable!("not used in phase 5 tests")
        }

        async fn get_drawer(&self, _id: &DrawerId) -> Result<Option<DrawerRecord>, StorageError> {
            unreachable!("not used in phase 5 tests")
        }

        async fn delete_drawers(&self, _ids: &[DrawerId]) -> Result<usize, StorageError> {
            unreachable!("not used in phase 5 tests")
        }

        async fn search_drawers(
            &self,
            request: &SearchRequest,
        ) -> Result<Vec<DrawerMatch>, StorageError> {
            let mut filtered = self
                .drawers
                .iter()
                .filter(|drawer| filter_matches(drawer, &request.filter))
                .cloned()
                .map(|drawer| DrawerMatch {
                    distance: Some((drawer.embedding[0] - request.embedding[0]).abs()),
                    record: drawer,
                })
                .collect::<Vec<_>>();

            filtered.sort_by(|left, right| {
                left.distance
                    .partial_cmp(&right.distance)
                    .unwrap_or(std::cmp::Ordering::Equal)
            });
            filtered.truncate(request.limit);
            Ok(filtered)
        }

        async fn list_drawers(
            &self,
            filter: &DrawerFilter,
        ) -> Result<Vec<DrawerRecord>, StorageError> {
            Ok(self
                .drawers
                .iter()
                .filter(|drawer| filter_matches(drawer, filter))
                .cloned()
                .collect())
        }
    }

    fn filter_matches(drawer: &DrawerRecord, filter: &DrawerFilter) -> bool {
        (filter.ids.is_empty() || filter.ids.iter().any(|id| id == &drawer.id))
            && filter.wing.as_ref().is_none_or(|wing| wing == &drawer.wing)
            && filter.room.as_ref().is_none_or(|room| room == &drawer.room)
            && filter.hall.as_ref().is_none_or(|hall| drawer.hall.as_ref() == Some(hall))
            && filter
                .source_file
                .as_ref()
                .is_none_or(|source| source == &drawer.source_file)
    }

    fn sample_store() -> StubStore {
        StubStore {
            drawers: vec![
                record(
                    "wing_team/auth-migration/0001",
                    "wing_team",
                    "auth-migration",
                    "fixtures/team.txt",
                    "The team decided the auth-migration must preserve CLI and MCP parity.",
                    Some(0.49),
                    datetime!(2026-04-11 09:00:00 UTC),
                ),
                record(
                    "wing_code/auth-migration/0001",
                    "wing_code",
                    "auth-migration",
                    "fixtures/code.txt",
                    "Code notes: auth-migration keeps search filter semantics exact while storage changes underneath.",
                    Some(0.069),
                    datetime!(2026-04-11 08:00:00 UTC),
                ),
                record(
                    "project_alpha/backend/0001",
                    "project_alpha",
                    "backend",
                    "project_alpha/backend/auth.py",
                    "def issue_session(user_id: str) -> str:\n    \"\"\"\n    We switched from opaque session blobs to signed session tokens because the\n    old format made auth debugging painful during the Rust migration work.\n    \"\"\"\n    if not user_id:\n        raise ValueError(\"user_id is required\")\n\n    token = f\"session:{user_id}:signed\"\n    return token\n\n\ndef refresh_token(token: str) -> str:\n    \"\"\"\n    The auth migration plan keeps refresh logic local-first and deterministic.\n    We chose signed tokens over a database-backed session lookup because the\n    CLI and MCP tools need predictable offline behavior.\n    \"\"\"\n    if not token.startswith(\"session:\"):\n        raise ValueError(\"invalid token format\")\n    return token + \":refreshed\"",
                    Some(-0.267),
                    datetime!(2026-04-11 07:00:00 UTC),
                ),
                record(
                    "wing_team/phase0-rollout/0001",
                    "wing_team",
                    "phase0-rollout",
                    "fixtures/rollout.txt",
                    "Phase 0 rollout stays on the team wing so graph traversal captures connected_via semantics.",
                    Some(-0.848),
                    datetime!(2026-04-10 07:00:00 UTC),
                ),
            ],
        }
    }

    #[tokio::test]
    async fn search_applies_filters_and_normalizes_similarity() {
        let mut runtime = SearchRuntime::new(StubProvider { response: vec![embedding(0.0)] });
        let store = sample_store();

        let query = SearchQuery {
            text: "auth migration parity".to_owned(),
            wing: Some(WingId::new("wing_team").unwrap()),
            room: None,
            limit: 5,
            profile: EmbeddingProfile::Balanced,
        };

        let results = runtime.search(&store, &query).await.unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].wing.as_str(), "wing_team");
        assert_eq!(results[0].room.as_str(), "auth-migration");
        assert!((results[0].score - 0.49).abs() < 1e-6);
        assert_eq!(results[0].source_file, "team.txt");
        assert_eq!(results[1].room.as_str(), "phase0-rollout");
    }

    #[tokio::test]
    async fn search_rejects_profile_mismatch() {
        let mut runtime = SearchRuntime::new(StubProvider { response: vec![embedding(0.0)] });
        let store = sample_store();
        let err = runtime
            .search(
                &store,
                &SearchQuery {
                    text: "auth".to_owned(),
                    wing: None,
                    room: None,
                    limit: 5,
                    profile: EmbeddingProfile::LowCpu,
                },
            )
            .await
            .unwrap_err();

        assert!(matches!(err, super::SearchError::ProfileMismatch { .. }));
    }

    #[tokio::test]
    async fn search_tie_breaking_is_deterministic() {
        let store = StubStore {
            drawers: vec![
                record(
                    "wing_b/general/0001",
                    "wing_b",
                    "general",
                    "zeta.txt",
                    "B",
                    Some(0.5),
                    datetime!(2026-04-11 09:00:00 UTC),
                ),
                record(
                    "wing_a/general/0001",
                    "wing_a",
                    "general",
                    "alpha.txt",
                    "A",
                    Some(0.5),
                    datetime!(2026-04-11 09:00:00 UTC),
                ),
            ],
        };
        let mut runtime = SearchRuntime::new(StubProvider { response: vec![embedding(0.0)] });
        let query = SearchQuery {
            text: "tie".to_owned(),
            wing: None,
            room: None,
            limit: 5,
            profile: EmbeddingProfile::Balanced,
        };

        let results = runtime.search(&store, &query).await.unwrap();
        assert_eq!(results.iter().map(|entry| entry.wing.as_str()).collect::<Vec<_>>(), vec!["wing_a", "wing_b"]);
    }

    #[test]
    fn render_search_results_matches_python_shape() {
        let rendered = render_search_results(
            "auth migration parity",
            &[
                mempalace_core::SearchResult {
                    drawer_id: None,
                    wing: WingId::new("wing_team").unwrap(),
                    room: RoomId::new("auth-migration").unwrap(),
                    score: 0.49,
                    content: "The team decided the auth-migration must preserve CLI and MCP parity."
                        .to_owned(),
                    source_file: "team.txt".to_owned(),
                },
                mempalace_core::SearchResult {
                    drawer_id: None,
                    wing: WingId::new("wing_code").unwrap(),
                    room: RoomId::new("auth-migration").unwrap(),
                    score: 0.069,
                    content: "Code notes: auth-migration keeps search filter semantics exact while storage changes underneath."
                        .to_owned(),
                    source_file: "code.txt".to_owned(),
                },
            ],
            None,
            None,
        );

        assert!(rendered.contains("Results for: \"auth migration parity\""));
        assert!(rendered.contains("[1] wing_team / auth-migration"));
        assert!(rendered.contains("Match:  0.49"));
        assert!(rendered.contains("Match:  0.069"));
    }

    #[tokio::test]
    async fn recall_returns_stable_filtered_layer_output() {
        let runtime = SearchRuntime::new(StubProvider { response: vec![embedding(0.0)] });
        let store = sample_store();
        let rendered = runtime
            .recall(
                &store,
                &LayerRetrieveRequest {
                    wing: Some(WingId::new("wing_team").unwrap()),
                    room: None,
                    limit: 10,
                },
            )
            .await
            .unwrap();

        assert!(rendered.starts_with("## L2 — ON-DEMAND (2 drawers)"));
        assert!(rendered.contains("[auth-migration] The team decided"));
        assert!(rendered.contains("[phase0-rollout] Phase 0 rollout"));
    }

    #[tokio::test]
    async fn wake_up_uses_identity_and_groups_rooms_in_stable_order() {
        let runtime = SearchRuntime::new(StubProvider { response: vec![embedding(0.0)] });
        let store = sample_store();
        let rendered = runtime
            .wake_up(
                &store,
                &WakeUpRequest {
                    wing: None,
                    identity: IdentitySource::Inline(
                        "## L0 - IDENTITY\nI am the MemPalace phase 0 reference capture.".to_owned(),
                    ),
                    layer1: Layer1Config { max_drawers: 4, max_chars: 3_200 },
                },
            )
            .await
            .unwrap();

        assert!(rendered.starts_with("## L0 - IDENTITY"));
        assert!(rendered.contains("## L1 — ESSENTIAL STORY"));
        let auth_index = rendered.find("[auth-migration]").unwrap();
        let backend_index = rendered.find("[backend]").unwrap();
        let rollout_index = rendered.find("[phase0-rollout]").unwrap();
        assert!(auth_index < backend_index);
        assert!(backend_index < rollout_index);
        assert!(rendered.contains("(team.txt)"));
        assert!(rendered.contains("(auth.py)"));
    }

    #[tokio::test]
    async fn generate_layer1_honors_wing_filter() {
        let store = sample_store();
        let layer1 = generate_layer1(
            &store,
            Some(WingId::new("wing_code").unwrap()),
            Layer1Config::default(),
        )
        .await
        .unwrap();

        assert!(layer1.contains("[auth-migration]"));
        assert!(layer1.contains("code.txt"));
        assert!(!layer1.contains("team.txt"));
    }

    #[tokio::test]
    async fn search_text_reports_empty_results() {
        let mut runtime = SearchRuntime::new(StubProvider { response: vec![embedding(100.0)] });
        let store = StubStore { drawers: Vec::new() };
        let rendered = runtime
            .search_text(
                &store,
                &SearchQuery {
                    text: "missing".to_owned(),
                    wing: None,
                    room: None,
                    limit: 5,
                    profile: EmbeddingProfile::Balanced,
                },
            )
            .await
            .unwrap();

        assert_eq!(rendered, "\n  No results found for: \"missing\"");
    }

    #[test]
    fn identity_source_can_load_inline_or_missing_default() {
        assert_eq!(
            IdentitySource::Inline(" hello \n".to_owned()).render().unwrap(),
            "hello"
        );
        assert!(IdentitySource::MissingDefault
            .render()
            .unwrap()
            .contains("No identity configured"));
    }
}
