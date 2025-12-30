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

## File Headers

All source files must have a standard header block. The format varies by file type:

### Python Files

```python
##############################################################################
#
# Name: filename.py
#
# Function:
#       Brief description of the module's purpose
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################
```

### Makefile

```makefile
##############################################################################
#
# File: Makefile
#
# Purpose:
#       Brief description of the makefile's purpose
#
# Copyright notice and license:
#       See LICENSE.md in this directory.
#
# Author:
#       Terry Moore
#
# Notes:
#       Additional notes about compatibility, requirements, etc.
#
##############################################################################
```

### JSON Schema Files

JSON doesn't support comments, so use the `$comment` field or `description`:

```json
{
  "$schema": "...",
  "$comment": "Copyright: See LICENSE.md. Author: Terry Moore",
  "description": "Schema for..."
}
```

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

## Dependency Versioning

In `pyproject.toml`, all dependencies must be constrained to avoid breaking changes:

- **For packages at version 1.0+**: Use pattern `"package>=X.Y, ==X.*"`
  - Example: `"requests>=2.28, ==2.*"`
- **For packages before version 1.0**: Lock to current minor version
  - Example: `"ruff>=0.8.0, ==0.8.*"`

This ensures compatible updates while preventing unexpected major version changes.

## Makefile Conventions

The project uses a GNU Makefile for build automation:

1. **Help target**: `make help` must list all targets, each on a single line
2. **Descriptive comments**: Each target must have a comment block above it
   explaining its purpose
3. **Variable naming**: All project-specific variables must use a common
   project-specific prefix (e.g., `MEETUP_SCHEDULER_` for this project)
4. **Compatibility**: Makefile should work on macOS and Windows (via git bash)

Example help target format (note: Makefiles require hard tabs for indentation):

<!-- markdownlint-save -->
<!-- markdownlint-disable MD010 -->

```makefile
help:
	@printf "%s\n" \
		"Available targets:" \
		"" \
		"* make help      -- prints this message" \
		"* make build     -- builds the app using uv" \
		"* make test      -- runs pytest" \
		"* make clean     -- removes build artifacts"
```

<!-- markdownlint-restore -->

## Option Priority

When options can be specified from both command line and JSON files:

- JSON file is highest priority
- Command line is used if JSON doesn't specify
- Otherwise use default value
