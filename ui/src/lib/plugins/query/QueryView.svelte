<script lang="ts">
  import { executeQuery, type QueryResult } from "../../sdk";

  const HISTORY_KEY = "treeline-query-history";
  const MAX_HISTORY = 50;

  interface HistoryEntry {
    query: string;
    timestamp: number;
    success: boolean;
  }

  let query = $state("SELECT * FROM transactions LIMIT 10");
  let result = $state<QueryResult | null>(null);
  let isLoading = $state(false);
  let error = $state<string | null>(null);
  let history = $state<HistoryEntry[]>(loadHistory());
  let showHistory = $state(false);

  function loadHistory(): HistoryEntry[] {
    try {
      const stored = localStorage.getItem(HISTORY_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  function saveHistory(entries: HistoryEntry[]) {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
    } catch {
      // Ignore storage errors
    }
  }

  function addToHistory(queryText: string, success: boolean) {
    // Don't add duplicates of the most recent query
    if (history.length > 0 && history[0].query === queryText) {
      return;
    }

    const entry: HistoryEntry = {
      query: queryText,
      timestamp: Date.now(),
      success,
    };

    history = [entry, ...history.slice(0, MAX_HISTORY - 1)];
    saveHistory(history);
  }

  function loadFromHistory(entry: HistoryEntry) {
    query = entry.query;
    showHistory = false;
  }

  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest(".history-container")) {
      showHistory = false;
    }
  }

  $effect(() => {
    if (showHistory) {
      // Use setTimeout to avoid the click that opened the dropdown from immediately closing it
      const timeout = setTimeout(() => {
        document.addEventListener("click", handleClickOutside);
      }, 0);
      return () => {
        clearTimeout(timeout);
        document.removeEventListener("click", handleClickOutside);
      };
    }
  });

  function clearHistory() {
    history = [];
    saveHistory([]);
  }

  function formatTimestamp(ts: number): string {
    const date = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - ts;

    if (diff < 60000) return "just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (date.toDateString() === now.toDateString()) return "today";

    return date.toLocaleDateString();
  }

  async function runQuery() {
    if (!query.trim()) {
      error = "Please enter a query";
      return;
    }

    isLoading = true;
    error = null;
    result = null;

    try {
      result = await executeQuery(query);
      addToHistory(query, true);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to execute query";
      addToHistory(query, false);
      console.error("Query error:", e);
    } finally {
      isLoading = false;
    }
  }

  function clearQuery() {
    query = "";
    result = null;
    error = null;
  }

  let viewEl: HTMLDivElement;

  function handleGlobalKeyDown(e: KeyboardEvent) {
    // Only handle if we're inside the query view
    if (!viewEl?.contains(document.activeElement) && document.activeElement !== document.body) {
      return;
    }

    const isMod = e.metaKey || e.ctrlKey;

    // Cmd/Ctrl + Enter to run query
    if (isMod && e.key === "Enter") {
      e.preventDefault();
      runQuery();
    }
    // Cmd/Ctrl + L to clear
    else if (isMod && e.key === "l") {
      e.preventDefault();
      clearQuery();
    }
  }

  // Example queries
  const examples = [
    {
      name: "Recent transactions",
      query: "SELECT transaction_date, description, amount, tags FROM transactions ORDER BY transaction_date DESC LIMIT 20",
    },
    {
      name: "Spending by tag",
      query: "SELECT unnest(tags) as tag, SUM(amount) as total FROM transactions WHERE amount < 0 GROUP BY tag ORDER BY total",
    },
    {
      name: "Monthly spending",
      query: "SELECT strftime('%Y-%m', transaction_date) as month, SUM(amount) as total FROM transactions WHERE amount < 0 GROUP BY month ORDER BY month DESC LIMIT 12",
    },
    {
      name: "Untagged transactions",
      query: "SELECT transaction_date, description, amount FROM transactions WHERE tags = [] ORDER BY transaction_date DESC LIMIT 50",
    },
  ];

  function loadExample(exampleQuery: string) {
    query = exampleQuery;
  }

  function exportCSV() {
    if (!result) return;

    const escapeCSV = (val: unknown): string => {
      if (val === null) return "";
      if (Array.isArray(val)) val = `[${val.join(", ")}]`;
      const str = String(val);
      if (str.includes(",") || str.includes('"') || str.includes("\n")) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    const header = result.columns.map(escapeCSV).join(",");
    const rows = result.rows.map((row) => row.map(escapeCSV).join(","));
    const csv = [header, ...rows].join("\n");

    downloadFile(csv, "query-results.csv", "text/csv");
  }

  function exportJSON() {
    if (!result) return;

    const data = result.rows.map((row) => {
      const obj: Record<string, unknown> = {};
      result!.columns.forEach((col, i) => {
        obj[col] = row[i];
      });
      return obj;
    });

    const json = JSON.stringify(data, null, 2);
    downloadFile(json, "query-results.json", "application/json");
  }

  function downloadFile(content: string, filename: string, mimeType: string) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function formatQuery() {
    // Simple SQL formatter
    const keywords = [
      "SELECT", "FROM", "WHERE", "AND", "OR", "ORDER BY", "GROUP BY",
      "HAVING", "LIMIT", "OFFSET", "JOIN", "LEFT JOIN", "RIGHT JOIN",
      "INNER JOIN", "OUTER JOIN", "ON", "AS", "DISTINCT", "UNION",
      "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE FROM", "CREATE",
      "DROP", "ALTER", "WITH"
    ];

    let formatted = query.trim();

    // Normalize whitespace
    formatted = formatted.replace(/\s+/g, " ");

    // Add newlines before major keywords
    const majorKeywords = [
      "SELECT", "FROM", "WHERE", "ORDER BY", "GROUP BY", "HAVING",
      "LIMIT", "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN",
      "OUTER JOIN", "UNION", "WITH"
    ];

    for (const kw of majorKeywords) {
      const regex = new RegExp(`\\b(${kw})\\b`, "gi");
      formatted = formatted.replace(regex, "\n$1");
    }

    // Add newlines and indentation for AND/OR
    formatted = formatted.replace(/\b(AND|OR)\b/gi, "\n  $1");

    // Uppercase keywords
    for (const kw of keywords) {
      const regex = new RegExp(`\\b(${kw})\\b`, "gi");
      formatted = formatted.replace(regex, kw);
    }

    // Clean up leading newline and extra spaces
    formatted = formatted.trim();

    query = formatted;
  }
</script>

<svelte:window onkeydown={handleGlobalKeyDown} />

<div class="query-view" bind:this={viewEl}>
  <div class="query-panel">
    <div class="panel-header">
      <h2 class="panel-title">SQL Query</h2>
      <div class="header-actions">
        <div class="history-container">
          <button
            class="history-button"
            class:active={showHistory}
            onclick={() => (showHistory = !showHistory)}
            disabled={history.length === 0}
          >
            History ({history.length})
          </button>
          {#if showHistory}
            <div class="history-dropdown">
              <div class="history-header">
                <span>Query History</span>
                <button class="clear-history" onclick={clearHistory}>Clear</button>
              </div>
              <div class="history-list">
                {#each history as entry}
                  <button
                    class="history-item"
                    class:failed={!entry.success}
                    onclick={() => loadFromHistory(entry)}
                  >
                    <pre class="history-query">{entry.query}</pre>
                    <span class="history-time">{formatTimestamp(entry.timestamp)}</span>
                  </button>
                {/each}
              </div>
            </div>
          {/if}
        </div>
        <button class="format-button" onclick={formatQuery} disabled={!query.trim()}>
          Format
        </button>
        <button class="run-button" onclick={runQuery} disabled={isLoading}>
          {isLoading ? "Running..." : "Run Query"}
          <span class="shortcut">⌘↵</span>
        </button>
      </div>
    </div>

    <textarea
      class="query-editor"
      bind:value={query}
      placeholder="Enter SQL query..."
      spellcheck="false"
    ></textarea>

    <div class="query-footer">
      <div class="examples">
        <div class="examples-label">Examples:</div>
        <div class="examples-list">
          {#each examples as example}
            <button class="example-button" onclick={() => loadExample(example.query)}>
              {example.name}
            </button>
          {/each}
        </div>
      </div>
      <div class="shortcuts">
        <span class="shortcut-item"><kbd>⌘</kbd><kbd>↵</kbd> Run</span>
        <span class="shortcut-item"><kbd>⌘</kbd><kbd>L</kbd> Clear</span>
      </div>
    </div>
  </div>

  <div class="results-panel">
    {#if isLoading}
      <div class="status">
        <div class="spinner"></div>
        <span>Running query...</span>
      </div>
    {:else if error}
      <div class="status error">
        <span class="error-icon">⚠️</span>
        <div class="error-content">
          <div class="error-title">Query Error</div>
          <pre class="error-message">{error}</pre>
        </div>
      </div>
    {:else if result}
      <div class="results-content">
        <div class="results-header">
          <span class="result-count">{result.row_count} {result.row_count === 1 ? 'row' : 'rows'}</span>
          <div class="export-buttons">
            <button class="export-button" onclick={exportCSV}>Export CSV</button>
            <button class="export-button" onclick={exportJSON}>Export JSON</button>
          </div>
        </div>

        {#if result.row_count === 0}
          <div class="no-results">No results returned</div>
        {:else}
          <div class="table-container">
            <table class="results-table">
              <thead>
                <tr>
                  {#each result.columns as column}
                    <th>{column}</th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each result.rows as row}
                  <tr>
                    {#each row as cell}
                      <td>
                        {#if cell === null}
                          <span class="null-value">NULL</span>
                        {:else if Array.isArray(cell)}
                          <span class="array-value">[{cell.join(", ")}]</span>
                        {:else}
                          {cell}
                        {/if}
                      </td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {:else}
      <div class="status empty">
        <span class="empty-icon">⚡</span>
        <span>Run a query to see results</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .query-view {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
  }

  .query-panel {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-primary);
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
    align-items: center;
  }

  .history-container {
    position: relative;
  }

  .history-button {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
  }

  .history-button:hover:not(:disabled) {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .history-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .history-button.active {
    background: var(--bg-tertiary);
    border-color: var(--accent-primary);
    color: var(--text-primary);
  }

  .format-button {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
  }

  .format-button:hover:not(:disabled) {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .format-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .history-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: var(--spacing-xs);
    width: 400px;
    max-height: 300px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    z-index: 100;
    display: flex;
    flex-direction: column;
  }

  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .clear-history {
    background: none;
    border: none;
    color: var(--accent-danger);
    font-size: 11px;
    cursor: pointer;
    padding: 2px var(--spacing-xs);
  }

  .clear-history:hover {
    text-decoration: underline;
  }

  .history-list {
    flex: 1;
    overflow-y: auto;
  }

  .history-item {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    border-bottom: 1px solid var(--border-primary);
    cursor: pointer;
    text-align: left;
    transition: background 0.2s;
  }

  .history-item:hover {
    background: var(--bg-tertiary);
  }

  .history-item:last-child {
    border-bottom: none;
  }

  .history-item.failed {
    border-left: 2px solid var(--accent-danger);
  }

  .history-query {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-primary);
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  .history-time {
    font-size: 10px;
    color: var(--text-muted);
  }

  .panel-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .run-button {
    background: var(--accent-primary);
    color: var(--bg-primary);
    border: none;
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    transition: opacity 0.2s;
  }

  .run-button:hover:not(:disabled) {
    opacity: 0.9;
  }

  .run-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .shortcut {
    font-family: var(--font-mono);
    font-size: 11px;
    opacity: 0.7;
  }

  .query-editor {
    width: 100%;
    min-height: 120px;
    font-family: var(--font-mono);
    font-size: 13px;
    background: var(--bg-primary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    resize: vertical;
    outline: none;
  }

  .query-editor:focus {
    border-color: var(--accent-primary);
  }

  .query-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .examples {
    display: flex;
    gap: var(--spacing-sm);
    align-items: center;
  }

  .shortcuts {
    display: flex;
    gap: var(--spacing-md);
    font-size: 11px;
    color: var(--text-muted);
  }

  .shortcut-item {
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .shortcut-item kbd {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: 3px;
    padding: 1px 4px;
    font-family: var(--font-mono);
    font-size: 10px;
  }

  .examples-label {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
  }

  .examples-list {
    display: flex;
    gap: var(--spacing-xs);
    flex-wrap: wrap;
  }

  .example-button {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: 4px var(--spacing-sm);
    font-size: 11px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
  }

  .example-button:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--accent-primary);
  }

  .results-panel {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .status {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: var(--spacing-md);
    height: 100%;
    color: var(--text-muted);
    font-size: 14px;
  }

  .status.error {
    color: var(--accent-danger);
  }

  .status.empty {
    color: var(--text-muted);
  }

  .spinner {
    width: 24px;
    height: 24px;
    border: 2px solid var(--border-primary);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .error-icon,
  .empty-icon {
    font-size: 48px;
  }

  .error-content {
    max-width: 600px;
    text-align: center;
  }

  .error-title {
    font-weight: 600;
    margin-bottom: var(--spacing-sm);
  }

  .error-message {
    font-family: var(--font-mono);
    font-size: 12px;
    background: var(--bg-secondary);
    padding: var(--spacing-md);
    border-radius: var(--radius-sm);
    overflow-x: auto;
    text-align: left;
  }

  .results-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .results-header {
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-primary);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .result-count {
    font-size: 12px;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .export-buttons {
    display: flex;
    gap: var(--spacing-xs);
  }

  .export-button {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: 4px var(--spacing-sm);
    font-size: 11px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
  }

  .export-button:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--accent-primary);
  }

  .no-results {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    color: var(--text-muted);
    font-size: 14px;
  }

  .table-container {
    flex: 1;
    overflow: auto;
  }

  .results-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .results-table thead {
    position: sticky;
    top: 0;
    background: var(--bg-secondary);
    z-index: 10;
  }

  .results-table th {
    text-align: left;
    padding: var(--spacing-sm) var(--spacing-md);
    font-weight: 600;
    color: var(--text-secondary);
    border-bottom: 2px solid var(--border-primary);
    white-space: nowrap;
  }

  .results-table td {
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
    color: var(--text-primary);
    max-width: 400px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .results-table tbody tr:hover {
    background: var(--bg-secondary);
  }

  .null-value {
    color: var(--text-muted);
    font-style: italic;
    font-size: 11px;
  }

  .array-value {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--accent-primary);
  }
</style>
