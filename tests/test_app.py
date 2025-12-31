##############################################################################
#
# Name: test_app.py
#
# Function:
#       Unit tests for meetup-scheduler App class and CLI parsing
#
# Copyright notice and license:
#       See LICENSE.md
#
# Author:
#       Terry Moore
#
##############################################################################

from __future__ import annotations

from pathlib import Path

from meetup_scheduler.app import App


class TestAppArgumentParsing:
    """Test CLI argument parsing."""

    def test_no_args_returns_none_command(self) -> None:
        """Test that no arguments results in command=None."""
        app = App(args=[])
        assert app.args.command is None

    def test_verbose_flag_single(self) -> None:
        """Test -v sets verbose to 1."""
        app = App(args=["-v"])
        assert app.args.verbose == 1

    def test_verbose_flag_double(self) -> None:
        """Test -vv sets verbose to 2."""
        app = App(args=["-vv"])
        assert app.args.verbose == 2

    def test_verbose_flag_triple(self) -> None:
        """Test -vvv sets verbose to 3."""
        app = App(args=["-vvv"])
        assert app.args.verbose == 3

    def test_verbose_long_form(self) -> None:
        """Test --verbose sets verbose to 1."""
        app = App(args=["--verbose"])
        assert app.args.verbose == 1

    def test_verbose_long_form_repeated(self) -> None:
        """Test --verbose --verbose sets verbose to 2."""
        app = App(args=["--verbose", "--verbose"])
        assert app.args.verbose == 2

    def test_verbose_default(self) -> None:
        """Test verbose defaults to 0."""
        app = App(args=[])
        assert app.args.verbose == 0

    def test_quiet_flag(self) -> None:
        """Test -q sets quiet to True."""
        app = App(args=["-q"])
        assert app.args.quiet is True

    def test_quiet_long_form(self) -> None:
        """Test --quiet sets quiet to True."""
        app = App(args=["--quiet"])
        assert app.args.quiet is True

    def test_quiet_default(self) -> None:
        """Test quiet defaults to False in production mode."""
        app = App(args=[])
        assert app.args.quiet is False

    def test_quiet_negated(self) -> None:
        """Test --no-quiet explicitly sets quiet to False."""
        # Use _testing=True so default is None, allowing us to verify negation works
        app = App(args=["--no-quiet"], _testing=True)
        assert app.args.quiet is False

    def test_quiet_default_none_in_testing(self) -> None:
        """Test quiet defaults to None in testing mode."""
        app = App(args=[], _testing=True)
        assert app.args.quiet is None

    def test_debug_flag(self) -> None:
        """Test --debug sets debug to True."""
        app = App(args=["--debug"])
        assert app.args.debug is True

    def test_debug_default(self) -> None:
        """Test debug defaults to False in production mode."""
        app = App(args=[])
        assert app.args.debug is False

    def test_debug_negated(self) -> None:
        """Test --no-debug explicitly sets debug to False."""
        # Use _testing=True so default is None, allowing us to verify negation works
        app = App(args=["--no-debug"], _testing=True)
        assert app.args.debug is False

    def test_debug_default_none_in_testing(self) -> None:
        """Test debug defaults to None in testing mode."""
        app = App(args=[], _testing=True)
        assert app.args.debug is None

    def test_config_option(self) -> None:
        """Test --config PATH sets config path."""
        app = App(args=["--config", "/path/to/config.json"])
        assert app.args.config == "/path/to/config.json"

    def test_config_default(self) -> None:
        """Test config defaults to None."""
        app = App(args=[])
        assert app.args.config is None

    def test_dry_run_flag(self) -> None:
        """Test --dry-run sets dry_run to True."""
        app = App(args=["--dry-run"])
        assert app.args.dry_run is True

    def test_dry_run_default(self) -> None:
        """Test dry_run defaults to False in production mode."""
        app = App(args=[])
        assert app.args.dry_run is False

    def test_dry_run_negated(self) -> None:
        """Test --no-dry-run explicitly sets dry_run to False."""
        # Use _testing=True so default is None, allowing us to verify negation works
        app = App(args=["--no-dry-run"], _testing=True)
        assert app.args.dry_run is False

    def test_dry_run_default_none_in_testing(self) -> None:
        """Test dry_run defaults to None in testing mode."""
        app = App(args=[], _testing=True)
        assert app.args.dry_run is None


