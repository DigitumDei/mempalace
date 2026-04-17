#![allow(missing_docs)]

use mempalace_mcp::{McpServer, serve_transport};
use tokio::io::{self, BufReader};

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let server = McpServer::from_default_config(None).await?;
    serve_transport(&server, BufReader::new(io::stdin()), io::stdout()).await
}
