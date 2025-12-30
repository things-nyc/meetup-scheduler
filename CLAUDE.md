<!-- markdownlint-disable MD013 -->

# Project Guidelines for Claude

## Markdown Files

All markdown files must pass `markdownlint` cleanly:

1. Run `npx markdownlint <file.md>` before considering any markdown file complete
2. Ask for user approval before adding markdownlint disable annotations
3. When using local markdownlint annotations, use the save/restore pattern
   with HTML comments: `markdownlint-save`, then `markdownlint-disable MDXXX`,
   then content, then `markdownlint-restore`. Each directive goes in its own
   HTML comment (e.g., `<` + `!-- markdownlint-save --` + `>`).

4. Common rules to be aware of:
   - MD013: Line length (often disabled at file level)
   - MD029: Ordered list prefix (disable locally if continuous numbering intentional)
   - MD060: Table column spacing (use spaces around separator dashes)
   - MD022/MD032: Blank lines around headings and lists

5. When documenting tool directives as examples, quote or break up the directive
   syntax to prevent tools from interpreting example text as actual directives.
   For example, write `<` + `!-- directive --` + `>` instead of the literal
   HTML comment syntax.

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
- All command-line options must have unit tests that verify:
  - Each option is correctly parsed into the expected namespace attribute
  - Default values are applied when options are not specified
  - Option combinations and conflicts behave as expected

## Command-Line Argument Parsing

- Boolean command-line options must use `action=argparse.BooleanOptionalAction`
  to allow explicit negation (e.g., `--debug` and `--no-debug`)
- Boolean options must specify `default=False` for production use
- This enables users to override defaults or config file settings explicitly
- Example: `parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)`
- For unit testing negation, a `_testing=True` parameter can set defaults to None
  to distinguish "not specified" from "explicitly set to False"
- Unit tests should verify both the positive and negated forms work correctly

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
5. **Required targets**:
   - `clean`: Remove build artifacts (`__pycache__`, `.pytest_cache`, `*.egg-info`, etc.)
   - `distclean`: Run `clean`, then also remove `dist/` directory and its contents

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
		"* make clean     -- removes build artifacts" \
		"* make distclean -- clean, plus removes dist/"
```

<!-- markdownlint-restore -->

## Environment Variable Naming

All project-specific environment variables must use a common project-specific
prefix to avoid conflicts with other tools:

- **Prefix pattern**: `PROJECTNAME_` in uppercase with underscores
- **Example for meetup-scheduler**:
  - `MEETUP_SCHEDULER_ACCESS_TOKEN` (not `MEETUP_ACCESS_TOKEN`)
  - `MEETUP_SCHEDULER_TOKEN_FILE` (not `MEETUP_TOKEN_FILE`)
  - `MEETUP_SCHEDULER_DEBUG` (not `DEBUG`)

This naming convention:

1. Prevents collisions with environment variables from other tools
2. Makes it clear which application owns the variable
3. Aligns with the Makefile variable prefix convention

## GitHub Repository Standards

For projects hosted on GitHub:

### GitHub Actions

Set up CI workflows in `.github/workflows/` for pre-commit checks:

- **Python linting**: Run `ruff check` on all Python files
- **Markdown linting**: Run `markdownlint` on all `.md` files
- **Unit tests**: Run `pytest` with coverage reporting
- **Type checking**: Run `mypy` (if configured)

Workflows should trigger on:

- Push to `main` branch
- Pull requests targeting `main`

### Issue Tracking and Contributions

- Enable GitHub Issues for bug reports and feature requests
- Include a `CONTRIBUTING.md` with guidelines:
  - How to report bugs
  - How to suggest features
  - Pull request process (fork, branch, PR)
  - Code style requirements (reference CLAUDE.md or project docs)
  - Requirement to pass CI checks before merge

## README Structure

The README.md should be user-oriented (not implementation details) and end with
a `## Meta` section (colophon) containing:

- **Contributors**: List of contributors to the project
- **Support link**: Link to [thethings.nyc](https://thethings.nyc)
- **Support message**: "If you find this helpful, please support The Things
  Network New York by joining, participating, or donating."

Example:

```markdown
## Meta

### Contributors

- [Terry Moore](https://github.com/terrillmoore)

### Support

This project is maintained by [The Things Network New York](https://thethings.nyc).

If you find this helpful, please support The Things Network New York by
joining, participating, or donating.
```

## Project URL Synchronization

The project homepage URL is defined once in `pyproject.toml` under `[project.urls]`
and must be kept in sync across all documentation:

- **Source of truth**: `pyproject.toml` `[project.urls]` section
- **Runtime access**: Use `meetup_scheduler.metadata.get_homepage_url()` to get
  the URL at runtime (e.g., for CLI help text)
- **README.md**: Must match the URL in `pyproject.toml` wherever it appears
  (Installation section, OAuth Setup Application Website, etc.)

When updating the project URL:

1. Update `pyproject.toml` `[project.urls]` first
2. Search README.md for any hardcoded URLs and update them
3. Verify `meetup-scheduler --help` shows the correct URL in the epilog

## Option Priority

When options can be specified from both command line and JSON files:

- JSON file is highest priority
- Command line is used if JSON doesn't specify
- Otherwise use default value
