/**
 * Frequency-Based Tag Suggester
 *
 * Loads all tag data ONCE into memory, then computes suggestions purely in-memory.
 * No DB queries during navigation - only on initial load/refresh.
 */

import { executeQuery } from "../../../sdk";
import type { TagSuggester, TagSuggestion, Transaction } from "./types";

interface TagData {
  globalFrequencies: Map<string, number>;
  merchantTagFrequencies: Map<string, Map<string, number>>; // merchant pattern -> tag -> count
}

export class FrequencyBasedSuggester implements TagSuggester {
  private tagData: TagData | null = null;
  private loadingPromise: Promise<TagData> | null = null;

  /**
   * Load all tag data into memory. Call this once at startup.
   * Returns cached data if already loaded.
   */
  async loadTagData(): Promise<TagData> {
    if (this.tagData) {
      return this.tagData;
    }

    // Avoid duplicate loads
    if (this.loadingPromise) {
      return this.loadingPromise;
    }

    this.loadingPromise = this.fetchTagData();
    this.tagData = await this.loadingPromise;
    this.loadingPromise = null;
    return this.tagData;
  }

  /**
   * Force refresh of tag data from DB.
   */
  async refresh(): Promise<void> {
    this.tagData = null;
    this.loadingPromise = null;
    await this.loadTagData();
  }

  private async fetchTagData(): Promise<TagData> {
    const globalFrequencies = new Map<string, number>();
    const merchantTagFrequencies = new Map<string, Map<string, number>>();

    try {
      // Single query to get all tagged transactions with their descriptions
      const result = await executeQuery(`
        SELECT description, tags
        FROM transactions
        WHERE tags IS NOT NULL AND len(tags) > 0
      `);

      for (const row of result.rows) {
        const description = row[0] as string;
        const tags = (row[1] as string[]) || [];

        // Extract merchant pattern
        const pattern = this.extractMerchantPattern(description);

        for (const tag of tags) {
          // Global frequency
          globalFrequencies.set(tag, (globalFrequencies.get(tag) || 0) + 1);

          // Merchant-specific frequency
          if (pattern) {
            let merchantTags = merchantTagFrequencies.get(pattern);
            if (!merchantTags) {
              merchantTags = new Map();
              merchantTagFrequencies.set(pattern, merchantTags);
            }
            merchantTags.set(tag, (merchantTags.get(tag) || 0) + 1);
          }
        }
      }
    } catch (e) {
      console.error("Failed to load tag data:", e);
    }

    return { globalFrequencies, merchantTagFrequencies };
  }

  async suggestBatch(
    transactions: Transaction[],
    limit: number
  ): Promise<Map<string, TagSuggestion[]>> {
    const result = new Map<string, TagSuggestion[]>();

    if (transactions.length === 0) {
      return result;
    }

    // Ensure tag data is loaded
    const tagData = await this.loadTagData();

    // Compute suggestions for each transaction (pure in-memory)
    for (const txn of transactions) {
      const suggestions = this.computeSuggestionsForTransaction(txn, tagData, limit);
      result.set(txn.transaction_id, suggestions);
    }

    return result;
  }

  /**
   * Compute suggestions for a single transaction. Pure in-memory, no DB access.
   */
  private computeSuggestionsForTransaction(
    txn: Transaction,
    tagData: TagData,
    limit: number
  ): TagSuggestion[] {
    const existingTags = new Set(txn.tags || []);
    const scores = new Map<string, { score: number; reason: string }>();

    // Merchant-based suggestions (highest weight)
    const pattern = this.extractMerchantPattern(txn.description);
    if (pattern) {
      const merchantTags = tagData.merchantTagFrequencies.get(pattern);
      if (merchantTags) {
        for (const [tag, count] of merchantTags) {
          if (!existingTags.has(tag)) {
            const merchantScore = count * 3; // 3x weight for merchant match
            scores.set(tag, { score: merchantScore, reason: "similar merchant" });
          }
        }
      }
    }

    // Global frequency (fallback, lower weight)
    for (const [tag, count] of tagData.globalFrequencies) {
      if (!existingTags.has(tag)) {
        const existing = scores.get(tag);
        if (existing) {
          existing.score += count;
        } else {
          scores.set(tag, { score: count, reason: "frequently used" });
        }
      }
    }

    // Sort by score and take top N
    return Array.from(scores.entries())
      .map(([tag, { score, reason }]) => ({ tag, score, reason }))
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  /**
   * Extract a merchant pattern from a transaction description.
   * Takes the first significant word(s) as the merchant identifier.
   */
  private extractMerchantPattern(description: string): string | null {
    if (!description) return null;

    // Clean up the description
    const cleaned = description
      .toUpperCase()
      .replace(/[*#]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    // Take first word as merchant pattern
    const words = cleaned.split(" ").filter(w => w.length > 2);
    if (words.length === 0) return null;

    // Use first word, or first two if first is very short
    if (words[0].length <= 3 && words.length > 1) {
      return words.slice(0, 2).join(" ");
    }

    return words[0];
  }
}
