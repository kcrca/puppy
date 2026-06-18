import argparse
from pathlib import Path

from puppy.hashes import parse_content
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
        '-c',
        '--content',
        dest='content',
        default=None,
        metavar='CATEGORIES',
        help='Content categories to act on: file/f, images/i, data/d, or all '
             '(combine as -c fid or --content file,images). '
             'On push, named categories upload regardless of hash; on pull, '
             'images means download the gallery and icon.',
    )

    parser.add_argument(
        '--rehash',
        action='store_true',
        dest='rehash',
        help='Record current content as already-uploaded: write hashes.yaml for the '
             'in-scope categories (-c, else all) without uploading anything.',
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

    if args.rehash and args.action != 'push':
        parser.error('--rehash is only valid with push')
    if args.rehash and args.dry_run:
        parser.error('--rehash cannot be combined with --dry-run')

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
        content=parse_content(args.content) if args.content else None,
        rehash=args.rehash,
        handle_filter=args.handle_name or None,
        open_browser=args.open_browser,
    )
