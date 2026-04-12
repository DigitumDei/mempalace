#![allow(missing_docs)]

use std::env;

use mempalace_config::ConfigLoader;
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

            tracing::info!(
                config_file = %paths.config_file.display(),
                palace_path = %config.palace_path.display(),
                embedding_profile = config.embedding_profile.as_str(),
                "mempalace cli foundation initialized"
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

#[cfg(test)]
mod tests {
    use super::{Command, parse_args, usage};

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
}
