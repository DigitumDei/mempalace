use tracing_subscriber::{EnvFilter, fmt};

/// Initialize tracing for binaries and tests that want the shared setup.
pub fn init_tracing(default_filter: &str) {
    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(default_filter));

    let _ = fmt().with_env_filter(filter).with_target(false).try_init();
}
