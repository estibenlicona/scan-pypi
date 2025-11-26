# Testing Guide

## Overview

The project includes comprehensive unit and integration tests organized by testing layer.

## Test Organization

### Unit Tests (`tests/unit/`)

Tests for individual components and domain logic:

- **`test_license_extraction.py`** - License detection from multiple sources (PyPI, classifiers, expressions)
- **`test_license_from_sources.py`** - License extraction from specific data sources
- **`test_deduplication.py`** - Package deduplication logic (name@version keys)
- **`test_dto_conversion.py`** - Data transfer object conversions
- **`test_package_sorting.py`** - Package ordering and sorting logic

### Integration Tests (`tests/integration/`)

Tests for complete workflows and cross-component interactions:

- **`test_approval_integration.py`** - End-to-end approval engine with business rules
- **`test_package_sorting_versions.py`** - Full package sorting with version handling
- **`test_xlsx_display.py`** - Excel report generation with formatting
- **`test_xlsx_styling.py`** - Excel styling (colors, fonts, layouts)
- **`test_hexagonal_architecture.py`** - Hexagonal architecture compliance

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run unit tests only:
```bash
pytest tests/unit/
```

### Run integration tests only:
```bash
pytest tests/integration/
```

### Run specific test:
```bash
pytest tests/unit/test_deduplication.py
```

### Run with coverage:
```bash
pytest tests/ --cov=src
```

## Test Coverage

Current coverage includes:
- ✅ License extraction (4-tier cascade)
- ✅ Retry policy with exponential backoff
- ✅ Package deduplication (2 levels)
- ✅ Root library ordering
- ✅ Excel styling (pastel colors)
- ✅ Approval engine logic
- ✅ DTO conversions

## Key Testing Patterns

### 1. License Extraction Tests
Validates the 4-level cascade:
1. PyPI direct license field
2. License expression parsing
3. Classifier extraction
4. GitHub repository fallback

### 2. Deduplication Tests
Verifies that duplicate packages are eliminated using `{name}@{version}` keys at:
- Domain layer (DependencyGraph)
- Adapter layer (XLSXReportAdapter)

### 3. Integration Tests
Tests complete workflows from requirements.txt → Snyk → PyPI enrichment → Excel generation

## Maintenance

When modifying core logic:
1. Update relevant unit tests first
2. Run `pytest tests/unit/` to verify
3. Run `pytest tests/integration/` to ensure cross-component compatibility
4. Run full test suite before committing

