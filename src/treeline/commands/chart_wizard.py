"""Chart wizard logic for creating charts from query results.

This module contains the business logic for validating data and creating charts,
separated from the UI interaction code.
"""

from dataclasses import dataclass
from typing import Any, Optional
from pyplot import barplot, lineplot, scatterplot, histogram
from pyplot.utils.colors import strip_colors

from treeline.domain import Result, Ok, Fail


@dataclass
class ChartWizardConfig:
    """Configuration for creating a chart via the wizard."""

    chart_type: str  # bar, line, scatter, histogram
    x_column: str
    y_column: str
    title: Optional[str] = None
    xlabel: Optional[str] = None
    ylabel: Optional[str] = None
    color: Optional[str] = None
    width: int = 60
    height: int = 20


def validate_chart_data(
    rows: list[list[Any]],
    columns: list[str],
    x_column: str,
    y_column: str,
    chart_type: str = "line",
) -> Optional[str]:
    """Validate that query results can be used for charting.

    Args:
        rows: Query result rows
        columns: Column names from query
        x_column: Name of X column
        y_column: Name of Y column
        chart_type: Type of chart (for specific validation)

    Returns:
        Error message if validation fails, None if valid
    """
    # Check if results are empty
    if len(rows) == 0:
        return "Query returned no results. Cannot create chart from empty data."

    # Check if columns exist
    if x_column not in columns:
        return f"Column '{x_column}' not found in query results. Available columns: {', '.join(columns)}"

    if y_column and y_column not in columns:
        return f"Column '{y_column}' not found in query results. Available columns: {', '.join(columns)}"

    # Get column indices
    x_idx = columns.index(x_column)
    y_idx = columns.index(y_column) if y_column else None

    # Validate Y column is numeric (if provided)
    if y_idx is not None:
        for row in rows:
            y_val = row[y_idx]
            if y_val is not None and not isinstance(y_val, (int, float)):
                try:
                    float(y_val)
                except (ValueError, TypeError):
                    return f"Column '{y_column}' contains non-numeric values. Charts require numeric Y values."

    # Warn for single row on line charts
    if chart_type in ["line", "scatter"] and len(rows) == 1:
        return f"Query returned only one row. {chart_type.capitalize()} charts work best with multiple data points."

    return None


def create_chart_from_config(
    config: ChartWizardConfig, columns: list[str], rows: list[list[Any]]
) -> Result[str]:
    """Create a chart from wizard configuration and query results.

    Args:
        config: Chart wizard configuration
        columns: Column names from query results
        rows: Query result rows

    Returns:
        Result with rendered chart string, or error
    """
    try:
        # Validate data first
        error = validate_chart_data(
            rows, columns, config.x_column, config.y_column, config.chart_type
        )
        if error:
            return Fail(error)

        # Get column indices
        x_idx = columns.index(config.x_column)
        y_idx = columns.index(config.y_column) if config.y_column else None

        # Extract data
        x_data = [row[x_idx] for row in rows]

        # For histogram, we don't need y_data
        if config.chart_type == "histogram":
            # Convert to numeric
            numeric_data = []
            for val in x_data:
                try:
                    numeric_data.append(float(val))
                except (ValueError, TypeError):
                    return Fail(f"Histogram requires numeric values in column '{config.x_column}'")

            # Create histogram
            chart = histogram(
                values=numeric_data,
                bins=10,  # Default number of bins
                title=config.title or "",
                xlabel=config.xlabel or "",
                width=config.width,
                color=config.color or "cyan",
            )

            rendered = chart.render()
            clean_output = strip_colors(rendered)
            return Ok(f"\n{clean_output}\n")

        # For other chart types, we need y_data
        if y_idx is None:
            return Fail("Y column is required for this chart type")

        y_data = []
        for row in rows:
            y_val = row[y_idx]
            try:
                y_data.append(float(y_val) if y_val is not None else 0.0)
            except (ValueError, TypeError):
                return Fail(f"Column '{config.y_column}' contains non-numeric values")

        # Create chart based on type
        if config.chart_type == "bar":
            # Bar chart needs string labels for x-axis
            labels = [str(x) for x in x_data]

            chart = barplot(
                labels=labels,
                values=y_data,
                title=config.title or "",
                xlabel=config.xlabel or "",
                width=config.width,
                color=config.color or "green",
            )

        elif config.chart_type == "line":
            # Line chart can have numeric or use indices for x
            # Try to convert x to numeric, fall back to indices
            try:
                x_numeric = [float(x) if x is not None else i for i, x in enumerate(x_data)]
            except (ValueError, TypeError):
                # Use indices if x is not numeric
                x_numeric = None

            chart = lineplot(
                x=x_numeric,
                y=y_data,
                title=config.title or "",
                xlabel=config.xlabel or "",
                ylabel=config.ylabel or "",
                width=config.width,
                height=config.height,
                color=config.color or "blue",
            )

        elif config.chart_type == "scatter":
            # Scatter plot needs numeric x values
            try:
                x_numeric = [float(x) if x is not None else 0.0 for x in x_data]
            except (ValueError, TypeError):
                return Fail(f"Scatter plot requires numeric values in column '{config.x_column}'")

            chart = scatterplot(
                x=x_numeric,
                y=y_data,
                title=config.title or "",
                xlabel=config.xlabel or "",
                ylabel=config.ylabel or "",
                width=config.width,
                height=config.height,
                color=config.color or "red",
            )

        else:
            return Fail(f"Unsupported chart type: {config.chart_type}")

        # Render and strip colors
        rendered = chart.render()
        clean_output = strip_colors(rendered)
        return Ok(f"\n{clean_output}\n")

    except Exception as e:
        return Fail(f"Error creating chart: {str(e)}")
