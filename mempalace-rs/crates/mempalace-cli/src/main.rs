#![allow(missing_docs)]

use mempalace_config::ConfigLoader;
use tracing_subscriber::{EnvFilter, fmt};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_tracing("info");
    let paths = ConfigLoader::init_default(None)?;
    let config = ConfigLoader::load_with_env(None)?;

    tracing::info!(
        config_file = %paths.config_file.display(),
        palace_path = %config.palace_path.display(),
        embedding_profile = config.embedding_profile.as_str(),
        "mempalace cli foundation initialized"
    );

    Ok(())
}

fn init_tracing(default_filter: &str) {
    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(default_filter));

    let _ = fmt().with_env_filter(filter).with_target(false).try_init();
}
