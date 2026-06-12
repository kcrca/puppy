import argparse
from pathlib import Path

from puppy.runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='puppy',
        description='Manage one or more Minecraft projects on multiple sites',
    )

    parser.add_argument(
        'action',
        nargs='?',
        default='push',
        choices=['push', 'pull', 'init', 'auth', 'create'],
        help='Action to perform (default: push).',
    )

    parser.add_argument(
        'handle_name',
        nargs='*',
        metavar='project',
        help='Limit action to one or more projects (by handle).',
    )

    parser.add_argument(
        '-n',
        '--dry-run',
        action='store_true',
        dest='dry_run',
        help='Run full pipeline without hitting APIs; write preview to temp dir.',
    )

    parser.add_argument(
        '-q',
        '--quiet',
        action='store_const',
        const=0,
        dest='verbosity',
        default=1,
        help='Suppress progress output.',
    )

    parser.add_argument(
        '-d',
        '--dir',
        type=Path,
        dest='directory',
        default=None,
        metavar='PATH',
        help='Project directory (default: current working directory).',
    )

    parser.add_argument(
        '-s',
        '--site',
        dest='site',
        default=None,
        metavar='SITENAME',
        help='Limit action to one or more sites (comma-separated, such as cf,mr).',
    )

    parser.add_argument(
        '-V',
        '--version',
        dest='version',
        default=None,
        metavar='STRING',
        help='Version string override; falls back to version: in puppy.yaml.',
    )

    parser.add_argument(
        '-F',
        '--file',
        action='store_true',
        dest='upload_file',
        help='Include artifact file upload in push.',
    )

    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        dest='force',
        help='With push -F, bypass per-site skip checks. With create, skip confirmation prompt.',
    )

    parser.add_argument(
        '-I',
        '--images',
        action='store_true',
        dest='images',
        help='Include image gallery. For pull: download from site. For push: include in upload.',
    )

    parser.add_argument(
        '--no-open',
        action='store_false',
        dest='open_browser',
        default=True,
        help='Do not open the dry-run preview in a browser.',
    )

    return parser


def main(argv: list[str] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    directory = args.directory or Path.cwd()

    if args.action == 'auth':
        from puppy.auth import run_auth
        run_auth(site=args.site, directory=directory)
        return

    run(
        action=args.action,
        directory=directory,
        dry_run=args.dry_run,
        verbosity=args.verbosity,
        site=args.site,
        version=args.version,
        upload_file=args.upload_file,
        handle_filter=args.handle_name or None,
        force=args.force,
        images=args.images,
        open_browser=args.open_browser,
    )
