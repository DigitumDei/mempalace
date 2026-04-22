#![allow(missing_docs)]

use std::ffi::OsString;

use mempalace_config::{ConfigLoader, build_runtime};
use mempalace_mcp::{DeterministicStubProvider, McpServer, default_provider, serve_transport};
use tokio::io::{self, BufReader};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    if let Some(output) = early_output(std::env::args_os().skip(1)) {
        print!("{output}");
        return Ok(());
    }

    let config = ConfigLoader::load_with_env(None)?;
    build_runtime(&config)?.block_on(async move {
        if std::env::var_os("MEMPALACE_STUB_EMBEDDINGS").is_some() {
            let server = McpServer::from_parts(
                config.clone(),
                DeterministicStubProvider::new(config.embedding_profile),
            )
            .await?;
            return serve_transport(&server, BufReader::new(io::stdin()), io::stdout()).await;
        }

        let server =
            McpServer::from_parts(config.clone(), default_provider(config.embedding_profile)?)
                .await?;
        serve_transport(&server, BufReader::new(io::stdin()), io::stdout()).await
    })
}

fn early_output<I, S>(args: I) -> Option<&'static str>
where
    I: IntoIterator<Item = S>,
    S: Into<OsString>,
{
    let mut args = args.into_iter().map(Into::into);
    let first = args.next()?;
    if args.next().is_some() {
        return None;
    }

    match first.to_str() {
        Some("--help") | Some("-h") => Some(help_text()),
        Some("--version") | Some("-V") => Some(version_text()),
        _ => None,
    }
}

fn help_text() -> &'static str {
    concat!(
        "MemPalace MCP stdio server\n\n",
        "Usage: mempalace-mcp\n\n",
        "Options:\n",
        "  -h, --help     Print help\n",
        "  -V, --version  Print version\n",
    )
}

fn version_text() -> &'static str {
    concat!("mempalace-mcp ", env!("CARGO_PKG_VERSION"), "\n")
}

#[cfg(test)]
mod tests {
    use super::{early_output, help_text, version_text};

    #[test]
    fn help_and_version_short_circuit_before_startup() {
        assert_eq!(early_output(["--help"]), Some(help_text()));
        assert_eq!(early_output(["-h"]), Some(help_text()));
        assert_eq!(early_output(["--version"]), Some(version_text()));
        assert_eq!(early_output(["-V"]), Some(version_text()));
        assert_eq!(early_output(["--help", "--version"]), None);
        assert_eq!(early_output(std::iter::empty::<&str>()), None);
        assert_eq!(early_output(["--unknown"]), None);
    }
}
