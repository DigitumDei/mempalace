#![allow(missing_docs)]

use std::env;
use std::path::PathBuf;

use mempalace_config::ConfigLoader;
use mempalace_core::EmbeddingProfile;
use mempalace_embeddings::{
    EmbeddingProvider, FastembedProvider, FastembedProviderConfig, StartupValidationStatus,
    log_startup_validation,
};
use tracing_subscriber::{EnvFilter, fmt};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_tracing("info");
    match parse_args(env::args().skip(1))? {
        Command::Help => {
            print!("{}", usage());
        }
        Command::Version => {
            println!("mempalace-cli {}", env!("CARGO_PKG_VERSION"));
        }
        Command::Init => {
            let paths = ConfigLoader::init_default(None)?;
            let config = ConfigLoader::load_with_env(None)?;
            let cache_root = default_embedding_cache_dir();
            let provider = FastembedProvider::new(
                config.embedding_profile,
                FastembedProviderConfig::new(cache_root),
            );
            let validation = provider.startup_validation()?;
            log_startup_validation(&validation);

            log_init_outcome(
                &paths.config_file,
                &config.palace_path,
                config.embedding_profile,
                validation.status,
            );
        }
    }

    Ok(())
}

fn init_tracing(default_filter: &str) {
    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(default_filter));

    let _ = fmt().with_env_filter(filter).with_target(false).try_init();
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum Command {
    Help,
    Version,
    Init,
}

fn parse_args<I>(args: I) -> Result<Command, String>
where
    I: IntoIterator<Item = String>,
{
    let args = args.into_iter().collect::<Vec<_>>();

    match args.as_slice() {
        [] => Ok(Command::Init),
        [arg] if arg == "init" => Ok(Command::Init),
        [arg] if arg == "--help" || arg == "-h" || arg == "help" => Ok(Command::Help),
        [arg] if arg == "--version" || arg == "-V" || arg == "version" => Ok(Command::Version),
        _ => Err(format!("unrecognized arguments: {}\n\n{}", args.join(" "), usage())),
    }
}

fn usage() -> &'static str {
    concat!(
        "mempalace-cli ",
        env!("CARGO_PKG_VERSION"),
        "\n\n",
        "Usage:\n",
        "  mempalace-cli [init]\n",
        "  mempalace-cli [--help | -h]\n",
        "  mempalace-cli [--version | -V]\n"
    )
}

fn default_embedding_cache_dir() -> PathBuf {
    dirs::cache_dir()
        .unwrap_or_else(|| PathBuf::from(".cache"))
        .join("mempalace")
        .join("embeddings")
}

fn log_init_outcome(
    config_file: &std::path::Path,
    palace_path: &std::path::Path,
    embedding_profile: EmbeddingProfile,
    validation_status: StartupValidationStatus,
) {
    match validation_status {
        StartupValidationStatus::Ready => tracing::info!(
            config_file = %config_file.display(),
            palace_path = %palace_path.display(),
            embedding_profile = embedding_profile.as_str(),
            "mempalace cli foundation initialized"
        ),
        StartupValidationStatus::MissingAssets | StartupValidationStatus::PartialDownload => {
            tracing::warn!(
                config_file = %config_file.display(),
                palace_path = %palace_path.display(),
                embedding_profile = embedding_profile.as_str(),
                startup_validation = %validation_status,
                "mempalace cli foundation initialized; embedding assets must be downloaded before offline use"
            )
        }
        StartupValidationStatus::CorruptedCache => tracing::warn!(
            config_file = %config_file.display(),
            palace_path = %palace_path.display(),
            embedding_profile = embedding_profile.as_str(),
            startup_validation = %validation_status,
            "mempalace cli foundation initialized; embedding cache is corrupted and must be refreshed"
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        Command, EmbeddingProfile, StartupValidationStatus, log_init_outcome, parse_args, usage,
    };
    use std::path::Path;

    #[test]
    fn parses_default_invocation_as_init() {
        assert!(matches!(parse_args(Vec::new()), Ok(Command::Init)));
    }

    #[test]
    fn parses_help_without_init_side_effects() {
        assert!(matches!(parse_args(vec!["--help".to_owned()]), Ok(Command::Help)));
        assert!(usage().contains("Usage:"));
    }

    #[test]
    fn parses_version_without_init_side_effects() {
        assert!(matches!(parse_args(vec!["--version".to_owned()]), Ok(Command::Version)));
    }

    #[test]
    fn rejects_unknown_args() {
        assert!(matches!(
            parse_args(vec!["status".to_owned()]),
            Err(err) if err.contains("unrecognized arguments")
        ));
    }

    #[test]
    fn init_outcome_logging_branches_for_each_validation_state() {
        for status in [
            StartupValidationStatus::Ready,
            StartupValidationStatus::MissingAssets,
            StartupValidationStatus::PartialDownload,
            StartupValidationStatus::CorruptedCache,
        ] {
            log_init_outcome(
                Path::new("/tmp/config.toml"),
                Path::new("/tmp/palace"),
                EmbeddingProfile::Balanced,
                status,
            );
        }
    }
}
