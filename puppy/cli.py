import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="puppy",
        description="Thin management layer for PackUpdate (pu).",
    )

    parser.add_argument(
        "action",
        nargs="?",
        default="sync",
        choices=["sync", "publish", "create", "import"],
        help="Action to perform (default: sync).",
    )

    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Run full pipeline and write payloads to debug/ without executing the worker.",
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v",
        action="store_const", const=1, dest="verbosity", default=0,
        help="High-level progress output.",
    )
    verbosity.add_argument(
        "-vv",
        action="store_const", const=2, dest="verbosity",
        help="Raw worker stdout/stderr.",
    )

    parser.add_argument(
        "-d", "--dir",
        type=Path,
        dest="directory",
        default=None,
        metavar="PATH",
        help="Project directory (default: current working directory).",
    )

    parser.add_argument(
        "-s", "--site",
        dest="site",
        default=None,
        metavar="SITENAME",
        help="Limit action to a specific site.",
    )

    parser.add_argument(
        "-V", "--version",
        dest="version",
        default=None,
        metavar="STRING",
        help="Version string for publish; falls back to version: in puppy.yaml.",
    )

    parser.add_argument(
        "--create",
        action="store_true",
        dest="create",
        help="Required flag to enable the create action.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.action == "create" and not args.create:
        parser.error("create action requires --create flag")

    directory = args.directory or Path.cwd()

    from puppy.runner import run
    run(
        action=args.action,
        directory=directory,
        dry_run=args.dry_run,
        verbosity=args.verbosity,
        site=args.site,
        version=args.version,
    )


if __name__ == "__main__":
    main()
