"""Tests for chart configuration storage and parsing."""

import pytest
from pathlib import Path
import tempfile
from treeline.domain import ChartConfig
from treeline.commands.chart_config import (
    parse_chart_config,
    serialize_chart_config,
    validate_chart_name,
)
from treeline.infra.file_storage import FileChartStorage


class TestChartConfigParsing:
    """Tests for parsing and serializing .tl chart config files."""

    def test_parse_simple_line_chart(self):
        """Test parsing a simple line chart configuration."""
        config_text = """# Monthly Spending Trend

## Query
```sql
SELECT
  date_trunc('month', transaction_date)::DATE as month,
  SUM(amount) as spending
FROM transactions
WHERE amount < 0
GROUP BY month
ORDER BY month
```

## Chart
type: line
x_column: month
y_column: spending
title: Monthly Spending Trend
color: blue
"""
        config = parse_chart_config(config_text)

        assert config is not None
        assert config.name == "Monthly Spending Trend"
        assert config.chart_type == "line"
        assert config.x_column == "month"
        assert config.y_column == "spending"
        assert config.title == "Monthly Spending Trend"
        assert config.color == "blue"
        assert "SELECT" in config.query
        assert "date_trunc" in config.query

    def test_parse_bar_chart_with_optional_fields(self):
        """Test parsing bar chart with optional xlabel."""
        config_text = """# Category Spending

## Query
```sql
SELECT category, SUM(amount) as total
FROM transactions
GROUP BY category
```

## Chart
type: bar
x_column: category
y_column: total
title: Spending by Category
xlabel: Amount ($)
color: green
"""
        config = parse_chart_config(config_text)

        assert config.chart_type == "bar"
        assert config.xlabel == "Amount ($)"
        assert config.color == "green"

    def test_serialize_line_chart(self):
        """Test serializing a line chart configuration."""
        config = ChartConfig(
            name="Monthly Spending",
            query="SELECT month, amount FROM spending",
            chart_type="line",
            x_column="month",
            y_column="amount",
            title="Monthly Spending Trend",
            color="blue",
        )

        serialized = serialize_chart_config(config)

        assert "# Monthly Spending" in serialized
        assert "```sql" in serialized
        assert "SELECT month, amount FROM spending" in serialized
        assert "type: line" in serialized
        assert "x_column: month" in serialized
        assert "y_column: amount" in serialized
        assert "title: Monthly Spending Trend" in serialized
        assert "color: blue" in serialized

    def test_round_trip_parsing(self):
        """Test that serializing and parsing returns same config."""
        original = ChartConfig(
            name="Test Chart",
            query="SELECT a, b FROM t",
            chart_type="scatter",
            x_column="a",
            y_column="b",
            title="Test",
            color="red",
        )

        serialized = serialize_chart_config(original)
        parsed = parse_chart_config(serialized)

        assert parsed.name == original.name
        assert parsed.query.strip() == original.query.strip()
        assert parsed.chart_type == original.chart_type
        assert parsed.x_column == original.x_column
        assert parsed.y_column == original.y_column
        assert parsed.title == original.title
        assert parsed.color == original.color

    def test_parse_chart_with_description(self):
        """Test parsing chart config with optional description."""
        config_text = """# Weekly Trends

Weekly spending analysis for the last 6 months.

## Query
```sql
SELECT week, total FROM weekly_spending
```

## Chart
type: line
x_column: week
y_column: total
title: Weekly Spending
color: cyan
"""
        config = parse_chart_config(config_text)

        assert config.description == "Weekly spending analysis for the last 6 months."

    def test_parse_invalid_config_missing_query(self):
        """Test parsing fails gracefully on invalid config."""
        config_text = """# Bad Config

## Chart
type: line
x_column: x
y_column: y
"""
        config = parse_chart_config(config_text)
        assert config is None  # Should return None for invalid config


class TestFileChartStorage:
    """Tests for FileChartStorage abstraction."""

    def test_save_and_load_chart_config(self):
        """Test saving and loading a chart configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            charts_dir = Path(tmpdir)
            store = FileChartStorage(charts_dir)

            config = ChartConfig(
                name="test_chart",
                query="SELECT x, y FROM data",
                chart_type="line",
                x_column="x",
                y_column="y",
                title="Test Chart",
                color="blue",
            )

            # Save
            result = store.save("test_chart", config)
            assert result is True

            # Load
            loaded = store.load("test_chart")
            assert loaded is not None
            assert loaded.name == "test_chart"
            assert loaded.query.strip() == "SELECT x, y FROM data"
            assert loaded.chart_type == "line"

    def test_list_chart_configs(self):
        """Test listing all chart configurations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            charts_dir = Path(tmpdir)
            store = FileChartStorage(charts_dir)

            # Save multiple configs
            for name in ["chart1", "chart2", "chart3"]:
                config = ChartConfig(
                    name=name,
                    query=f"SELECT * FROM {name}",
                    chart_type="bar",
                    x_column="x",
                    y_column="y",
                    title=name,
                )
                store.save(name, config)

            # List
            charts = store.list()
            assert len(charts) == 3
            assert "chart1" in charts
            assert "chart2" in charts
            assert "chart3" in charts

    def test_delete_chart_config(self):
        """Test deleting a chart configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            charts_dir = Path(tmpdir)
            store = FileChartStorage(charts_dir)

            config = ChartConfig(
                name="to_delete",
                query="SELECT x, y FROM data",
                chart_type="line",
                x_column="x",
                y_column="y",
                title="Delete Me",
            )

            # Save and delete
            store.save("to_delete", config)
            assert "to_delete" in store.list()

            result = store.delete("to_delete")
            assert result is True
            assert "to_delete" not in store.list()

    def test_overwrite_existing_chart(self):
        """Test overwriting an existing chart configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            charts_dir = Path(tmpdir)
            store = FileChartStorage(charts_dir)

            # Save original
            original = ChartConfig(
                name="chart",
                query="SELECT a FROM t1",
                chart_type="bar",
                x_column="a",
                y_column="b",
                title="Original",
            )
            store.save("chart", original)

            # Overwrite
            updated = ChartConfig(
                name="chart",
                query="SELECT x FROM t2",
                chart_type="line",
                x_column="x",
                y_column="y",
                title="Updated",
            )
            store.save("chart", updated)

            # Load and verify
            loaded = store.load("chart")
            assert loaded.query.strip() == "SELECT x FROM t2"
            assert loaded.title == "Updated"

    def test_validate_chart_name(self):
        """Test chart name validation."""
        # Valid names
        assert validate_chart_name("chart_1") is True
        assert validate_chart_name("my_chart") is True
        assert validate_chart_name("Chart123") is True

        # Invalid names
        assert validate_chart_name("chart-1") is False  # hyphen
        assert validate_chart_name("my chart") is False  # space
        assert validate_chart_name("chart!") is False  # special char
        assert validate_chart_name("") is False  # empty
