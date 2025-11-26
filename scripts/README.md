# Treeline Scripts

## Release Script

Automates the release process for Treeline.

### Prerequisites

1. **GitHub CLI** must be installed and authenticated:
   ```bash
   brew install gh
   gh auth login
   ```

2. Must be on `main` branch with clean working directory

3. All changes must be committed

### Usage

```bash
./scripts/release.sh <version>
```

**Examples:**
```bash
./scripts/release.sh v0.2.0
./scripts/release.sh 0.2.0   # 'v' prefix is optional
```

### What It Does

1. ✅ Validates version format (semver)
2. ✅ Checks you're on main branch
3. ✅ Ensures working directory is clean
4. ✅ Pulls latest changes from origin
5. ✅ Updates version in `cli/pyproject.toml`
6. ✅ Commits version bump
7. ✅ Creates git tag
8. ✅ Pushes commits and tags
9. ✅ Creates GitHub Release with auto-generated notes

### What Happens Next (Automated)

Once the GitHub Release is created, the GitHub Actions workflow automatically:

1. **Runs tests** - Ensures code quality
2. **Publishes to PyPI** - Via trusted publishing
3. **Builds binaries** - For all platforms:
   - Linux x64
   - macOS x64
   - macOS ARM64 (Apple Silicon)
   - Windows x64
4. **Uploads binaries** - To the GitHub Release

### Monitoring

After running the script, you can monitor progress:

- **Actions**: https://github.com/zack-schrag/treeline-money/actions
- **Releases**: https://github.com/zack-schrag/treeline-money/releases

### Troubleshooting

**"gh command not found"**
```bash
brew install gh
```

**"GitHub CLI is not authenticated"**
```bash
gh auth login
```

**"Working directory has uncommitted changes"**
```bash
git status
git add .
git commit -m "Your changes"
```

**"Must be on main branch"**
```bash
git checkout main
```

### Testing

To test the script without actually creating a release, you can:

1. Create a test branch
2. Make changes
3. Run the script
4. Delete the tag and release manually

Or just review the script code to see what it does.
