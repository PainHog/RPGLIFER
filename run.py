"""Launcher used both for local development and as the PyInstaller entry point.

Running ``python run.py`` starts the app exactly like the packaged ``.exe`` does.
Keeping the frozen-app entry point as a top-level script (rather than ``-m``)
keeps PyInstaller's module analysis straightforward.
"""

import sys

from rpglifer.app import main

if __name__ == "__main__":
    sys.exit(main())
