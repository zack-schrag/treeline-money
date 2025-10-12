# Smoke Tests Deleted

**Date:** 2025-10-11
**Reason:** Smoke tests should NOT use mocks

## Why Deleted

All smoke tests in this directory were using mocks (unittest.mock.patch), which defeats the purpose of smoke testing. Smoke tests should be **true end-to-end tests** that exercise real functionality without mocking.

## What Smoke Tests Should Be

Smoke tests should:
- ✅ Run the actual CLI in a subprocess
- ✅ Use real file I/O
- ✅ Exercise real database operations (with test database)
- ✅ Test actual user workflows
- ❌ NOT use mocks
- ❌ NOT patch internal functions

## How to Implement Proper Smoke Tests

Use subprocess to run actual CLI commands:

```python
import subprocess
import tempfile
from pathlib import Path

def test_sql_command_end_to_end():
    """Test /sql command actually works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run actual CLI
        result = subprocess.run(
            ["uv", "run", "python", "-m", "treeline.cli"],
            input="/sql\nSELECT 1\n/exit\n",
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )

        assert result.returncode == 0
        assert "1 row" in result.stdout
```

## Current Status

- **Unit tests:** Comprehensive coverage with proper mocking (208 tests passing)
- **Smoke tests:** Need to be rewritten from scratch using subprocess approach
- **Priority:** Focus on unit tests first, add proper smoke tests later

## See Also

- Unit tests in `tests/unit/` - these properly use mocks for isolated testing
- Integration tests should go in `tests/integration/` (not yet implemented)