class TestAppCommands:
    """Test command parsing."""

    def test_init_command(self) -> None:
        """Test init command is parsed."""
        app = App(args=["init"])
        assert app.args.command == "init"

    def test_init_force_option(self) -> None:
        """Test init --force option."""
        app = App(args=["init", "--force"])
        assert app.args.command == "init"
        assert app.args.force is True

    def test_init_force_negated(self) -> None:
        """Test init --no-force option."""
        # Use _testing=True so default is None, allowing us to verify negation works
        app = App(args=["init", "--no-force"], _testing=True)
        assert app.args.command == "init"
        assert app.args.force is False

    def test_init_force_default(self) -> None:
        """Test init --force defaults to False in production mode."""
        app = App(args=["init"])
        assert app.args.force is False

    def test_init_path_argument(self) -> None:
        """Test init accepts path argument."""
        app = App(args=["init", "/some/path"])
        assert app.args.command == "init"
        assert app.args.path == "/some/path"

    def test_init_path_default(self) -> None:
        """Test init path defaults to current directory."""
        app = App(args=["init"])
        assert app.args.path == "."

    def test_init_path_with_force(self) -> None:
        """Test init with both path and --force."""
        app = App(args=["init", "/some/path", "--force"])
        assert app.args.command == "init"
        assert app.args.path == "/some/path"
        assert app.args.force is True

    def test_config_command(self) -> None:
        """Test config command is parsed."""
        app = App(args=["config"])
        assert app.args.command == "config"

    def test_config_command_with_key(self) -> None:
        """Test config command with key argument."""
        app = App(args=["config", "organizer.name"])
        assert app.args.command == "config"
        assert app.args.key == "organizer.name"

    def test_config_command_with_key_value(self) -> None:
        """Test config command with key and value arguments."""
        app = App(args=["config", "organizer.name", "Terry Moore"])
        assert app.args.command == "config"
        assert app.args.key == "organizer.name"
        assert app.args.value == "Terry Moore"

    def test_config_list_option(self) -> None:
        """Test config --list option."""
        app = App(args=["config", "--list"])
        assert app.args.command == "config"
        assert app.args.list is True

    def test_config_list_negated(self) -> None:
        """Test config --no-list option."""
        # Use _testing=True so default is None, allowing us to verify negation works
        app = App(args=["config", "--no-list"], _testing=True)
        assert app.args.command == "config"
        assert app.args.list is False

    def test_config_list_default(self) -> None:
        """Test config --list defaults to False in production mode."""
        app = App(args=["config"])
        assert app.args.list is False

    def test_config_edit_option(self) -> None:
        """Test config --edit option."""
        app = App(args=["config", "--edit"])
        assert app.args.command == "config"
        assert app.args.edit is True

    def test_config_edit_negated(self) -> None:
        """Test config --no-edit option."""
        # Use _testing=True so default is None, allowing us to verify negation works
        app = App(args=["config", "--no-edit"], _testing=True)
        assert app.args.command == "config"
        assert app.args.edit is False

    def test_config_edit_default(self) -> None:
        """Test config --edit defaults to False in production mode."""
        app = App(args=["config"])
        assert app.args.edit is False

    def test_sync_command(self) -> None:
        """Test sync command is parsed."""
        app = App(args=["sync"])
        assert app.args.command == "sync"

    def test_sync_group_option(self) -> None:
        """Test sync --group option."""
        app = App(args=["sync", "--group", "test-group"])
        assert app.args.command == "sync"
        assert app.args.group == "test-group"

    def test_sync_years_option(self) -> None:
        """Test sync --years option."""
        app = App(args=["sync", "--years", "3"])
        assert app.args.command == "sync"
        assert app.args.years == 3

    def test_sync_years_default(self) -> None:
        """Test sync --years defaults to 2."""
        app = App(args=["sync"])
        assert app.args.years == 2

    def test_sync_venues_only_option(self) -> None:
        """Test sync --venues-only option."""
        app = App(args=["sync", "--venues-only"])
        assert app.args.command == "sync"
        assert app.args.venues_only is True

    def test_sync_venues_only_negated(self) -> None:
        """Test sync --no-venues-only option."""
        # Use _testing=True so default is None, allowing us to verify negation works
        app = App(args=["sync", "--no-venues-only"], _testing=True)
        assert app.args.command == "sync"
        assert app.args.venues_only is False

    def test_sync_venues_only_default(self) -> None:
        """Test venues_only defaults to False in production mode."""
        app = App(args=["sync"])
        assert app.args.venues_only is False

    def test_sync_venues_only_default_none_in_testing(self) -> None:
        """Test venues_only defaults to None in testing mode."""
        app = App(args=["sync"], _testing=True)
        assert app.args.venues_only is None

    def test_schedule_command(self) -> None:
        """Test schedule command is parsed."""
        app = App(args=["schedule"])
        assert app.args.command == "schedule"

    def test_schedule_with_file(self) -> None:
        """Test schedule command with file argument."""
        app = App(args=["schedule", "events.json"])
        assert app.args.command == "schedule"
        assert app.args.file == "events.json"

    def test_schedule_output_option(self) -> None:
        """Test schedule --output option."""
        app = App(args=["schedule", "--output", "markdown"])
        assert app.args.command == "schedule"
        assert app.args.output == "markdown"

    def test_schedule_output_default(self) -> None:
        """Test schedule --output defaults to summary."""
        app = App(args=["schedule"])
        assert app.args.output == "summary"

    def test_schedule_on_conflict_option(self) -> None:
        """Test schedule --on-conflict option."""
        app = App(args=["schedule", "--on-conflict", "skip"])
        assert app.args.command == "schedule"
        assert app.args.on_conflict == "skip"

    def test_schedule_on_conflict_default(self) -> None:
        """Test schedule --on-conflict defaults to prompt."""
        app = App(args=["schedule"])
        assert app.args.on_conflict == "prompt"

    def test_schedule_series_mode_option(self) -> None:
        """Test schedule --series-mode option."""
        app = App(args=["schedule", "--series-mode", "link"])
        assert app.args.command == "schedule"
        assert app.args.series_mode == "link"

    def test_schedule_series_mode_default(self) -> None:
        """Test schedule --series-mode defaults to independent."""
        app = App(args=["schedule"])
        assert app.args.series_mode == "independent"

    def test_generate_command(self) -> None:
        """Test generate command is parsed."""
        app = App(args=["generate"])
        assert app.args.command == "generate"

    def test_generate_group_option(self) -> None:
        """Test generate --group option."""
        app = App(args=["generate", "--group", "test-group"])
        assert app.args.command == "generate"
        assert app.args.group == "test-group"

    def test_generate_pattern_option(self) -> None:
        """Test generate --pattern option."""
        app = App(args=["generate", "--pattern", "first Thursday"])
        assert app.args.command == "generate"
        assert app.args.pattern == "first Thursday"

    def test_generate_count_option(self) -> None:
        """Test generate --count option."""
        app = App(args=["generate", "--count", "6"])
        assert app.args.command == "generate"
        assert app.args.count == 6

    def test_generate_count_default(self) -> None:
        """Test generate --count defaults to 12."""
        app = App(args=["generate"])
        assert app.args.count == 12


