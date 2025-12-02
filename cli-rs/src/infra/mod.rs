//! Infrastructure implementations.

pub mod duckdb_repo;
pub mod demo_provider;
pub mod simplefin;
pub mod csv_provider;

pub use duckdb_repo::DuckDBRepository;
pub use demo_provider::DemoDataProvider;
pub use simplefin::SimpleFINProvider;
pub use csv_provider::{CSVProvider, ColumnMapping};
