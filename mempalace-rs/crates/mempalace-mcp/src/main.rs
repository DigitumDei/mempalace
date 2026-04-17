#![allow(missing_docs)]

use std::io::Write;

use mempalace_mcp::McpServer;
use tokio::io::{self, AsyncBufReadExt};

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

        writeln!(stdout, "{}", serde_json::to_string(&response)?)?;
        stdout.flush()?;
    }

    Ok(())
}
