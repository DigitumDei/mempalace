#![allow(missing_docs)]

use mempalace_config::ConfigLoader;
use mempalace_mcp::{DeterministicStubProvider, McpServer, serve_transport};
use tokio::io::{self, BufReader};

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::var_os("MEMPALACE_STUB_EMBEDDINGS").is_some() {
        let config = ConfigLoader::load_with_env(None)?;
        let server = McpServer::from_parts(
            config.clone(),
            DeterministicStubProvider::new(config.embedding_profile),
        )
        .await?;
        return serve_transport(&server, BufReader::new(io::stdin()), io::stdout()).await;
    }

    let server = McpServer::from_default_config(None).await?;
    serve_transport(&server, BufReader::new(io::stdin()), io::stdout()).await
}
