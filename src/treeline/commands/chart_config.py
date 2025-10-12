"""Chart configuration parsing and serialization.

This module handles the .tl file format for saving chart configurations.
The format is designed to be human-readable and easy to parse.
"""

import re
from typing import Optional

from treeline.domain import ChartConfig


def parse_chart_config(content: str) -> Optional[ChartConfig]:
    """Parse a .tl chart configuration file.

    The format is:
    ```
    # Chart Name

    Optional description here.

    ## Query
    ```sql
    SELECT ...
    ```

    ## Chart
    type: line
    x_column: month
    y_column: amount
    title: Optional Title
    xlabel: Optional X Label
    ylabel: Optional Y Label
    color: blue
    ```

    Args:
        content: The .tl file content

    Returns:
        ChartConfig if valid, None otherwise
    """
    try:
        lines = content.split("\n")

        # Extract name (first line starting with #)
        name = None
        for line in lines:
            if line.strip().startswith("# "):
                name = line.strip()[2:].strip()
                break

        if not name:
            return None

        # Extract query (between ```sql and ```)
        query_match = re.search(r"```sql\s*\n(.*?)\n```", content, re.DOTALL)
        if not query_match:
            return None
        query = query_match.group(1).strip()

        # Extract description (text between name and ## Query)
        description = None
        query_section_match = re.search(r"^# .*?\n\n(.*?)\n##", content, re.DOTALL | re.MULTILINE)
        if query_section_match:
            desc_text = query_section_match.group(1).strip()
            if desc_text and not desc_text.startswith("##"):
                description = desc_text

        # Extract chart configuration (after ## Chart)
        chart_section_match = re.search(r"## Chart\s*\n(.*?)(?:\n##|$)", content, re.DOTALL)
        if not chart_section_match:
            return None

        chart_section = chart_section_match.group(1)

        # Parse chart properties
        def get_prop(prop_name: str) -> Optional[str]:
            match = re.search(rf"^{prop_name}:\s*(.+)$", chart_section, re.MULTILINE)
            return match.group(1).strip() if match else None

        chart_type = get_prop("type")
        x_column = get_prop("x_column")
        y_column = get_prop("y_column")

        if not chart_type or not x_column or not y_column:
            return None

        return ChartConfig(
            name=name,
            query=query,
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            title=get_prop("title"),
            xlabel=get_prop("xlabel"),
            ylabel=get_prop("ylabel"),
            color=get_prop("color"),
            description=description,
        )

    except Exception:
        return None


def serialize_chart_config(config: ChartConfig) -> str:
    """Serialize a chart configuration to .tl format.

    Args:
        config: The chart configuration to serialize

    Returns:
        String content in .tl format
    """
    parts = []

    # Name
    parts.append(f"# {config.name}")
    parts.append("")

    # Description (optional)
    if config.description:
        parts.append(config.description)
        parts.append("")

    # Query
    parts.append("## Query")
    parts.append("```sql")
    parts.append(config.query)
    parts.append("```")
    parts.append("")

    # Chart configuration
    parts.append("## Chart")
    parts.append(f"type: {config.chart_type}")
    parts.append(f"x_column: {config.x_column}")
    parts.append(f"y_column: {config.y_column}")

    if config.title:
        parts.append(f"title: {config.title}")
    if config.xlabel:
        parts.append(f"xlabel: {config.xlabel}")
    if config.ylabel:
        parts.append(f"ylabel: {config.ylabel}")
    if config.color:
        parts.append(f"color: {config.color}")

    return "\n".join(parts)


def validate_chart_name(name: str) -> bool:
    """Validate that a chart name is valid.

    Args:
        name: The chart name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    # Only allow alphanumeric and underscores
    return bool(re.match(r"^[a-zA-Z0-9_]+$", name))
