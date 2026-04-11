use std::env;
use std::fs;
use std::path::{Path, PathBuf};

use mempalace_core::{EmbeddingProfile, MempalaceError, Result};
use serde::{Deserialize, Serialize};

pub const DEFAULT_BASE_DIR: &str = "~/.mempalace";
pub const DEFAULT_COLLECTION_NAME: &str = "mempalace_drawers";
const CONFIG_FILE_NAME: &str = "config.json";
const PROJECT_CONFIG_FILE_NAME: &str = "mempalace.yaml";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolvedPaths {
    pub base_dir: PathBuf,
    pub palace_dir: PathBuf,
    pub config_file: PathBuf,
    pub people_map_file: PathBuf,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ConfigFileV1 {
    pub version: u32,
    #[serde(default)]
    pub palace_path: Option<String>,
    #[serde(default = "default_collection_name")]
    pub collection_name: String,
    #[serde(default)]
    pub embedding_profile: Option<EmbeddingProfile>,
}

impl Default for ConfigFileV1 {
    fn default() -> Self {
        Self {
            version: 1,
            palace_path: Some(default_palace_path()),
            collection_name: default_collection_name(),
            embedding_profile: Some(EmbeddingProfile::Balanced),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MempalaceConfig {
    pub schema_version: u32,
    pub collection_name: String,
    pub palace_path: PathBuf,
    pub embedding_profile: EmbeddingProfile,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProjectConfig {
    pub wing: String,
}

pub struct ConfigLoader;

impl ConfigLoader {
    pub fn load_with_env(base_dir_override: Option<&Path>) -> Result<MempalaceConfig> {
        Self::load_from_sources(
            base_dir_override,
            env::var("MEMPALACE_PALACE_PATH").ok().or_else(|| env::var("MEMPAL_PALACE_PATH").ok()),
            env::var("MEMPALACE_EMBEDDING_PROFILE").ok(),
        )
    }

    fn load_from_sources(
        base_dir_override: Option<&Path>,
        palace_path_override: Option<String>,
        profile_override: Option<String>,
    ) -> Result<MempalaceConfig> {
        let paths = resolve_paths(base_dir_override)?;
        let file = read_config_file(&paths.config_file)?;

        let palace_path = palace_path_override
            .or(file.palace_path)
            .unwrap_or_else(|| paths.palace_dir.display().to_string());

        Ok(MempalaceConfig {
            schema_version: file.version,
            collection_name: file.collection_name,
            palace_path: expand_path(&palace_path)?,
            embedding_profile: resolve_profile(profile_override, file.embedding_profile)?,
        })
    }

    pub fn init_default(base_dir_override: Option<&Path>) -> Result<ResolvedPaths> {
        let paths = resolve_paths(base_dir_override)?;
        fs::create_dir_all(&paths.base_dir).map_err(|source| MempalaceError::ConfigWrite {
            path: paths.base_dir.clone(),
            source,
        })?;

        if !paths.config_file.exists() {
            let default_file = ConfigFileV1 {
                palace_path: Some(paths.palace_dir.display().to_string()),
                ..ConfigFileV1::default()
            };
            let body = serde_json::to_string_pretty(&default_file).map_err(|err| {
                MempalaceError::ConfigParse {
                    path: paths.config_file.clone(),
                    message: err.to_string(),
                }
            })?;
            fs::write(&paths.config_file, body).map_err(|source| MempalaceError::ConfigWrite {
                path: paths.config_file.clone(),
                source,
            })?;
        }

        Ok(paths)
    }

    pub fn load_project_config(path: &Path) -> Result<ProjectConfig> {
        let config_path = path.join(PROJECT_CONFIG_FILE_NAME);
        let body = fs::read_to_string(&config_path)
            .map_err(|source| MempalaceError::ConfigRead { path: config_path.clone(), source })?;
        serde_yaml::from_str(&body).map_err(|err| MempalaceError::ConfigParse {
            path: config_path,
            message: err.to_string(),
        })
    }
}

fn resolve_paths(base_dir_override: Option<&Path>) -> Result<ResolvedPaths> {
    let base_dir = match base_dir_override {
        Some(path) => path.to_path_buf(),
        None => expand_path(DEFAULT_BASE_DIR)?,
    };

    Ok(ResolvedPaths {
        palace_dir: base_dir.join("palace"),
        config_file: base_dir.join(CONFIG_FILE_NAME),
        people_map_file: base_dir.join("people_map.json"),
        base_dir,
    })
}

fn read_config_file(path: &Path) -> Result<ConfigFileV1> {
    if !path.exists() {
        return Ok(ConfigFileV1::default());
    }

    let body = fs::read_to_string(path)
        .map_err(|source| MempalaceError::ConfigRead { path: path.to_path_buf(), source })?;

    let file: ConfigFileV1 = serde_json::from_str(&body).map_err(|err| {
        MempalaceError::ConfigParse { path: path.to_path_buf(), message: err.to_string() }
    })?;

    if file.version != 1 {
        return Err(MempalaceError::UnsupportedConfigVersion(file.version));
    }

    Ok(file)
}

fn resolve_profile(
    env_profile: Option<String>,
    file_profile: Option<EmbeddingProfile>,
) -> Result<EmbeddingProfile> {
    if let Some(profile) = env_profile {
        return profile.parse();
    }

    Ok(file_profile.unwrap_or_default())
}

fn default_collection_name() -> String {
    DEFAULT_COLLECTION_NAME.to_owned()
}

fn default_palace_path() -> String {
    format!("{DEFAULT_BASE_DIR}/palace")
}

fn expand_path(value: &str) -> Result<PathBuf> {
    if let Some(stripped) = value.strip_prefix("~/") {
        let home = dirs::home_dir().ok_or(MempalaceError::MissingHomeDirectory)?;
        return Ok(home.join(stripped));
    }

    if value == "~" {
        return dirs::home_dir().ok_or(MempalaceError::MissingHomeDirectory);
    }

    Ok(PathBuf::from(value))
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    use mempalace_core::EmbeddingProfile;

    use super::{ConfigLoader, DEFAULT_COLLECTION_NAME};

    fn temp_dir() -> PathBuf {
        let nanos = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
        std::env::temp_dir().join(format!("mempalace-rs-config-{nanos}"))
    }

    #[test]
    fn init_and_load_defaults_round_trip() {
        let base = temp_dir();
        let paths = ConfigLoader::init_default(Some(&base)).unwrap();
        let config = ConfigLoader::load_with_env(Some(&base)).unwrap();

        assert_eq!(paths.config_file, base.join("config.json"));
        assert_eq!(config.schema_version, 1);
        assert_eq!(config.collection_name, DEFAULT_COLLECTION_NAME);
        assert_eq!(config.embedding_profile, EmbeddingProfile::Balanced);
        assert_eq!(config.palace_path, base.join("palace"));

        fs::remove_dir_all(base).unwrap();
    }

    #[test]
    fn env_overrides_palace_path_and_profile() {
        let base = temp_dir();
        ConfigLoader::init_default(Some(&base)).unwrap();

        let config = ConfigLoader::load_from_sources(
            Some(&base),
            Some("/tmp/custom-palace".to_owned()),
            Some("low_cpu".to_owned()),
        )
        .unwrap();

        assert_eq!(config.palace_path, PathBuf::from("/tmp/custom-palace"));
        assert_eq!(config.embedding_profile, EmbeddingProfile::LowCpu);

        fs::remove_dir_all(base).unwrap();
    }

    #[test]
    fn project_config_parses_yaml() {
        let base = temp_dir();
        fs::create_dir_all(&base).unwrap();
        fs::write(base.join("mempalace.yaml"), "wing: project_alpha\n").unwrap();

        let config = ConfigLoader::load_project_config(&base).unwrap();
        assert_eq!(config.wing, "project_alpha");

        fs::remove_dir_all(base).unwrap();
    }

    #[test]
    fn rejects_unsupported_schema_version() {
        let base = temp_dir();
        fs::create_dir_all(&base).unwrap();
        fs::write(
            base.join("config.json"),
            r#"{"version":2,"collection_name":"mempalace_drawers"}"#,
        )
        .unwrap();

        let err = ConfigLoader::load_with_env(Some(&base)).unwrap_err();
        assert!(err.to_string().contains("unsupported config schema version"));

        fs::remove_dir_all(base).unwrap();
    }
}
