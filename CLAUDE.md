# Project Guidelines for Claude

## Markdown Files

All markdown files must pass `markdownlint` cleanly:

1. Run `npx markdownlint <file.md>` before considering any markdown file complete
2. Ask for user approval before adding markdownlint disable annotations
3. When using local markdownlint annotations, use the save/restore pattern:

   ```markdown
   <!-- markdownlint-save -->
   <!-- markdownlint-disable MD029 -->

   ... content requiring exception ...

   <!-- markdownlint-restore -->
   ```

4. Common rules to be aware of:
   - MD013: Line length (often disabled at file level)
   - MD029: Ordered list prefix (disable locally if continuous numbering intentional)
   - MD060: Table column spacing (use spaces around separator dashes)
   - MD022/MD032: Blank lines around headings and lists

## Code Style

1. No bare functions that are not methods of classes or local to a method
2. Exception: a single `main()` function in `__main__.py` that sets up the main
   App object and calls it
3. All schemas and data files must be bundled as package resources (available
   when installed as .whl)
4. Reference application for style: `github.com/terrillmoore/annotate_film_scans`

## File Location Constraints

**Critical**: The tool never writes files to its own installation or source
directory. All outputs go to:

- **User config directory**: User-level settings, OAuth credentials, cached data
- **Task directory**: Project-specific files, `.gitignore` updates, VS Code schemas

This ensures the tool works correctly whether installed via pip/uv or run from
a local checkout.

## Build and Test

- Use `uv` for project and dependency management
- Use `pytest` for testing with mocks for external API calls
- All classes should have corresponding unit tests

## Option Priority

When options can be specified from both command line and JSON files:

- JSON file is highest priority
- Command line is used if JSON doesn't specify
- Otherwise use default value
