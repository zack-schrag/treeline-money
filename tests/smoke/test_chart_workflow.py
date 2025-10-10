"""Smoke tests for chart workflow - end-to-end chart functionality."""

import tempfile
from pathlib import Path
from treeline.commands.chart_config import ChartConfig, ChartConfigStore
from treeline.commands.chart_wizard import ChartWizardConfig, create_chart_from_config


def test_create_and_save_line_chart():
    """Test creating a line chart and saving its configuration."""
    # Simulate query results
    columns = ["month", "spending"]
    rows = [
        ["2024-01", 500.00],
        ["2024-02", 650.00],
        ["2024-03", 580.00],
        ["2024-04", 720.00],
    ]

    # Create chart wizard config
    wizard_config = ChartWizardConfig(
        chart_type="line",
        x_column="month",
        y_column="spending",
        title="Monthly Spending Trend",
        color="blue",
    )

    # Generate chart
    result = create_chart_from_config(wizard_config, columns, rows)

    assert result.success is True
    assert result.data is not None
    assert len(result.data) > 0

    # Save chart config
    with tempfile.TemporaryDirectory() as tmpdir:
        charts_dir = Path(tmpdir)
        store = ChartConfigStore(charts_dir)

        chart_config = ChartConfig(
            name="monthly_spending",
            query="SELECT month, spending FROM spending_summary",
            chart_type="line",
            x_column="month",
            y_column="spending",
            title="Monthly Spending Trend",
            color="blue",
        )

        # Save
        saved = store.save("monthly_spending", chart_config)
        assert saved is True

        # Verify file exists
        chart_file = charts_dir / "monthly_spending.tl"
        assert chart_file.exists()

        # Load and verify
        loaded = store.load("monthly_spending")
        assert loaded is not None
        assert loaded.name == "monthly_spending"
        assert loaded.chart_type == "line"
        assert loaded.x_column == "month"
        assert loaded.y_column == "spending"


def test_create_bar_chart_for_categories():
    """Test creating a bar chart for categorical data."""
    # Simulate query results
    columns = ["category", "total"]
    rows = [
        ["Dining", 450.00],
        ["Transport", 200.00],
        ["Groceries", 550.00],
        ["Entertainment", 180.00],
    ]

    # Create chart
    wizard_config = ChartWizardConfig(
        chart_type="bar",
        x_column="category",
        y_column="total",
        title="Spending by Category",
        color="green",
    )

    result = create_chart_from_config(wizard_config, columns, rows)

    assert result.success is True
    assert result.data is not None


def test_create_scatter_plot():
    """Test creating a scatter plot for correlation analysis."""
    # Simulate query results
    columns = ["income", "spending"]
    rows = [
        [5000, 3200],
        [5500, 3400],
        [6000, 3800],
        [5200, 3100],
        [5800, 3600],
    ]

    # Create chart
    wizard_config = ChartWizardConfig(
        chart_type="scatter",
        x_column="income",
        y_column="spending",
        title="Income vs Spending",
        color="red",
    )

    result = create_chart_from_config(wizard_config, columns, rows)

    assert result.success is True
    assert result.data is not None


def test_create_histogram_for_distribution():
    """Test creating a histogram to show value distribution."""
    # Simulate query results
    columns = ["amount"]
    rows = [
        [50.00],
        [125.00],
        [200.00],
        [175.00],
        [100.00],
        [300.00],
        [250.00],
        [150.00],
        [225.00],
        [180.00],
    ]

    # Create chart
    wizard_config = ChartWizardConfig(
        chart_type="histogram",
        x_column="amount",
        y_column="",  # Not used for histogram
        title="Transaction Amount Distribution",
        color="cyan",
    )

    result = create_chart_from_config(wizard_config, columns, rows)

    assert result.success is True
    assert result.data is not None


def test_chart_config_round_trip():
    """Test saving and loading chart configuration preserves data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        charts_dir = Path(tmpdir)
        store = ChartConfigStore(charts_dir)

        # Create and save multiple charts
        charts = [
            ChartConfig(
                name="chart1",
                query="SELECT a, b FROM t1",
                chart_type="line",
                x_column="a",
                y_column="b",
                title="Chart 1",
                color="blue",
            ),
            ChartConfig(
                name="chart2",
                query="SELECT x, y FROM t2",
                chart_type="bar",
                x_column="x",
                y_column="y",
                title="Chart 2",
                color="green",
                description="A helpful description",
            ),
            ChartConfig(
                name="chart3",
                query="SELECT m, n FROM t3",
                chart_type="scatter",
                x_column="m",
                y_column="n",
                title="Chart 3",
                xlabel="M Axis",
                ylabel="N Axis",
                color="red",
            ),
        ]

        for chart in charts:
            assert store.save(chart.name, chart) is True

        # List charts
        chart_names = store.list()
        assert len(chart_names) == 3
        assert "chart1" in chart_names
        assert "chart2" in chart_names
        assert "chart3" in chart_names

        # Load and verify each chart
        for original in charts:
            loaded = store.load(original.name)
            assert loaded is not None
            assert loaded.name == original.name
            assert loaded.query.strip() == original.query
            assert loaded.chart_type == original.chart_type
            assert loaded.x_column == original.x_column
            assert loaded.y_column == original.y_column
            assert loaded.title == original.title
            assert loaded.color == original.color
            if original.description:
                assert loaded.description == original.description

        # Delete a chart
        assert store.delete("chart2") is True
        assert len(store.list()) == 2
        assert "chart2" not in store.list()


def test_chart_validation_errors():
    """Test that chart validation catches common errors."""
    from treeline.commands.chart_wizard import validate_chart_data

    columns = ["month", "amount"]
    rows = [["2024-01", 500], ["2024-02", 600]]

    # Test invalid column name
    error = validate_chart_data(rows, columns, "invalid_col", "amount")
    assert error is not None
    assert "invalid_col" in error

    # Test empty results
    error = validate_chart_data([], columns, "month", "amount")
    assert error is not None

    # Test non-numeric Y column
    non_numeric_rows = [["2024-01", "text"], ["2024-02", "more text"]]
    error = validate_chart_data(non_numeric_rows, columns, "month", "amount")
    assert error is not None
    assert "numeric" in error.lower()

    # Test valid data
    error = validate_chart_data(rows, columns, "month", "amount")
    assert error is None
