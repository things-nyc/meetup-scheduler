##############################################################################
#
# File: Makefile
#
# Purpose:
#       Build automation for meetup-scheduler
#
# Copyright notice and license:
#       See LICENSE.md in this directory.
#
# Author:
#       Terry Moore
#
# Notes:
#       Requires GNU Make. Works on macOS, Linux, and Windows (via git bash).
#
##############################################################################

# Project-specific prefix for all variables
MEETUP_SCHEDULER_PYTHON := python
MEETUP_SCHEDULER_UV := uv

.PHONY: help build test lint clean distclean

##############################################################################
#
# help: Display available make targets
#
##############################################################################
help:
	@printf "%s\n" \
		"Available targets:" \
		"" \
		"* make help      -- prints this message" \
		"* make build     -- builds the package using uv" \
		"* make test      -- runs pytest" \
		"* make lint      -- runs ruff linting" \
		"* make clean     -- removes build artifacts" \
		"* make distclean -- clean, plus removes dist/"

##############################################################################
#
# build: Build the package using uv
#
##############################################################################
build:
	$(MEETUP_SCHEDULER_UV) build

##############################################################################
#
# test: Run pytest test suite
#
##############################################################################
test:
	$(MEETUP_SCHEDULER_UV) run pytest

##############################################################################
#
# lint: Run ruff linting on source and test files
#
##############################################################################
lint:
	$(MEETUP_SCHEDULER_UV) run ruff check src/ tests/

##############################################################################
#
# clean: Remove build artifacts
#
##############################################################################
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

##############################################################################
#
# distclean: Clean plus remove dist directory
#
##############################################################################
distclean: clean
	rm -rf dist/
