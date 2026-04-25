import argparse
from pathlib import Path

from puppy.runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='puppy',
        description='Thin management layer for PackUpdate (pu).',
    )

    parser.add_argument(
        'action',
        nargs='?',
        default='push',
        choices=['push', 'create', 'import', 'init', 'clean'],
        help='Action to perform (default: push).',
    )

    parser.add_argument(
        'pack_name',
        nargs='?',
        default=None,
        metavar='PACK',
        help='Limit action to a specific pack (by pack slug).',
    )

    parser.add_argument(
        '-n',
        '--dry-run',
        action='store_true',
        dest='dry_run',
        help='Run full pipeline and write payloads to debug/ without executing the worker.',
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        '-v',
        action='store_const',
        const=1,
        dest='verbosity',
        default=0,
        help='High-level progress output.',
    )
    verbosity.add_argument(
        '-vv',
        action='store_const',
        const=2,
        dest='verbosity',
        help='Raw worker stdout/stderr.',
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
        help='Limit action to a specific site.',
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
        '-p',
        '--pack',
        action='store_true',
        dest='pack',
        help='Include zip artifact upload in push.',
    )

    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        dest='force',
        help='With push -p, bypass per-site skip checks. With create, skip confirmation prompt.',
    )

    parser.add_argument(
        '-I',
        '--images',
        action='store_true',
        dest='images',
        help='Import image gallery (valid for import).',
    )

    parser.add_argument(
        '--worker',
        type=Path,
        dest='worker',
        default=None,
        metavar='PATH',
        help='PackUploader worker directory (default: ~/PackUploader).',
    )

    return parser


def main(argv: list[str] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.action == 'create' and not args.force:
        answer = input('Create new projects on sites? This cannot be undone. [y/N] ')
        if not answer.strip().lower().startswith('y'):
            raise SystemExit('Aborted.')

    directory = args.directory or Path.cwd()

    run(
        action=args.action,
        directory=directory,
        dry_run=args.dry_run,
        verbosity=args.verbosity,
        site=args.site,
        version=args.version,
        pack=args.pack,
        pack_filter=args.pack_name,
        force=args.force,
        images=args.images,
        worker=args.worker,
    )
