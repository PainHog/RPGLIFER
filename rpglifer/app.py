"""Application entry point: parse arguments, load the save, launch a front-end.

The GUI is preferred, but if Tkinter isn't importable (some minimal Python
builds) or the user passes ``--cli``, we fall back to the console front-end so
the app is never dead in the water.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import __app_name__, __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rpglifer",
        description=f"{__app_name__} — turn daily activities into a leveling RPG character.",
    )
    parser.add_argument("--cli", action="store_true",
                        help="run the text-mode interface instead of the GUI")
    parser.add_argument("--data-dir", metavar="PATH",
                        help="override where the save file lives")
    parser.add_argument("--version", action="version",
                        version=f"{__app_name__} {__version__}")
    return parser


def _gui_available() -> bool:
    try:
        import tkinter  # noqa: F401
    except Exception:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.data_dir:
        os.environ["RPGLIFER_DATA_DIR"] = args.data_dir

    # Imported lazily so that --version / --help work even if a front-end's
    # dependencies are unhappy.
    from . import storage

    character = storage.load()

    if args.cli or not _gui_available():
        if not args.cli:
            print("(Tkinter unavailable — falling back to the text interface.)")
        from . import cli
        return cli.run(character)

    try:
        from . import ui_tk
        return ui_tk.run(character)
    except Exception as exc:  # pragma: no cover - last-resort safety net
        print(f"GUI failed to start ({exc}). Falling back to the text interface.")
        from . import cli
        return cli.run(character)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
