use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

fn unique_base_dir() -> PathBuf {
    let nanos = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    std::env::temp_dir().join(format!("mempalace-mcp-stdio-{nanos}"))
}

#[test]
fn server_handles_initialize_and_tools_list_over_stdio() {
    let base_dir = unique_base_dir();
    std::fs::create_dir_all(&base_dir).unwrap();

    let mut child = Command::new(env!("CARGO_BIN_EXE_mempalace-mcp"))
        .env("HOME", &base_dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();

    let mut stdin = child.stdin.take().unwrap();
    writeln!(
        stdin,
        "{}",
        serde_json::json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}})
    )
    .unwrap();
    writeln!(
        stdin,
        "{}",
        serde_json::json!({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
    )
    .unwrap();
    drop(stdin);

    let stdout = child.stdout.take().unwrap();
    let lines = BufReader::new(stdout).lines().collect::<Result<Vec<_>, _>>().unwrap();
    let initialize: serde_json::Value = serde_json::from_str(&lines[0]).unwrap();
    let tools: serde_json::Value = serde_json::from_str(&lines[1]).unwrap();

    assert_eq!(initialize["result"]["protocolVersion"], "2024-11-05");
    assert!(
        tools["result"]["tools"]
            .as_array()
            .unwrap()
            .iter()
            .any(|tool| tool["name"] == "mempalace_status")
    );
    assert!(child.wait().unwrap().success());
}

#[test]
fn server_returns_parse_error_for_invalid_json() {
    let base_dir = unique_base_dir();
    std::fs::create_dir_all(&base_dir).unwrap();

    let mut child = Command::new(env!("CARGO_BIN_EXE_mempalace-mcp"))
        .env("HOME", &base_dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();

    let mut stdin = child.stdin.take().unwrap();
    writeln!(stdin, "{{").unwrap();
    drop(stdin);

    let stdout = child.stdout.take().unwrap();
    let line = BufReader::new(stdout).lines().next().unwrap().unwrap();
    let response: serde_json::Value = serde_json::from_str(&line).unwrap();
    assert_eq!(response["error"]["code"], -32700);
    assert!(child.wait().unwrap().success());
}
