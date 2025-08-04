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

## Architecture

### Core Components

1. **base.py**: Main API entry point containing `seavoyage()` function
2. **classes/m_network.py**: Enhanced `MNetwork` class extending `searoute.Marnet` with restriction zone support
3. **modules/restriction.py**: Custom restriction zone management using global registry pattern
4. **utils/**: Modular utilities for coordinates, geojson, mapping, networks, routes, geometry, and shorelines

### Key Design Patterns

- **Extension Pattern**: MNetwork extends searoute's Marnet class
- **Global Registry**: Custom restrictions stored in global `CUSTOM_RESTRICTIONS` dictionary
- **Factory Functions**: Network resolution factories (`get_m_network_5km()`, etc.)
- **Data Embedding**: Maritime networks and shoreline data included in package

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