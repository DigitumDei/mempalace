use std::path::PathBuf;

use mempalace_config::MempalaceConfig;
use mempalace_core::EmbeddingProfile;
use mempalace_embeddings::{
    EmbeddingProvider, EmbeddingRequest, EmbeddingResponse, StartupValidation,
    StartupValidationStatus,
};
use mempalace_mcp::{McpServer, serve_transport};
use tempfile::TempDir;
use tokio::io::{AsyncReadExt, AsyncWriteExt, BufReader};

#[derive(Debug, Clone)]
struct StubProvider {
    profile: EmbeddingProfile,
}

impl StubProvider {
    fn vector_for(&self, text: &str) -> Vec<f32> {
        let lower = text.to_ascii_lowercase();
        let seed = if ["auth", "migration", "parity"].iter().any(|token| lower.contains(token)) {
            [1.0, 0.0, 0.0, 0.0]
        } else if ["session", "diary", "ops"].iter().any(|token| lower.contains(token)) {
            [0.0, 1.0, 0.0, 0.0]
        } else if ["rust", "cli"].iter().any(|token| lower.contains(token)) {
            [0.0, 0.0, 1.0, 0.0]
        } else {
            [0.0, 0.0, 0.0, 1.0]
        };
        let mut values = Vec::with_capacity(self.profile.metadata().dimensions);
        while values.len() < self.profile.metadata().dimensions {
            values.extend(seed);
        }
        values.truncate(self.profile.metadata().dimensions);
        values
    }
}

impl EmbeddingProvider for StubProvider {
    fn profile(&self) -> &'static mempalace_core::EmbeddingProfileMetadata {
        self.profile.metadata()
    }

    fn startup_validation(&self) -> mempalace_embeddings::Result<StartupValidation> {
        Ok(StartupValidation {
            status: StartupValidationStatus::Ready,
            cache_root: PathBuf::from("/tmp/stub"),
            model_id: self.profile.metadata().model_id,
            detail: "stub".to_owned(),
        })
    }

    fn embed(
        &mut self,
        request: &EmbeddingRequest,
    ) -> mempalace_embeddings::Result<EmbeddingResponse> {
        EmbeddingResponse::from_vectors(
            request.texts().iter().map(|text| self.vector_for(text)).collect(),
            self.profile.metadata().dimensions,
            self.profile,
            self.profile.metadata().model_id,
        )
    }
}

async fn test_server(tempdir: &TempDir) -> McpServer<StubProvider> {
    let config = MempalaceConfig {
        schema_version: 1,
        collection_name: "mempalace_drawers".to_owned(),
        palace_path: tempdir.path().join("palace"),
        embedding_profile: EmbeddingProfile::Balanced,
    };
    McpServer::from_parts(config, StubProvider { profile: EmbeddingProfile::Balanced })
        .await
        .unwrap()
}

#[tokio::test]
async fn server_handles_initialize_and_tools_list_over_transport() {
    let tempdir = TempDir::new().unwrap();
    let server = test_server(&tempdir).await;
    let input = concat!(
        "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}\n",
        "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{}}\n"
    );

    let (client, server_stream) = tokio::io::duplex(8_192);
    let (reader_half, writer_half) = tokio::io::split(server_stream);
    let task = tokio::spawn(async move {
        serve_transport(&server, BufReader::new(reader_half), writer_half).await.unwrap();
    });

    let (mut client_reader, mut client_writer) = tokio::io::split(client);
    client_writer.write_all(input.as_bytes()).await.unwrap();
    client_writer.shutdown().await.unwrap();

    let mut output = String::new();
    client_reader.read_to_string(&mut output).await.unwrap();
    task.await.unwrap();

    let lines = output.lines().collect::<Vec<_>>();
    let initialize: serde_json::Value = serde_json::from_str(lines[0]).unwrap();
    let tools: serde_json::Value = serde_json::from_str(lines[1]).unwrap();

    assert_eq!(initialize["result"]["protocolVersion"], "2024-11-05");
    assert!(
        tools["result"]["tools"]
            .as_array()
            .unwrap()
            .iter()
            .any(|tool| tool["name"] == "mempalace_status")
    );
}

