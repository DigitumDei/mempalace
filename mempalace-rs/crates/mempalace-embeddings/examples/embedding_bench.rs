use std::env;
use std::path::PathBuf;

use mempalace_core::EmbeddingProfile;
use mempalace_embeddings::{
    EmbeddingBenchmark, EmbeddingRequest, FastembedProvider, FastembedProviderConfig,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cache_root =
        env::var_os("MEMPALACE_EMBED_CACHE").map(PathBuf::from).unwrap_or_else(default_cache_root);
    let profile = env::var("MEMPALACE_EMBED_PROFILE")
        .ok()
        .as_deref()
        .unwrap_or("balanced")
        .parse::<EmbeddingProfile>()?;
    let request = EmbeddingRequest::new(vec![
        "MemPalace benchmark query for warm-path embedding latency.".to_owned(),
    ])?;

    let mut provider = FastembedProvider::new(profile, FastembedProviderConfig::new(cache_root))
        .try_initialize()?;
    let benchmark = EmbeddingBenchmark::measure(&mut provider, &request, 15)?;

    if let Some(p95) = benchmark.p95_millis() {
        println!("profile={} p95_ms={p95:.2}", profile.as_str());
    }

    Ok(())
}

fn default_cache_root() -> PathBuf {
    PathBuf::from(".cache").join("mempalace").join("embeddings")
}
