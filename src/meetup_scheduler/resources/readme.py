##############################################################################
#
# Name: readme.py
#
# Function:
#       Utilities for reading and extracting sections from README.md
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

import importlib.resources
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console
    from rich.markdown import Markdown


class ReadmeReader:
    """Read and extract sections from the bundled README.md."""

    # Pattern for extracting marked sections
    # Matches: <!-- meetup-scheduler:section-name:start --> content
    #          <!-- meetup-scheduler:section-name:end -->
    SECTION_PATTERN = re.compile(
        r"<!--\s*meetup-scheduler:(\S+):start\s*-->\s*\n(.*?)\n\s*<!--\s*meetup-scheduler:\1:end\s*-->",
        re.DOTALL,
    )

    class Error(Exception):
        """Exception raised for README reading errors."""

        pass

    def __init__(self) -> None:
        """Initialize the README reader."""
        self._content: str | None = None

    def _get_readme_resource(self) -> str:
        """Get the README content from package resources or source directory.

        Tries package resources first (for installed wheel), then falls back
        to source directory (for editable/development install).

        Returns:
            The README.md content as a string.

        Raises:
            Error: If README cannot be loaded from any location.
        """
        # Try package resources first (works for installed wheel)
        try:
            resource = importlib.resources.files("meetup_scheduler.resources").joinpath(
                "README.md"
            )
            return resource.read_text(encoding="utf-8")
        except (FileNotFoundError, TypeError):
            pass

        # Fall back to source directory (for editable/dev install)
        try:
            from pathlib import Path

            import meetup_scheduler

            module_path = Path(meetup_scheduler.__file__).resolve()
            # module_path is .../src/meetup_scheduler/__init__.py
            # README.md is at repo root: .../README.md
            source_root = module_path.parent.parent.parent
            readme_path = source_root / "README.md"
            if readme_path.exists():
                return readme_path.read_text(encoding="utf-8")
        except (AttributeError, OSError):
            pass

        raise self.Error(
            "Could not load README.md from package resources or source directory"
        )

    @property
    def content(self) -> str:
        """Return the full README content, loading if needed."""
        if self._content is None:
            self._content = self._get_readme_resource()
        return self._content

    def get_section(self, section_name: str) -> str | None:
        """Extract a marked section from the README.

        Sections are marked with HTML comments:
            <!-- meetup-scheduler:section-name:start -->
            content here
            <!-- meetup-scheduler:section-name:end -->

        Args:
            section_name: Name of the section to extract (e.g., "oauth-setup").

        Returns:
            The section content (without markers), or None if not found.
        """
        pattern = re.compile(
            rf"<!--\s*meetup-scheduler:{re.escape(section_name)}:start\s*-->\s*\n"
            rf"(.*?)\n\s*<!--\s*meetup-scheduler:{re.escape(section_name)}:end\s*-->",
            re.DOTALL,
        )
        match = pattern.search(self.content)
        if match:
            return match.group(1).strip()
        return None

    def get_all_sections(self) -> dict[str, str]:
        """Extract all marked sections from the README.

        Returns:
            Dictionary mapping section names to their content.
        """
        sections: dict[str, str] = {}
        for match in self.SECTION_PATTERN.finditer(self.content):
            section_name = match.group(1)
            section_content = match.group(2).strip()
            sections[section_name] = section_content
        return sections

    def print_raw(self) -> None:
        """Print the README as raw markdown to stdout."""
        print(self.content)

    def _simple_pager(self, text: str) -> None:
        """A simple cross-platform pager that handles UTF-8 correctly.

        Python's pydoc.pager() on Windows uses backslashreplace encoding
        which converts Unicode characters to \\uXXXX escape sequences.
        This pager avoids that issue by using Python's print() directly.
        """
        import shutil

        # Get terminal size
        try:
            terminal_size = shutil.get_terminal_size()
            lines_per_page = terminal_size.lines - 1  # Leave room for prompt
        except (ValueError, OSError):
            lines_per_page = 24  # Fallback default

        lines = text.splitlines()
        total_lines = len(lines)
        current_line = 0

        while current_line < total_lines:
            # Print a page worth of lines
            page_end = min(current_line + lines_per_page, total_lines)
            for line in lines[current_line:page_end]:
                print(line)

            current_line = page_end

            if current_line < total_lines:
                # More content available - prompt user
                try:
                    response = input("-- More (Enter=next page, q=quit) --")
                    # Clear the prompt line by overwriting with spaces
                    print(f"\r{' ' * 40}\r", end="")
                    if response.lower() == "q":
                        break
                except (KeyboardInterrupt, EOFError):
                    print()
                    break

    def _create_left_justified_markdown(self, content: str) -> Markdown:
        """Create a Markdown object with left-justified headings.

        Rich's default Markdown rendering centers headings, which can look
        odd in terminal output. This method creates a custom Markdown that
        left-justifies all content including headings.

        Args:
            content: The markdown content to render.

        Returns:
            A Markdown object configured for left-justified output.
        """
        from rich import box
        from rich.markdown import Heading, Markdown
        from rich.panel import Panel
        from rich.text import Text

        # Create a custom Heading subclass that left-justifies
        class LeftHeading(Heading):
            """Heading that renders left-justified instead of centered."""

            def __rich_console__(self, console, options):  # type: ignore[no-untyped-def]
                text = self.text
                text.justify = "left"
                if self.tag == "h1":
                    # Draw a border around h1s, but left-align content
                    yield Panel(
                        text,
                        box=box.HEAVY,
                        style="markdown.h1.border",
                    )
                else:
                    if self.tag == "h2":
                        yield Text("")
                    yield text

        # Create markdown and replace heading element type
        md = Markdown(content, justify="left")
        md.elements["heading_open"] = LeftHeading
        return md

    def print_formatted(
        self, console: Console | None = None, *, pager: bool = False
    ) -> None:
        """Print the README with rich markdown formatting.

        Uses left-justified headings for better readability in terminals.

        Args:
            console: Rich Console instance. If None, creates a new one.
            pager: If True, use system pager for long output.
        """
        from io import StringIO

        from rich.console import Console

        md = self._create_left_justified_markdown(self.content)

        if pager:
            # Render to string first, then use our simple pager
            # This avoids encoding issues with system pagers on Windows
            string_io = StringIO()
            render_console = Console(file=string_io, force_terminal=True)
            render_console.print(md)
            output = string_io.getvalue()

            self._simple_pager(output)
        else:
            if console is None:
                console = Console()
            console.print(md)

    def print_section(
        self, section_name: str, *, raw: bool = False, pager: bool = False
    ) -> bool:
        """Print a specific section from the README.

        Uses left-justified headings for better readability in terminals.

        Args:
            section_name: Name of the section to print.
            raw: If True, print as raw markdown. If False, use rich formatting.
            pager: If True, use system pager for long output.

        Returns:
            True if section was found and printed, False otherwise.
        """
        section = self.get_section(section_name)
        if section is None:
            return False

        if raw:
            print(section)
        else:
            from io import StringIO

            from rich.console import Console

            md = self._create_left_justified_markdown(section)

            if pager:
                # Render to string first, then use our simple pager
                # This avoids encoding issues with system pagers on Windows
                string_io = StringIO()
                render_console = Console(file=string_io, force_terminal=True)
                render_console.print(md)
                output = string_io.getvalue()

                self._simple_pager(output)
            else:
                console = Console()
                console.print(md)

        return True