#[tokio::test]
async fn server_returns_parse_error_for_invalid_json() {
    let tempdir = TempDir::new().unwrap();
    let server = test_server(&tempdir).await;
    let (client, server_stream) = tokio::io::duplex(4_096);
    let (reader_half, writer_half) = tokio::io::split(server_stream);
    let task = tokio::spawn(async move {
        serve_transport(&server, BufReader::new(reader_half), writer_half).await.unwrap();
    });

    let (mut client_reader, mut client_writer) = tokio::io::split(client);
    client_writer.write_all(b"{\n").await.unwrap();
    client_writer.shutdown().await.unwrap();

    let mut output = String::new();
    client_reader.read_to_string(&mut output).await.unwrap();
    task.await.unwrap();

    let response: serde_json::Value = serde_json::from_str(output.trim()).unwrap();
    assert_eq!(response["error"]["code"], -32700);
}

#[tokio::test]
async fn server_handles_embedding_backed_tool_calls_over_transport() {
    let tempdir = TempDir::new().unwrap();
    let server = test_server(&tempdir).await;
    let input = concat!(
        "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"mempalace_add_drawer\",\"arguments\":{\"wing\":\"wing_code\",\"room\":\"backend\",\"content\":\"Rust MCP transport coverage note\",\"source_file\":\"transport.md\",\"added_by\":\"stdio-test\"}}}\n",
        "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"mempalace_check_duplicate\",\"arguments\":{\"content\":\"Rust MCP transport coverage note\",\"threshold\":0.9}}}\n",
        "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"mempalace_diary_write\",\"arguments\":{\"agent_name\":\"Transport Bot\",\"entry\":\"SESSION:2026-04-17|transport.coverage\",\"topic\":\"transport\"}}}\n",
        "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"mempalace_diary_read\",\"arguments\":{\"agent_name\":\"Transport Bot\",\"last_n\":1}}}\n"
    );

    let (client, server_stream) = tokio::io::duplex(16_384);
    let (reader_half, writer_half) = tokio::io::split(server_stream);
    let task = tokio::spawn(async move {
        serve_transport(&server, BufReader::new(reader_half), writer_half).await.unwrap();
    });

    let (mut client_reader, mut client_writer) = tokio::io::split(client);
    client_writer.write_all(input.as_bytes()).await.unwrap();
    client_writer.shutdown().await.unwrap();

    let mut output = String::new();
    client_reader.read_to_string(&mut output).await.unwrap();
    task.await.unwrap();

    let lines = output.lines().collect::<Vec<_>>();
    assert_eq!(lines.len(), 4);

    let add: serde_json::Value = serde_json::from_str(lines[0]).unwrap();
    let duplicate: serde_json::Value = serde_json::from_str(lines[1]).unwrap();
    let diary_write: serde_json::Value = serde_json::from_str(lines[2]).unwrap();
    let diary_read: serde_json::Value = serde_json::from_str(lines[3]).unwrap();

    let add_payload = mempalace_mcp::decode_tool_payload(&add).unwrap();
    assert_eq!(add_payload["success"], true);

    let duplicate_payload = mempalace_mcp::decode_tool_payload(&duplicate).unwrap();
    assert_eq!(duplicate_payload["is_duplicate"], true);
    assert!(!duplicate_payload["matches"].as_array().unwrap().is_empty());

    let diary_write_payload = mempalace_mcp::decode_tool_payload(&diary_write).unwrap();
    assert_eq!(diary_write_payload["success"], true);

    let diary_read_payload = mempalace_mcp::decode_tool_payload(&diary_read).unwrap();
    assert_eq!(diary_read_payload["agent"], "Transport Bot");
    assert_eq!(diary_read_payload["showing"], 1);
    assert_eq!(diary_read_payload["entries"][0]["topic"], "transport");
}
