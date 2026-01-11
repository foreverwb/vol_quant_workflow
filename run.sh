#!/bin/bash
# Convenience runner script - 自动检测目录名作为包名
# Usage: ./run.sh cmd AAPL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="$(basename "$SCRIPT_DIR")"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

export PYTHONPATH="$PARENT_DIR${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONWARNINGS="ignore::RuntimeWarning"
cd "$SCRIPT_DIR"

CMD="$1"
shift

case "$CMD" in
    cmd)
        exec python3 -m "${PACKAGE_NAME}.cli.cmd" "$@"
        ;;
    task)
        exec python3 -m "${PACKAGE_NAME}.cli.task" "$@"
        ;;
    updated)
        exec python3 -m "${PACKAGE_NAME}.cli.update" "$@"
        ;;
    test)
        exec python3 -m pytest tests/ -v "$@"
        ;;
    help|--help|-h|"")
        echo "Vol Quant Workflow (Package: $PACKAGE_NAME)"
        echo ""
        echo "Usage: ./run.sh <command> [options]"
        echo ""
        echo "Commands:"
        echo "  cmd     Initialize symbol"
        echo "  task    Full analysis pipeline"
        echo "  updated  Lightweight monitoring update"
        echo "  test    Run tests"
        ;;
    *)
        echo "Unknown command: $CMD"
        exit 1
        ;;
esac
