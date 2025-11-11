"""
CLI package entry point.

This module allows executing the CLI package with:
  python -m src.interface.cli

It delegates to the main module's main() function.
"""

from .main import main

if __name__ == "__main__":
    main()
