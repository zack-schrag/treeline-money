/**
 * Frequency-Based Tag Suggester
 *
 * Suggests tags based on:
 * 1. Tags frequently used on transactions with similar descriptions (merchant match)
 * 2. Tags frequently used on transactions with similar amounts
 * 3. Global tag frequency as fallback
 */

import { executeQuery } from "../../../sdk";
import type { TagSuggester, TagSuggestion, Transaction } from "./types";

export class FrequencyBasedSuggester implements TagSuggester {
  async suggestBatch(
    transactions: Transaction[],
    limit: number
  ): Promise<Map<string, TagSuggestion[]>> {
    const result = new Map<string, TagSuggestion[]>();

    if (transactions.length === 0) {
      return result;
    }

    // Get global tag frequencies
    const globalFrequencies = await this.getGlobalTagFrequencies();

    // Get merchant-based suggestions (batch query for efficiency)
    const merchantSuggestions = await this.getMerchantBasedSuggestions(transactions);

    // Combine and rank for each transaction
    for (const txn of transactions) {
      const existingTags = new Set(txn.tags || []);
      const scores = new Map<string, { score: number; reason: string }>();

      // Merchant-based suggestions (highest weight)
      const merchantTags = merchantSuggestions.get(txn.transaction_id) || [];
      for (const { tag, count } of merchantTags) {
        if (!existingTags.has(tag)) {
          const existing = scores.get(tag);
          const merchantScore = count * 3; // 3x weight for merchant match
          if (existing) {
            existing.score += merchantScore;
          } else {
            scores.set(tag, { score: merchantScore, reason: "similar merchant" });
          }
        }
      }

      // Global frequency (fallback, lower weight)
      for (const [tag, count] of globalFrequencies) {
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
      const suggestions: TagSuggestion[] = Array.from(scores.entries())
        .map(([tag, { score, reason }]) => ({ tag, score, reason }))
        .sort((a, b) => b.score - a.score)
        .slice(0, limit);

      result.set(txn.transaction_id, suggestions);
    }

    return result;
  }

  private async getGlobalTagFrequencies(): Promise<Map<string, number>> {
    const frequencies = new Map<string, number>();

    try {
      const result = await executeQuery(`
        SELECT tag, COUNT(*) as freq
        FROM (
          SELECT UNNEST(tags) as tag
          FROM transactions
          WHERE tags IS NOT NULL AND len(tags) > 0
        )
        GROUP BY tag
        ORDER BY freq DESC
        LIMIT 50
      `);

      for (const row of result.rows) {
        const tag = row[0] as string;
        const freq = row[1] as number;
        frequencies.set(tag, freq);
      }
    } catch (e) {
      console.error("Failed to get global tag frequencies:", e);
    }

    return frequencies;
  }

  private async getMerchantBasedSuggestions(
    transactions: Transaction[]
  ): Promise<Map<string, Array<{ tag: string; count: number }>>> {
    const result = new Map<string, Array<{ tag: string; count: number }>>();

    // Extract merchant patterns from descriptions
    // Use first word or first two words as merchant identifier
    const merchantPatterns = new Map<string, string[]>();

    for (const txn of transactions) {
      const pattern = this.extractMerchantPattern(txn.description);
      if (pattern) {
        const ids = merchantPatterns.get(pattern) || [];
        ids.push(txn.transaction_id);
        merchantPatterns.set(pattern, ids);
      }
      // Initialize empty result for each transaction
      result.set(txn.transaction_id, []);
    }

    // Query for each unique merchant pattern
    for (const [pattern, transactionIds] of merchantPatterns) {
      try {
        const escapedPattern = pattern.replace(/'/g, "''");
        const queryResult = await executeQuery(`
          SELECT tag, COUNT(*) as freq
          FROM (
            SELECT UNNEST(tags) as tag
            FROM transactions
            WHERE description ILIKE '${escapedPattern}%'
              AND tags IS NOT NULL AND len(tags) > 0
          )
          GROUP BY tag
          ORDER BY freq DESC
          LIMIT 10
        `);

        const suggestions = queryResult.rows.map(row => ({
          tag: row[0] as string,
          count: row[1] as number,
        }));

        // Apply to all transactions with this merchant pattern
        for (const txnId of transactionIds) {
          result.set(txnId, suggestions);
        }
      } catch (e) {
        console.error(`Failed to get merchant suggestions for pattern '${pattern}':`, e);
      }
    }

    return result;
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
