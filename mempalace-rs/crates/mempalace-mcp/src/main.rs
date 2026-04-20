#![allow(missing_docs)]

use mempalace_config::{ConfigLoader, MempalaceConfig};
use mempalace_mcp::{DeterministicStubProvider, McpServer, serve_transport};
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

        let server = McpServer::from_default_config(None).await?;
        serve_transport(&server, BufReader::new(io::stdin()), io::stdout()).await
    })
}

fn build_runtime(config: &MempalaceConfig) -> std::io::Result<tokio::runtime::Runtime> {
    if !config.low_cpu.enabled {
        return tokio::runtime::Runtime::new();
    }

    tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .worker_threads(config.low_cpu.worker_threads)
        .max_blocking_threads(config.low_cpu.max_blocking_threads)
        .build()
}
