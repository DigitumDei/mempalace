#![allow(missing_docs)]

use mempalace_config::{ConfigLoader, build_runtime};
use mempalace_mcp::{DeterministicStubProvider, McpServer, default_provider, serve_transport};
use tokio::io::{self, BufReader};

fn main() -> Result<(), Box<dyn std::error::Error>> {
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
