<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { subscribeToToasts, dismissToast, type Toast } from "../sdk/toast.svelte";

  let toasts = $state<Toast[]>([]);
  let unsubscribe: (() => void) | null = null;

  onMount(() => {
    unsubscribe = subscribeToToasts((newToasts) => {
      toasts = newToasts;
    });
  });

  onDestroy(() => {
    unsubscribe?.();
  });

  function getIcon(type: Toast["type"]): string {
    switch (type) {
      case "success":
        return "✓";
      case "error":
        return "✗";
      case "warning":
        return "⚠";
      case "info":
        return "ℹ";
    }
  }
</script>

<div class="toast-container">
  {#each toasts as toast (toast.id)}
    <div class="toast toast-{toast.type}" role="alert">
      <div class="toast-icon">{getIcon(toast.type)}</div>
      <div class="toast-content">
        <div class="toast-title">{toast.title}</div>
        {#if toast.message}
          <div class="toast-message">{toast.message}</div>
        {/if}
      </div>
      <div class="toast-actions">
        {#if toast.action}
          <button class="toast-action-btn" onclick={toast.action.onClick}>
            {toast.action.label}
          </button>
        {/if}
        <button
          class="toast-dismiss"
          onclick={() => dismissToast(toast.id)}
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    bottom: 40px; /* Above status bar */
    right: 16px;
    z-index: 1000;
    display: flex;
    flex-direction: column-reverse;
    gap: 8px;
    max-width: 360px;
    pointer-events: none;
  }

  .toast {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 14px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    animation: slideIn 0.2s ease-out;
    pointer-events: auto;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateX(20px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  .toast-icon {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    border-radius: 50%;
  }

  .toast-success .toast-icon {
    background: var(--accent-success, #22c55e);
    color: white;
  }

  .toast-error .toast-icon {
    background: var(--accent-danger, #ef4444);
    color: white;
  }

  .toast-warning .toast-icon {
    background: var(--accent-warning, #f59e0b);
    color: white;
  }

  .toast-info .toast-icon {
    background: var(--accent-primary, #3b82f6);
    color: white;
  }

  .toast-content {
    flex: 1;
    min-width: 0;
  }

  .toast-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.3;
  }

  .toast-message {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
    line-height: 1.4;
  }

  .toast-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .toast-action-btn {
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
    color: var(--accent-primary, #3b82f6);
    background: transparent;
    border: 1px solid var(--accent-primary, #3b82f6);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .toast-action-btn:hover {
    background: var(--accent-primary, #3b82f6);
    color: white;
  }

  .toast-dismiss {
    padding: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    color: var(--text-muted);
    background: transparent;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .toast-dismiss:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  /* Border accents by type */
  .toast-success {
    border-left: 3px solid var(--accent-success, #22c55e);
  }

  .toast-error {
    border-left: 3px solid var(--accent-danger, #ef4444);
  }

  .toast-warning {
    border-left: 3px solid var(--accent-warning, #f59e0b);
  }

  .toast-info {
    border-left: 3px solid var(--accent-primary, #3b82f6);
  }
</style>
