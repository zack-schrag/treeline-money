<script lang="ts">
  import { executeQuery, type QueryResult } from "../../sdk";

  let query = $state("SELECT * FROM transactions LIMIT 10");
  let result = $state<QueryResult | null>(null);
  let isLoading = $state(false);
  let error = $state<string | null>(null);

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
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to execute query";
      console.error("Query error:", e);
    } finally {
      isLoading = false;
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    // Cmd/Ctrl + Enter to run query
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      runQuery();
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
</script>

<div class="query-view">
  <div class="query-panel">
    <div class="panel-header">
      <h2 class="panel-title">SQL Query</h2>
      <button class="run-button" onclick={runQuery} disabled={isLoading}>
        {isLoading ? "Running..." : "Run Query"}
        <span class="shortcut">⌘↵</span>
      </button>
    </div>

    <textarea
      class="query-editor"
      bind:value={query}
      onkeydown={handleKeyDown}
      placeholder="Enter SQL query..."
      spellcheck="false"
    ></textarea>

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

  .examples {
    display: flex;
    gap: var(--spacing-sm);
    align-items: center;
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
  }

  .result-count {
    font-size: 12px;
    font-family: var(--font-mono);
    color: var(--text-muted);
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
