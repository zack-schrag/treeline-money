<script lang="ts">
  /**
   * RowMenu - Shared row context menu component (⋮ button with dropdown)
   *
   * Usage:
   * <RowMenu
   *   items={[
   *     { label: "Edit", action: () => editItem() },
   *     { label: "Delete", action: () => deleteItem(), danger: true },
   *   ]}
   *   isOpen={openMenuId === item.id}
   *   onToggle={() => toggleMenu(item.id)}
   * />
   */

  export interface RowMenuItem {
    /** Display label */
    label: string;
    /** Action to execute when clicked */
    action: () => void;
    /** Whether this is a destructive action (styled in red) */
    danger?: boolean;
    /** Whether this item is disabled */
    disabled?: boolean;
  }

  interface Props {
    /** Menu items to display */
    items: RowMenuItem[];
    /** Whether the dropdown is currently open */
    isOpen: boolean;
    /** Called when the button is clicked to toggle the menu */
    onToggle: (e: MouseEvent) => void;
    /** Optional title for the button */
    title?: string;
  }

  let { items, isOpen, onToggle, title = "Actions" }: Props = $props();

  function handleItemClick(item: RowMenuItem, e: MouseEvent) {
    e.stopPropagation();
    if (!item.disabled) {
      item.action();
    }
  }

  function handleButtonClick(e: MouseEvent) {
    e.stopPropagation();
    onToggle(e);
  }
</script>

<div class="row-menu">
  <button
    class="row-menu-btn"
    onclick={handleButtonClick}
    {title}
    aria-haspopup="true"
    aria-expanded={isOpen}
  >⋮</button>

  {#if isOpen}
    <div class="row-menu-dropdown" role="menu">
      {#each items as item}
        <button
          class="menu-item"
          class:danger={item.danger}
          class:disabled={item.disabled}
          onclick={(e) => handleItemClick(item, e)}
          disabled={item.disabled}
          role="menuitem"
        >
          {item.label}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .row-menu {
    position: relative;
    flex-shrink: 0;
  }

  .row-menu-btn {
    width: 24px;
    height: 24px;
    padding: 0;
    background: transparent;
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-muted);
    font-size: 14px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* Show button on row hover or when row has cursor */
  :global(.row:hover) .row-menu-btn,
  :global(.row.cursor) .row-menu-btn,
  .row-menu-btn[aria-expanded="true"] {
    opacity: 1;
  }

  .row-menu-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--text-muted);
  }

  .row-menu-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    z-index: 100;
    min-width: 120px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    overflow: hidden;
    margin-top: 2px;
  }

  .menu-item {
    display: block;
    width: 100%;
    padding: 8px 12px;
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-size: 12px;
    text-align: left;
    cursor: pointer;
    transition: background 0.1s;
  }

  .menu-item:hover:not(.disabled) {
    background: var(--bg-tertiary);
  }

  .menu-item.danger {
    color: var(--accent-danger, #ef4444);
  }

  .menu-item.danger:hover:not(.disabled) {
    background: rgba(239, 68, 68, 0.1);
  }

  .menu-item.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
