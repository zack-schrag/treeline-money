<script lang="ts">
  import { onMount } from "svelte";
  import Sidebar from "./Sidebar.svelte";
  import TabBar from "./TabBar.svelte";
  import ContentArea from "./ContentArea.svelte";
  import StatusBar from "./StatusBar.svelte";
  import CommandPalette from "./CommandPalette.svelte";
  import SettingsModal from "./SettingsModal.svelte";
  import ToastContainer from "./ToastContainer.svelte";
  import { Icon } from "../shared";
  import { registry, getDemoMode, disableDemo, toast, getAppSetting } from "../sdk";

  let commandPaletteOpen = $state(false);
  let settingsModalOpen = $state(false);
  let isDemoMode = $state(false);
  let hideDemoBanner = $state(false);
  let isExitingDemo = $state(false);

  // Check demo mode on mount and subscribe to refresh events
  onMount(() => {
    checkDemoMode();
    const unsubscribe = registry.on("data:refresh", checkDemoMode);
    return unsubscribe;
  });

  async function checkDemoMode() {
    isDemoMode = await getDemoMode();
    hideDemoBanner = (await getAppSetting("hideDemoBanner")) ?? false;
  }

  async function handleExitDemo() {
    isExitingDemo = true;
    try {
      toast.info("Exiting demo mode...", "Switching to real data");
      await disableDemo();
      isDemoMode = false;
      toast.success("Demo mode disabled", "Now using your real data");
      registry.emit("data:refresh");
    } catch (e) {
      toast.error("Failed to exit demo mode", e instanceof Error ? e.message : String(e));
    } finally {
      isExitingDemo = false;
    }
  }

  // Register core commands
  $effect(() => {
    registry.registerCommand({
      id: "core:command-palette",
      name: "Open Command Palette",
      category: "Core",
      shortcut: "⌘P",
      execute: () => {
        commandPaletteOpen = true;
      },
    });

    registry.registerCommand({
      id: "core:settings",
      name: "Open Settings",
      category: "Core",
      shortcut: "⌘,",
      execute: () => {
        settingsModalOpen = true;
      },
    });
  });

  // Global keyboard shortcuts
  function handleKeydown(e: KeyboardEvent) {
    // Command palette: Cmd+P or Ctrl+P
    if ((e.metaKey || e.ctrlKey) && e.key === "p") {
      e.preventDefault();
      commandPaletteOpen = true;
    }

    // Settings: Cmd+, or Ctrl+,
    if ((e.metaKey || e.ctrlKey) && e.key === ",") {
      e.preventDefault();
      settingsModalOpen = true;
    }

    // Close tab: Cmd+W
    if ((e.metaKey || e.ctrlKey) && e.key === "w") {
      e.preventDefault();
      const activeTab = registry.activeTab;
      if (activeTab) {
        registry.closeTab(activeTab.id);
      }
    }

    // Switch tabs: Cmd+1-9
    if ((e.metaKey || e.ctrlKey) && e.key >= "1" && e.key <= "9") {
      e.preventDefault();
      const index = parseInt(e.key) - 1;
      const tabs = registry.tabs;
      if (tabs[index]) {
        registry.setActiveTab(tabs[index].id);
      }
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="shell">
  <Sidebar />

  <div class="main-area">
    <TabBar />
    {#if isDemoMode && !hideDemoBanner}
      <div class="demo-banner">
        <span class="demo-icon"><Icon name="beaker" size={16} /></span>
        <span class="demo-text">
          <strong>Demo Mode</strong> — Exploring with sample data
        </span>
        <button class="demo-exit-btn" onclick={handleExitDemo} disabled={isExitingDemo}>
          <Icon name="log-out" size={12} />
          {isExitingDemo ? "Exiting..." : "Exit Demo Mode"}
        </button>
      </div>
    {/if}
    <ContentArea />
  </div>

  <StatusBar />

  <CommandPalette bind:isOpen={commandPaletteOpen} />
  <SettingsModal isOpen={settingsModalOpen} onClose={() => settingsModalOpen = false} />
  <ToastContainer />
</div>

<style>
  .shell {
    width: 100vw;
    height: 100vh;
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: 1fr auto;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-family: var(--font-sans);
  }

  .main-area {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .demo-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 1rem;
    background: linear-gradient(90deg, #b45309 0%, #d97706 100%);
    color: white;
    font-size: 0.875rem;
  }

  .demo-icon {
    display: flex;
    align-items: center;
  }

  .demo-text {
    flex: 1;
  }

  .demo-text strong {
    font-weight: 600;
  }

  .demo-exit-btn {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 4px;
    color: white;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .demo-exit-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.3);
  }

  .demo-exit-btn:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  :global(footer.statusbar) {
    grid-column: 1 / -1;
  }
</style>
