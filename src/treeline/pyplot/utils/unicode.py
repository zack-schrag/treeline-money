"""Unicode box drawing and special characters."""

# Box drawing characters
BOX_LIGHT = {
    "horizontal": "─",
    "vertical": "│",
    "top_left": "┌",
    "top_right": "┐",
    "bottom_left": "└",
    "bottom_right": "┘",
    "left_tee": "├",
    "right_tee": "┤",
    "top_tee": "┬",
    "bottom_tee": "┴",
    "cross": "┼",
}

BOX_HEAVY = {
    "horizontal": "━",
    "vertical": "┃",
    "top_left": "┏",
    "top_right": "┓",
    "bottom_left": "┗",
    "bottom_right": "┛",
    "left_tee": "┣",
    "right_tee": "┫",
    "top_tee": "┳",
    "bottom_tee": "┻",
    "cross": "╋",
}

# Block characters for bar charts
BLOCKS = {
    "full": "█",
    "seven_eighths": "▇",
    "three_quarters": "▆",
    "five_eighths": "▅",
    "half": "▄",
    "three_eighths": "▃",
    "quarter": "▂",
    "eighth": "▁",
    "upper_half": "▀",
    "lower_half": "▄",
}

# Braille patterns (for high-res plotting)
BRAILLE_BASE = 0x2800

# Braille dot positions (left column, right column)
# Each position is a bit flag
BRAILLE_DOTS = [
    [0x01, 0x02, 0x04, 0x40],  # Left column: dots 1,2,3,7
    [0x08, 0x10, 0x20, 0x80],  # Right column: dots 4,5,6,8
]

# Plot markers
MARKERS = {
    "dot": "•",
    "circle": "○",
    "square": "■",
    "diamond": "◆",
    "triangle": "▲",
    "star": "★",
    "plus": "+",
    "cross": "×",
}