class TestAppGlobalOptionsWithCommands:
    """Test global options work with commands."""

    def test_global_options_before_command(self) -> None:
        """Test global options work before command."""
        app = App(args=["-v", "--debug", "init"])
        assert app.args.verbose == 1
        assert app.args.debug is True
        assert app.args.command == "init"

    def test_multiple_global_options(self) -> None:
        """Test multiple global options together."""
        app = App(args=["-vv", "--dry-run", "--config", "/tmp/cfg.json", "sync"])
        assert app.args.verbose == 2
        assert app.args.dry_run is True
        assert app.args.config == "/tmp/cfg.json"
        assert app.args.command == "sync"

    def test_all_global_options(self) -> None:
        """Test all global options at once."""
        app = App(
            args=[
                "-vvv",
                "-q",
                "--debug",
                "--config",
                "/path/to/config",
                "--dry-run",
                "schedule",
            ]
        )
        assert app.args.verbose == 3
        assert app.args.quiet is True
        assert app.args.debug is True
        assert app.args.config == "/path/to/config"
        assert app.args.dry_run is True
        assert app.args.command == "schedule"


class TestAppRun:
    """Test App.run() behavior."""

    def test_no_command_returns_zero(self) -> None:
        """Test that no command prints help and returns 0."""
        app = App(args=[])
        assert app.run() == 0

    def test_config_command_returns_zero(self) -> None:
        """Test that config command returns 0."""
        app = App(args=["config"])
        assert app.run() == 0

    def test_init_command_with_path_returns_zero(self, tmp_path: Path) -> None:
        """Test that init command returns 0 with valid path."""
        target = tmp_path / "test-project"
        app = App(args=["init", str(target)])
        assert app.run() == 0
