# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-08-04

### Added
- **Progress Tracking System**: New progress callback functionality for monitoring route calculation progress
  - `ProgressCallback` abstract base class for custom implementations
  - `SimpleProgressCallback` for console output with progress percentage
  - `FunctionProgressCallback` for custom progress handling functions
  - `ProgressTracker` utility class for managing progress across calculation stages
  - Progress stages: INITIALIZATION, NETWORK_LOADING, RESTRICTION_PROCESSING, PATHFINDING, ROUTE_OPTIMIZATION, FINALIZATION

- **Error Recovery and Retry Mechanisms**: Comprehensive error handling and automatic retry capabilities
  - `RetryHandler` with configurable retry strategies (IMMEDIATE, LINEAR_BACKOFF, EXPONENTIAL_BACKOFF)
  - `ErrorRecoveryHandler` for comprehensive error recovery with multiple strategies
  - `FallbackHandler` for trying alternative calculation methods
  - Configurable retry attempts, delays, and backoff strategies
  - Support for partial route calculation on failure

- **Enhanced API Functions**:
  - `seavoyage_with_progress()`: Enhanced version of seavoyage with progress tracking and retry
  - `calculate_sea_route_with_recovery()`: High-level API with integrated error recovery
  - Progress callback support in `RouteConfig` data model
  - Retry configuration options in route calculation

### Changed
- Updated `RouteConfig` model to include progress and retry settings:
  - `progress_callback`: Optional callback for progress updates
  - `enable_retry`: Toggle automatic retry on failures
  - `max_retry_attempts`: Maximum number of retry attempts
  - `retry_delay`: Initial delay between retries
  - `enable_partial_routes`: Enable partial route calculation

### Fixed
- Improved error handling with more descriptive error messages
- Better handling of network connectivity issues

### Documentation
- Added comprehensive examples for progress tracking and retry mechanisms
- Updated README with new features and usage examples
- Added demo script showcasing all new features

## [0.1.20] - Previous version
- Base functionality for sea route calculation
- Custom restriction zones
- Multiple network resolutions
- Folium-based visualization