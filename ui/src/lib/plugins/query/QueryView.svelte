<script lang="ts">
  import { executeQuery, type QueryResult } from "../../sdk";
  import { onMount } from "svelte";
  import { EditorView, keymap, placeholder } from "@codemirror/view";
  import { EditorState } from "@codemirror/state";
  import { sql } from "@codemirror/lang-sql";
  import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
  import { tags } from "@lezer/highlight";
  import { history as cmHistory, defaultKeymap, historyKeymap } from "@codemirror/commands";

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
  let executionTime = $state<number | null>(null);

  // Schema state
  interface TableSchema {
    name: string;
    columns: { name: string; type: string }[];
  }
  let schema = $state<TableSchema[]>([]);
  let showSchema = $state(false);
  let schemaLoading = $state(false);

  async function loadSchema() {
    if (schema.length > 0) {
      showSchema = !showSchema;
      return;
    }

    schemaLoading = true;
    try {
      // Get list of tables
      const tablesResult = await executeQuery("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'");
      const tableNames = tablesResult.rows.map(row => row[0] as string);

      // Get columns for each table
      const tables: TableSchema[] = [];
      for (const tableName of tableNames) {
        const columnsResult = await executeQuery(
          `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '${tableName}' ORDER BY ordinal_position`
        );
        tables.push({
          name: tableName,
          columns: columnsResult.rows.map(row => ({
            name: row[0] as string,
            type: row[1] as string,
          })),
        });
      }
      schema = tables;
      showSchema = true;
    } catch (e) {
      console.error("Failed to load schema:", e);
    } finally {
      schemaLoading = false;
    }
  }

  // Sorting state
  let sortColumn = $state<number | null>(null);
  let sortDirection = $state<"asc" | "desc">("asc");

  // Derived sorted rows
  let sortedRows = $derived.by(() => {
    if (!result || sortColumn === null) return result?.rows ?? [];

    const rows = [...result.rows];
    rows.sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle nulls
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return sortDirection === "asc" ? 1 : -1;
      if (bVal === null) return sortDirection === "asc" ? -1 : 1;

      // Compare values
      let cmp = 0;
      if (typeof aVal === "number" && typeof bVal === "number") {
        cmp = aVal - bVal;
      } else if (Array.isArray(aVal) && Array.isArray(bVal)) {
        cmp = aVal.join(",").localeCompare(bVal.join(","));
      } else {
        cmp = String(aVal).localeCompare(String(bVal));
      }

      return sortDirection === "asc" ? cmp : -cmp;
    });

    return rows;
  });

  function toggleSort(colIndex: number) {
    if (sortColumn === colIndex) {
      // Toggle direction or clear
      if (sortDirection === "asc") {
        sortDirection = "desc";
      } else {
        sortColumn = null;
        sortDirection = "asc";
      }
    } else {
      sortColumn = colIndex;
      sortDirection = "asc";
    }
  }

  // Copy to clipboard
  let copiedCell = $state<{ row: number; col: number } | null>(null);

  async function copyCell(value: unknown, rowIndex: number, colIndex: number) {
    let text: string;
    if (value === null) {
      text = "";
    } else if (Array.isArray(value)) {
      text = value.join(", ");
    } else {
      text = String(value);
    }

    try {
      await navigator.clipboard.writeText(text);
      copiedCell = { row: rowIndex, col: colIndex };
      setTimeout(() => {
        copiedCell = null;
      }, 1500);
    } catch (e) {
      console.error("Failed to copy:", e);
    }
  }

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
    executionTime = null;
    sortColumn = null;
    sortDirection = "asc";

    const startTime = performance.now();

    try {
      result = await executeQuery(query);
      executionTime = performance.now() - startTime;
      addToHistory(query, true);
    } catch (e) {
      executionTime = performance.now() - startTime;
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
    // Update CodeMirror content
    if (editorView) {
      editorView.dispatch({
        changes: { from: 0, to: editorView.state.doc.length, insert: "" }
      });
    }
  }

  let viewEl: HTMLDivElement;
  let editorContainer: HTMLDivElement;
  let editorView: EditorView | null = null;

  // Custom theme using CSS variables
  const customTheme = EditorView.theme({
    "&": {
      backgroundColor: "var(--bg-primary)",
      color: "var(--text-primary)",
      fontSize: "13px",
      minHeight: "120px",
    },
    ".cm-content": {
      fontFamily: "var(--font-mono)",
      caretColor: "var(--text-primary)",
      padding: "var(--spacing-md)",
    },
    ".cm-cursor": {
      borderLeftColor: "var(--text-primary)",
    },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
      backgroundColor: "rgba(255, 255, 255, 0.1)",
    },
    ".cm-activeLine": {
      backgroundColor: "transparent",
    },
    ".cm-gutters": {
      display: "none",
    },
    ".cm-placeholder": {
      color: "var(--text-muted)",
    },
    "&.cm-focused": {
      outline: "none",
    },
  });

  // Syntax highlighting colors matching theme
  const customHighlighting = HighlightStyle.define([
    { tag: tags.keyword, color: "#c678dd" },           // Purple for keywords
    { tag: tags.operator, color: "#56b6c2" },          // Cyan for operators
    { tag: tags.string, color: "#98c379" },            // Green for strings
    { tag: tags.number, color: "#d19a66" },            // Orange for numbers
    { tag: tags.comment, color: "#5c6370", fontStyle: "italic" },
    { tag: tags.function(tags.variableName), color: "#61afef" }, // Blue for functions
    { tag: tags.variableName, color: "#e5c07b" },      // Yellow for identifiers
    { tag: tags.punctuation, color: "#abb2bf" },
    { tag: tags.null, color: "#d19a66" },
  ]);

  onMount(() => {
    const state = EditorState.create({
      doc: query,
      extensions: [
        sql(),
        customTheme,
        syntaxHighlighting(customHighlighting),
        placeholder("Enter SQL query..."),
        cmHistory(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            query = update.state.doc.toString();
          }
        }),
      ],
    });

    editorView = new EditorView({
      state,
      parent: editorContainer,
    });

    return () => {
      editorView?.destroy();
    };
  });

  // Update editor when query changes externally (e.g., from history or examples)
  $effect(() => {
    if (editorView && editorView.state.doc.toString() !== query) {
      editorView.dispatch({
        changes: { from: 0, to: editorView.state.doc.length, insert: query }
      });
    }
  });

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
    // Cmd/Ctrl + Shift + F to format
    else if (isMod && e.shiftKey && e.key === "f") {
      e.preventDefault();
      formatQuery();
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
      query: "SELECT tag, SUM(amount) as total FROM (SELECT unnest(tags) as tag, amount FROM transactions WHERE amount < 0) GROUP BY tag ORDER BY total",
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

<div class="query-view" bind:this={viewEl} role="region" aria-label="SQL Query Editor">
  <div class="query-panel" role="form" aria-label="Query input">
    <div class="panel-header">
      <h2 class="panel-title">SQL Query</h2>
      <div class="header-actions" role="toolbar" aria-label="Query actions">
        <div class="history-container">
          <button
            class="history-button"
            class:active={showHistory}
            onclick={() => (showHistory = !showHistory)}
            disabled={history.length === 0}
            aria-expanded={showHistory}
            aria-haspopup="listbox"
            aria-label={`Query history, ${history.length} entries`}
          >
            History ({history.length})
          </button>
          {#if showHistory}
            <div class="history-dropdown" role="listbox" aria-label="Query history">
              <div class="history-header">
                <span id="history-title">Query History</span>
                <button class="clear-history" onclick={clearHistory} aria-label="Clear all history">Clear</button>
              </div>
              <div class="history-list" aria-labelledby="history-title">
                {#each history as entry, i}
                  <button
                    class="history-item"
                    class:failed={!entry.success}
                    onclick={() => loadFromHistory(entry)}
                    role="option"
                    aria-selected="false"
                    aria-label={`${entry.success ? '' : 'Failed: '}${entry.query.slice(0, 50)}${entry.query.length > 50 ? '...' : ''}, ${formatTimestamp(entry.timestamp)}`}
                  >
                    <pre class="history-query">{entry.query}</pre>
                    <span class="history-time">{formatTimestamp(entry.timestamp)}</span>
                  </button>
                {/each}
              </div>
            </div>
          {/if}
        </div>
        <button class="format-button" onclick={formatQuery} disabled={!query.trim()} aria-label="Format SQL query">
          Format
        </button>
        <button
          class="schema-button"
          class:active={showSchema}
          onclick={loadSchema}
          disabled={schemaLoading}
          aria-expanded={showSchema}
          aria-label={schemaLoading ? "Loading database schema" : "Show database schema"}
        >
          {schemaLoading ? "Loading..." : "Schema"}
        </button>
        <button class="run-button" onclick={runQuery} disabled={isLoading} aria-label="Run query (Command+Enter)">
          {isLoading ? "Running..." : "Run Query"}
          <span class="shortcut" aria-hidden="true">⌘↵</span>
        </button>
      </div>
    </div>

    <div class="query-editor-container">
      <div class="query-editor" bind:this={editorContainer} role="textbox" aria-label="SQL query input" aria-multiline="true"></div>
      {#if showSchema}
        <aside class="schema-panel" aria-label="Database schema">
          <div class="schema-header">
            <span id="schema-title">Database Schema</span>
            <button class="schema-close" onclick={() => showSchema = false} aria-label="Close schema panel">×</button>
          </div>
          <div class="schema-content" aria-labelledby="schema-title">
            {#each [...schema].sort((a, b) => {
              const aIsSys = a.name.startsWith('sys_');
              const bIsSys = b.name.startsWith('sys_');
              if (aIsSys !== bIsSys) return aIsSys ? 1 : -1;
              return a.name.localeCompare(b.name);
            }) as table}
              <div class="schema-table" class:sys-table={table.name.startsWith('sys_')}>
                <div class="table-name" role="heading" aria-level="3">{table.name}</div>
                <ul class="table-columns" aria-label={`Columns in ${table.name}`}>
                  {#each table.columns as column}
                    <li class="column-row">
                      <span class="column-name">{column.name}</span>
                      <span class="column-type" aria-label="type">{column.type}</span>
                    </li>
                  {/each}
                </ul>
              </div>
            {/each}
          </div>
        </aside>
      {/if}
    </div>

    <div class="query-footer">
      <div class="examples" role="group" aria-label="Example queries">
        <div class="examples-label" id="examples-label">Examples:</div>
        <div class="examples-list" aria-labelledby="examples-label">
          {#each examples as example}
            <button class="example-button" onclick={() => loadExample(example.query)} aria-label={`Load example: ${example.name}`}>
              {example.name}
            </button>
          {/each}
        </div>
      </div>
      <div class="shortcuts" aria-label="Keyboard shortcuts">
        <span class="shortcut-item"><kbd>⌘</kbd><kbd>↵</kbd> Run</span>
        <span class="shortcut-item"><kbd>⌘</kbd><kbd>L</kbd> Clear</span>
        <span class="shortcut-item"><kbd>⌘</kbd><kbd>⇧</kbd><kbd>F</kbd> Format</span>
      </div>
    </div>
  </div>

  <div class="results-panel" role="region" aria-label="Query results" aria-live="polite">
    {#if isLoading}
      <div class="status" role="status" aria-busy="true">
        <div class="spinner" aria-hidden="true"></div>
        <span>Running query...</span>
      </div>
    {:else if error}
      <div class="status error" role="alert">
        <svg class="error-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
        </svg>
        <div class="error-content">
          <div class="error-title">Query Error</div>
          <pre class="error-message">{error}</pre>
        </div>
      </div>
    {:else if result}
      <div class="results-content">
        <div class="results-header">
          <div class="results-meta" aria-live="polite">
            <span class="result-count">{result.row_count} {result.row_count === 1 ? 'row' : 'rows'}</span>
            {#if executionTime !== null}
              <span class="execution-time" aria-label={`Query took ${executionTime < 1000 ? Math.round(executionTime) + ' milliseconds' : (executionTime / 1000).toFixed(2) + ' seconds'}`}>
                {executionTime < 1000
                  ? `${Math.round(executionTime)}ms`
                  : `${(executionTime / 1000).toFixed(2)}s`}
              </span>
            {/if}
          </div>
          <div class="export-buttons" role="group" aria-label="Export options">
            <button class="export-button" onclick={exportCSV} aria-label="Export results as CSV">Export CSV</button>
            <button class="export-button" onclick={exportJSON} aria-label="Export results as JSON">Export JSON</button>
          </div>
        </div>

        {#if result.row_count === 0}
          <div class="no-results" role="status">No results returned</div>
        {:else}
          <div class="table-container">
            <table class="results-table" aria-label="Query results">
              <thead>
                <tr>
                  {#each result.columns as column, i}
                    <th
                      class="sortable"
                      class:sorted={sortColumn === i}
                      onclick={() => toggleSort(i)}
                      aria-sort={sortColumn === i ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}
                      role="columnheader"
                      tabindex="0"
                      onkeydown={(e) => e.key === 'Enter' && toggleSort(i)}
                    >
                      <span class="column-name">{column}</span>
                      {#if sortColumn === i}
                        <span class="sort-indicator" aria-hidden="true">{sortDirection === "asc" ? "▲" : "▼"}</span>
                      {/if}
                    </th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each sortedRows as row, rowIndex}
                  <tr>
                    {#each row as cell, colIndex}
                      <td
                        class="copyable"
                        class:copied={copiedCell?.row === rowIndex && copiedCell?.col === colIndex}
                        onclick={() => copyCell(cell, rowIndex, colIndex)}
                        onkeydown={(e) => e.key === 'Enter' && copyCell(cell, rowIndex, colIndex)}
                        tabindex="0"
                        role="gridcell"
                        aria-label={`${result.columns[colIndex]}: ${cell === null ? 'null' : Array.isArray(cell) ? cell.join(', ') : cell}. Click to copy`}
                      >
                        {#if copiedCell?.row === rowIndex && copiedCell?.col === colIndex}
                          <span class="copied-indicator" role="status">Copied!</span>
                        {:else if cell === null}
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
      <div class="status empty" role="status">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
        <span>Run a query to see results</span>
        {#if schema.length > 0}
          <div class="empty-schema">
            <div class="empty-schema-title">Available Tables</div>
            <nav class="empty-schema-tables" aria-label="Quick table queries">
              {#each [...schema].sort((a, b) => {
                const aIsSys = a.name.startsWith('sys_');
                const bIsSys = b.name.startsWith('sys_');
                if (aIsSys !== bIsSys) return aIsSys ? 1 : -1;
                return a.name.localeCompare(b.name);
              }) as table}
                <button class="empty-schema-table" class:sys-table={table.name.startsWith('sys_')} onclick={() => query = `SELECT * FROM ${table.name} LIMIT 100`} aria-label={`Query ${table.name} table`}>
                  {table.name}
                </button>
              {/each}
            </nav>
          </div>
        {:else}
          <button class="load-schema-button" onclick={loadSchema} disabled={schemaLoading} aria-label="Load database tables">
            {schemaLoading ? "Loading..." : "Show available tables"}
          </button>
        {/if}
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
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .query-editor:focus-within {
    border-color: var(--accent-primary);
  }

  .query-editor :global(.cm-editor) {
    min-height: 120px;
  }

  .query-editor :global(.cm-scroller) {
    overflow: auto;
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
    width: 48px;
    height: 48px;
  }

  .error-icon {
    color: var(--accent-danger);
  }

  .empty-icon {
    color: var(--accent-primary);
    opacity: 0.6;
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
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
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

  .results-meta {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .result-count {
    font-size: 12px;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .execution-time {
    font-size: 11px;
    font-family: var(--font-mono);
    color: var(--text-muted);
    padding: 2px 6px;
    background: var(--bg-primary);
    border-radius: var(--radius-sm);
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

  .results-table th.sortable {
    cursor: pointer;
    user-select: none;
    transition: color 0.2s;
  }

  .results-table th.sortable:hover {
    color: var(--text-primary);
  }

  .results-table th.sorted {
    color: var(--accent-primary);
  }

  .results-table th .column-name {
    margin-right: var(--spacing-xs);
  }

  .results-table th .sort-indicator {
    font-size: 10px;
    opacity: 0.8;
  }

  .results-table td {
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
    color: var(--text-primary);
    max-width: 400px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .results-table td.copyable {
    cursor: pointer;
    transition: background 0.15s;
  }

  .results-table td.copyable:hover {
    background: var(--bg-tertiary);
  }

  .results-table td.copied {
    background: rgba(152, 195, 121, 0.2);
  }

  .copied-indicator {
    color: #98c379;
    font-size: 11px;
    font-weight: 500;
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

  /* Schema button and panel */
  .schema-button {
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
  }

  .schema-button:hover:not(:disabled) {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .schema-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .schema-button.active {
    background: var(--bg-tertiary);
    border-color: var(--accent-primary);
    color: var(--text-primary);
  }

  .query-editor-container {
    display: flex;
    gap: var(--spacing-md);
  }

  .query-editor-container .query-editor {
    flex: 1;
  }

  .schema-panel {
    width: 280px;
    background: var(--bg-primary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    max-height: 200px;
    overflow: hidden;
  }

  .schema-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .schema-close {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 18px;
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }

  .schema-close:hover {
    color: var(--text-primary);
  }

  .schema-content {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-sm);
  }

  .schema-table {
    margin-bottom: var(--spacing-sm);
  }

  .schema-table:last-child {
    margin-bottom: 0;
  }

  .schema-table .table-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--accent-primary);
    margin-bottom: var(--spacing-xs);
    padding: 2px var(--spacing-xs);
    background: var(--bg-tertiary);
    border-radius: var(--radius-sm);
  }

  .schema-table.sys-table {
    opacity: 0.5;
  }

  .schema-table.sys-table .table-name {
    color: var(--text-muted);
  }

  .table-columns {
    padding-left: var(--spacing-sm);
    list-style: none;
    margin: 0;
  }

  .column-row {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    padding: 2px 0;
  }

  ul.table-columns {
    padding-left: var(--spacing-sm);
  }

  li.column-row {
    list-style: none;
  }

  .column-row .column-name {
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .column-row .column-type {
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 10px;
  }

  /* Empty state schema display */
  .empty-schema {
    margin-top: var(--spacing-lg);
    text-align: center;
  }

  .empty-schema-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .empty-schema-tables {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
    justify-content: center;
  }

  .empty-schema-table {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 12px;
    font-family: var(--font-mono);
    color: var(--accent-primary);
    cursor: pointer;
    transition: all 0.2s;
  }

  .empty-schema-table:hover {
    background: var(--bg-tertiary);
    border-color: var(--accent-primary);
  }

  .empty-schema-table.sys-table {
    opacity: 0.5;
    color: var(--text-muted);
  }

  .empty-schema-table.sys-table:hover {
    opacity: 0.7;
  }

  .load-schema-button {
    margin-top: var(--spacing-lg);
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;
  }

  .load-schema-button:hover:not(:disabled) {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--accent-primary);
  }

  .load-schema-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
