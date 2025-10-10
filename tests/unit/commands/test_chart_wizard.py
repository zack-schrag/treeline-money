"""Tests for chart wizard functionality."""

import pytest
from treeline.commands.chart_wizard import (
    validate_chart_data,
    create_chart_from_config,
    ChartWizardConfig,
)


class TestChartWizardValidation:
    """Tests for chart data validation logic."""

    def test_validate_empty_results(self):
        """Test validation fails for empty query results."""
        columns = ["month", "amount"]
        rows = []

        error = validate_chart_data(rows, columns, "month", "amount")
        assert error is not None
        assert "no results" in error.lower() or "empty" in error.lower()

    def test_validate_column_not_in_results(self):
        """Test validation fails when column doesn't exist."""
        columns = ["month", "amount"]
        rows = [["2024-01", 100], ["2024-02", 200]]

        # X column doesn't exist
        error = validate_chart_data(rows, columns, "invalid_col", "amount")
        assert error is not None
        assert "invalid_col" in error

        # Y column doesn't exist
        error = validate_chart_data(rows, columns, "month", "invalid_col")
        assert error is not None
        assert "invalid_col" in error

    def test_validate_non_numeric_y_column(self):
        """Test validation fails when Y column contains non-numeric data."""
        columns = ["month", "label"]
        rows = [["2024-01", "label1"], ["2024-02", "label2"]]

        error = validate_chart_data(rows, columns, "month", "label")
        assert error is not None
        assert "numeric" in error.lower()

    def test_validate_single_row_for_line_chart(self):
        """Test validation warns for single row with line chart."""
        columns = ["month", "amount"]
        rows = [["2024-01", 100]]

        error = validate_chart_data(rows, columns, "month", "amount", chart_type="line")
        assert error is not None
        assert "single" in error.lower() or "one" in error.lower()

    def test_validate_success(self):
        """Test validation succeeds with valid data."""
        columns = ["month", "amount"]
        rows = [
            ["2024-01", 100],
            ["2024-02", 200],
            ["2024-03", 150],
        ]

        error = validate_chart_data(rows, columns, "month", "amount")
        assert error is None


class TestCreateChart:
    """Tests for chart creation from configuration."""

    def test_create_bar_chart(self):
        """Test creating a bar chart from data."""
        config = ChartWizardConfig(
            chart_type="bar",
            x_column="category",
            y_column="amount",
            title="Spending by Category",
            color="green",
        )

        columns = ["category", "amount"]
        rows = [
            ["dining", 500],
            ["transport", 200],
            ["groceries", 300],
        ]

        result = create_chart_from_config(config, columns, rows)

        assert result.success is True
        assert result.data is not None
        # Should contain chart output
        chart_output = result.data
        assert len(chart_output) > 0

    def test_create_line_chart(self):
        """Test creating a line chart from data."""
        config = ChartWizardConfig(
            chart_type="line",
            x_column="month",
            y_column="total",
            title="Monthly Trend",
            color="blue",
        )

        columns = ["month", "total"]
        rows = [
            ["2024-01", 100],
            ["2024-02", 150],
            ["2024-03", 200],
        ]

        result = create_chart_from_config(config, columns, rows)

        assert result.success is True
        assert result.data is not None

    def test_create_scatter_chart(self):
        """Test creating a scatter plot from data."""
        config = ChartWizardConfig(
            chart_type="scatter",
            x_column="income",
            y_column="spending",
            title="Income vs Spending",
            color="red",
        )

        columns = ["income", "spending"]
        rows = [
            [5000, 3000],
            [6000, 3500],
            [5500, 3200],
        ]

        result = create_chart_from_config(config, columns, rows)

        assert result.success is True
        assert result.data is not None

    def test_create_histogram(self):
        """Test creating a histogram from data."""
        config = ChartWizardConfig(
            chart_type="histogram",
            x_column="amount",  # Note: histogram only needs x_column
            y_column="",  # Not used for histogram but required by config
            title="Transaction Distribution",
            color="cyan",
        )

        columns = ["amount"]
        rows = [[100], [150], [200], [175], [125], [300], [250]]

        result = create_chart_from_config(config, columns, rows)

        assert result.success is True
        assert result.data is not None

    def test_create_chart_with_invalid_column(self):
        """Test chart creation fails gracefully with invalid column."""
        config = ChartWizardConfig(
            chart_type="bar",
            x_column="invalid",
            y_column="amount",
            title="Test",
        )

        columns = ["category", "amount"]
        rows = [["dining", 500]]

        result = create_chart_from_config(config, columns, rows)

        assert result.success is False
        assert result.error is not None

    def test_create_chart_with_numeric_x_values(self):
        """Test chart handles numeric X values correctly."""
        config = ChartWizardConfig(
            chart_type="line",
            x_column="day",
            y_column="count",
            title="Daily Count",
            color="blue",
        )

        columns = ["day", "count"]
        rows = [
            [1, 10],
            [2, 15],
            [3, 12],
        ]

        result = create_chart_from_config(config, columns, rows)

        assert result.success is True
