# Treeline Plugin Template

A starting point for building Treeline plugins.

## Quick Start

### 1. Create your plugin

```bash
tl plugin new my-plugin
cd my-plugin
npm install
```

### 2. Build and test

```bash
npm run build
tl plugin install .
# Restart Treeline to load the plugin
```

### 3. Develop

Edit `src/index.ts` and `src/*View.svelte` to build your plugin.

Use watch mode for faster iteration:
```bash
npm run dev
```

## Project Structure

```
my-plugin/
├── manifest.json      # Plugin metadata and permissions
├── src/
│   ├── index.ts       # Entry point (registers views/commands)
│   ├── types.ts       # TypeScript types for SDK
│   └── *View.svelte   # Your UI components
├── dist/
│   └── index.js       # Built plugin (generated)
└── package.json
```

## Releasing

When ready to share your plugin:

```bash
# Create a GitHub repo and push your code, then:
./scripts/release.sh 0.1.0
```

This tags the release and pushes to GitHub. The included GitHub Action automatically builds and publishes the release with the required assets.

## Submit to Community Plugins

1. Ensure your plugin has at least one GitHub release
2. Open a PR to [treeline-money](https://github.com/zack-schrag/treeline-money) adding your plugin to `community-plugins.json`:

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "description": "What it does",
  "author": "Your Name",
  "repo": "https://github.com/you/my-plugin"
}
```

## Documentation

- **[Full SDK Reference](https://github.com/zack-schrag/treeline-money/blob/main/docs/plugins.md)** - Complete API documentation
- **[AGENTS.md](./AGENTS.md)** - Quick reference for AI-assisted development
