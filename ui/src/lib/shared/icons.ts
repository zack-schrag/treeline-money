/**
 * Shared icon utilities
 *
 * Maps emoji icons (used in plugin manifests) to Icon component names.
 */

/**
 * Mapping from emoji to Icon component name.
 * Used by Sidebar and TabBar to display consistent icons.
 */
export const emojiToIconName: Record<string, string> = {
  "🏦": "bank",
  "💰": "wallet",
  "💳": "credit-card",
  "🏷": "tag",
  "⚡": "zap",
  "⚙": "settings",
  "📊": "chart",
  "🔍": "search",
};

/**
 * Convert an emoji to an Icon component name.
 * Returns "database" as fallback for unknown emojis.
 */
export function getIconName(emoji: string): string {
  return emojiToIconName[emoji] || "database";
}
