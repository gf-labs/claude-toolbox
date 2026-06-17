#!/bin/bash
# Wrapper to launch the MCP server using the venv Python.
# Using a shell script prevents Claude Code from resolving the venv symlink
# to the macOS framework binary, which loses the venv's site-packages context.
exec "$(dirname "$0")/.venv/bin/python3" "$(dirname "$0")/server.py" "$@"
