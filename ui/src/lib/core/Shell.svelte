<script lang="ts">
  import Sidebar from "./Sidebar.svelte";
  import TabBar from "./TabBar.svelte";
  import ContentArea from "./ContentArea.svelte";
  import StatusBar from "./StatusBar.svelte";
  import CommandPalette from "./CommandPalette.svelte";
  import SettingsModal from "./SettingsModal.svelte";
  import ToastContainer from "./ToastContainer.svelte";
  import { registry } from "../sdk";

  let commandPaletteOpen = $state(false);
  let settingsModalOpen = $state(false);

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

  :global(footer.statusbar) {
    grid-column: 1 / -1;
  }
</style>
