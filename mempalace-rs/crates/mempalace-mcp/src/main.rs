#![allow(missing_docs)]

use mempalace_mcp::McpServer;
use tokio::io::{self, AsyncBufReadExt, AsyncWriteExt};

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let server = McpServer::from_default_config(None).await?;
    let mut lines = io::BufReader::new(io::stdin()).lines();
    let mut stdout = io::stdout();

    while let Some(line) = lines.next_line().await? {
        if line.trim().is_empty() {
            continue;
        }

        let response = server.handle_line(&line).await;
        if response.is_null() {
            continue;
        }

        let response = serde_json::to_string(&response)?;
        stdout.write_all(response.as_bytes()).await?;
        stdout.write_all(b"\n").await?;
        stdout.flush().await?;
    }

    Ok(())
}
