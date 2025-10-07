Currently, the CLI has a bunch of hardcoded colors and visuals. Instead, we should implement a simple theme system based entirely in JSON, so users can potentially add their own themes in the future. 

Acceptance criteria:
- All CLI colors and stylistic choices are codified into a self-contained theme JSON file that is read at start time of the CLI.

Context:
Here is some typescript code from a previous implementation of "treeline dark" theme:
```typescript
const COLORS = {
  // Primary brand colors - sage greens (sophisticated, mountain-inspired, earthy)
  primary: {
    50: '#F8FAF9',   // Lightest sage
    100: '#E8F2ED',  // Light sage
    200: '#D1E5DB',  // Soft sage
    300: '#A3CDB5',  // Medium sage
    400: '#75B58F',  // Sage green
    500: '#44755a',  // Mountain sage (primary)
    600: '#3A6249',  // Deep sage
    700: '#2F4F39',  // Dark sage
    800: '#253C2A',  // Very dark sage
    900: '#1A291B'   // Darkest sage
  },
  // Background colors (dark theme)
  background: {
    primary: '#111827',
    secondary: '#1F2937',
    tertiary: '#374151'
  },
  // Surface colors (dark theme)
  surface: {
    primary: '#1F2937',
    secondary: '#374151',
    tertiary: '#4B5563'
  },
  // Text colors (dark theme)
  text: {
    primary: '#F9FAFB',
    secondary: '#E5E7EB',
    tertiary: '#9CA3AF',
    quaternary: '#6B7280'
  },
  // Border colors (dark theme)
  border: {
    primary: '#374151',
    secondary: '#4B5563',
    tertiary: '#6B7280'
  },
  // Semantic colors (dark theme)
  semantic: {
    success: '#4A7C59',
    warning: '#FBBF24',
    error: '#F87171',
    info: '#60A5FA'
  }
}
```
And here's the same one for the "treeline light" theme:
```typescript
const COLORS = {
  // Primary brand colors - sage greens (sophisticated, mountain-inspired, earthy)
  primary: {
    50: '#F8FAF9',   // Lightest sage
    100: '#E8F2ED',  // Light sage
    200: '#D1E5DB',  // Soft sage
    300: '#A3CDB5',  // Medium sage
    400: '#75B58F',  // Sage green
    500: '#44755a',  // Mountain sage (primary)
    600: '#3A6249',  // Deep sage
    700: '#2F4F39',  // Dark sage
    800: '#253C2A',  // Very dark sage
    900: '#1A291B'   // Darkest sage
  },
  // Warm accent colors - mountain sunset vibes
  accent: {
    terracotta: {
      50: '#FDF6F5',   // Lightest terracotta
      100: '#F9E8E6',  // Light terracotta
      200: '#F0CCC8',  // Soft terracotta
      300: '#E09B94',  // Medium terracotta
      400: '#D06A60',  // Warm terracotta
      500: '#B85450',  // Primary terracotta
      600: '#A04844',  // Deep terracotta
      700: '#883C38',  // Dark terracotta
      800: '#70302C',  // Very dark terracotta
      900: '#582420'   // Darkest terracotta
    },
    amber: {
      50: '#FEFBF3',   // Lightest amber
      100: '#FDF4E1',  // Light amber
      200: '#FAE6BE',  // Soft amber
      300: '#F5D085',  // Medium amber
      400: '#EFBA4C',  // Warm amber
      500: '#D4A574',  // Primary amber (golden)
      600: '#B8915F',  // Deep amber
      700: '#9C7D4A',  // Dark amber
      800: '#806935',  // Very dark amber
      900: '#645520'   // Darkest amber
    },
    copper: {
      50: '#FDF7F5',   // Lightest copper
      100: '#F9EBE6',  // Light copper
      200: '#F0D2C8',  // Soft copper
      300: '#E2A594',  // Medium copper
      400: '#D47860',  // Warm copper
      500: '#C17B5A',  // Primary copper
      600: '#A8674C',  // Deep copper
      700: '#8F533E',  // Dark copper
      800: '#763F30',  // Very dark copper
      900: '#5D2B22'   // Darkest copper
    }
  },
  // Enhanced nature-inspired colors for charts
  nature: {
    forestGreen: '#2D5016',
    autumnOrange: '#E67E22',
    mountainBlue: '#3498DB',
    sunsetRed: '#E74C3C',
    earthBrown: '#8B4513',
    skyBlue: '#87CEEB'
  },
  // Background colors
  background: {
    primary: '#FFFFFF',
    secondary: '#F9FAFB',
    tertiary: '#F3F4F6'
  },
  // Surface colors
  surface: {
    primary: '#FFFFFF',
    secondary: '#F9FAFB',
    tertiary: '#F3F4F6'
  },
  // Text colors
  text: {
    primary: '#111827',
    secondary: '#374151',
    tertiary: '#6B7280',
    quaternary: '#9CA3AF'
  },
  // Border colors
  border: {
    primary: '#D1D5DB',
    secondary: '#E5E7EB',
    tertiary: '#F3F4F6'
  },
  // Semantic colors - enhanced with warm accents
  semantic: {
    success: '#2D5016',      // Forest green (nature-inspired)
    warning: '#D4A574',      // Golden amber (warm, inviting)
    error: '#B85450',        // Terracotta (warm, less harsh than pure red)
    info: '#3498DB'          // Mountain blue (crisp, natural)
  }
}
```

You don't need to follow these exactly, since it might look not as good in a terminal (these were from a React UI previously). But use these as a starting point for the first theme JSON we create. 