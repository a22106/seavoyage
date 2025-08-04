# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Seavoyage is a Python package for maritime route planning and optimization, extending the `searoute` library with custom restriction zones, multiple network resolutions, and interactive visualizations.

## Development Commands

This project uses **uv** for modern Python package management. All commands should use uv for optimal performance and reliability.

### Environment Setup
```bash
# Install all dependencies including dev groups
uv sync

# Install specific dependency groups
uv sync --group dev
uv sync --group docs
uv sync --group test
uv sync --group lint

# Install in development mode
uv pip install -e .
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with specific groups
uv run --group test pytest

# Run specific test file
uv run pytest tests/test_base.py

# Run with coverage (configured in pyproject.toml)
uv run pytest

# Windows users can still use the convenience script
.\pytest.ps1
```

### Code Quality
```bash
# Run linting
uv run --group lint ruff check .

# Run formatting
uv run --group lint ruff format .

# Run type checking
uv run --group lint mypy seavoyage

# Run all quality checks
uv run --group lint ruff check . && uv run --group lint mypy seavoyage
```

### Building
```bash
# Build package
uv build

# Add new dependencies
uv add "new-package>=1.0.0"

# Add development dependencies
uv add --group dev "new-dev-package>=1.0.0"
```

### Documentation
```bash
# Build documentation
cd docs
make html
```

### Version Management
```bash
# Update version in pyproject.toml
# Follow semantic versioning: MAJOR.MINOR.PATCH
# - MAJOR: Breaking API changes
# - MINOR: New features, backwards compatible
# - PATCH: Bug fixes, backwards compatible

# Update CHANGELOG.md with:
# - Version number and date
# - Added features
# - Changed functionality
# - Fixed bugs
# - Breaking changes (if any)
```

## Architecture

### Core Components

1. **base.py**: Main API entry point containing `seavoyage()` function
2. **api.py**: New simplified API with `calculate_sea_route()`, `calculate_sea_route_simple()`, `get_quick_route()`
3. **enhanced_api.py**: Enhanced API with progress tracking and error recovery (`seavoyage_with_progress()`, `calculate_sea_route_with_recovery()`)
4. **classes/m_network.py**: Enhanced `MNetwork` class extending `searoute.Marnet` with restriction zone support
5. **modules/restriction.py**: Custom restriction zone management using global registry pattern
6. **callbacks.py**: Progress tracking system with various callback implementations
7. **retry.py**: Error recovery and retry mechanisms with configurable strategies
8. **utils/**: Modular utilities for coordinates, geojson, mapping, networks, routes, geometry, and shorelines

### Key Design Patterns

- **Extension Pattern**: MNetwork extends searoute's Marnet class
- **Global Registry**: Custom restrictions stored in global `CUSTOM_RESTRICTIONS` dictionary
- **Factory Functions**: Network resolution factories (`get_m_network_5km()`, etc.)
- **Data Embedding**: Maritime networks and shoreline data included in package
- **Callback Pattern**: Progress tracking via callback interfaces (ProgressCallback)
- **Strategy Pattern**: Configurable retry strategies (IMMEDIATE, LINEAR_BACKOFF, EXPONENTIAL_BACKOFF)
- **Configuration Objects**: RouteConfig, NetworkConfig for clean API design

### Data Flow

1. User calls `seavoyage()` with start/end coordinates
2. Function loads or creates appropriate maritime network (default 50km)
3. Applies restriction zones (built-in passages + custom restrictions)
4. Calculates route using NetworkX shortest path
5. Returns GeoJSON LineString with route details

## Important Considerations

### Python Version Issue
**CRITICAL**: Fix Python version inconsistency - `pyproject.toml` requires Python >=3.11 but classifiers include 3.9, 3.10.

### Memory Management
Large maritime networks are cached globally. Consider impact when working with multiple resolutions.

### Error Messages
Many error messages are in Korean. When modifying exceptions, ensure messages are in English for broader accessibility.

### Type Annotations
The codebase has inconsistent type hints. When adding new code or modifying existing functions, include proper type annotations.

### Changelog Management
- Maintain CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format
- Document all notable changes under appropriate sections: Added, Changed, Fixed, Deprecated, Removed, Security
- Include version number, date, and clear descriptions of changes
- Update version in pyproject.toml according to semantic versioning rules

### Testing Patterns
- Tests use pytest fixtures for common test data
- Mock network objects to avoid loading large data files
- Test both successful routes and error conditions

### Performance Considerations
- Maritime networks can be large (100MB+)
- Network loading is cached but initial load is slow
- Shapely operations on complex geometries can be expensive

## Common Tasks

### Adding a New Restriction Zone
1. Create GeoJSON file with the restriction area
2. Register using `register_custom_restriction(name, path)`
3. Pass restriction name in `restrictions` parameter

### Modifying Network Resolution
Networks are stored in `seavoyage/data/geojson/marnet/` at various resolutions (5km-100km).

### Debugging Route Issues
- Check if points are in ocean using `is_in_ocean()`
- Verify network connectivity with `MNetwork.is_valid_route()`
- Use `map_folium()` to visualize routes and restrictions

### Implementing Progress Tracking
```python
# Simple console progress
from seavoyage import SimpleProgressCallback
route = seavoyage_with_progress(start, end, progress_callback=SimpleProgressCallback())

# Custom progress handler
def my_progress(info):
    print(f"{info.percent:.1f}% - {info.message}")
    
route = seavoyage_with_progress(start, end, progress_callback=my_progress)
```

### Configuring Error Recovery
```python
from seavoyage import RouteConfig, RetryStrategy
config = RouteConfig(
    enable_retry=True,
    max_retry_attempts=3,
    retry_delay=1.0
)
route = calculate_sea_route_with_recovery(coords, config)
```

## Code Standards

### When modifying code:
- Add type hints to all function signatures
- Use descriptive variable names (avoid single letters except for well-known conventions)
- Keep functions focused on single responsibilities
- Handle exceptions with informative English messages
- Add docstrings following NumPy style guide

### Before committing:
- Run pytest to ensure all tests pass
- Check for any hardcoded paths or system-specific code
- Verify no sensitive data is included
- Update CHANGELOG.md with notable changes
- Follow semantic versioning for version updates