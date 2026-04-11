#![allow(missing_docs)]

use mempalace_config::ConfigLoader;
use mempalace_core::init_tracing;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_tracing("info");
    let config = ConfigLoader::load_with_env(None)?;

    tracing::info!(
        palace_path = %config.palace_path.display(),
        embedding_profile = config.embedding_profile.as_str(),
        "mempalace cli foundation initialized"
    );

    Ok(())
}
