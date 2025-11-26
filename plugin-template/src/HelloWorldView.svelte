<script lang="ts">
  let count = $state(0);

  function increment() {
    count++;
  }

  function reset() {
    count = 0;
  }
</script>

<div class="p-6 space-y-4">
  <h1 class="text-2xl font-bold">👋 Hello World Plugin</h1>

  <p class="text-gray-600">
    This is an external plugin loaded from <code class="bg-gray-100 px-2 py-1 rounded text-sm font-mono">~/.treeline/plugins/</code>
  </p>

  <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-2">
    <p class="text-sm text-blue-800">
      <span class="font-semibold">Plugin ID:</span>
      <code class="font-mono bg-white px-2 py-1 rounded ml-2">hello-world</code>
    </p>
    <p class="text-sm text-blue-800">
      <span class="font-semibold">Status:</span>
      <span class="ml-2">✓ Loaded successfully</span>
    </p>
    <p class="text-sm text-blue-800">
      <span class="font-semibold">Counter:</span>
      <span class="ml-2 text-lg font-bold">{count}</span>
    </p>
  </div>

  <div class="flex gap-2">
    <button
      onclick={increment}
      class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
    >
      Increment
    </button>

    <button
      onclick={reset}
      class="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition"
    >
      Reset
    </button>
  </div>

  <div class="mt-6 pt-6 border-t border-gray-200">
    <h2 class="text-lg font-semibold mb-2">Plugin Development</h2>
    <p class="text-sm text-gray-600">
      This plugin demonstrates how to create external plugins for Treeline.
      See the README for more information on plugin development.
    </p>
  </div>
</div>
