import hashlib
import json
from pathlib import Path

import yaml

from puppy import hashes
from puppy.config import ConfigSynthesizer, _deep_merge, build_projects_context
from puppy.core import Project
from puppy.creator import (
    _find_icon,
    _resolve_asset,
    _validate_square,
)
from puppy.errors import AuthExpiredError, SiteError
from puppy.images import find_image, prepare_icon
from puppy.parallel import run_sites_parallel
from puppy.publisher import _resolve_zip
from puppy.renderer import render
from puppy.searcher import ContentDiscovery
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SITES, SiteVisitor


def add_image_name_aliases(image_urls: dict, image_list: list) -> dict:
    result = dict(image_urls)
    for entry in image_list:
        name = entry.get('name', '')
        file_stem = Path(entry.get('file', '')).stem
        if name and file_stem in result:
            for alias in (name, name.lower()):
                if alias and alias not in result:
                    result[alias] = result[file_stem]
    return result


def apply_env_sides(config: dict) -> dict:
    from puppy.project_type import PROJECT_TYPES, PACK
    pt = PROJECT_TYPES.get(config.get('type', 'pack'), PACK)
    return pt.warn_inapplicable(config)


def _images_fingerprint(icon: Path, image_list: list, images_dir: Path) -> str:
    h = hashlib.sha512()
    if icon and icon.exists():
        h.update(icon.read_bytes())
    for entry in image_list:
        try:
            src = find_image(entry['file'], images_dir)
        except SystemExit:
            continue
        h.update(b'\x00')
        h.update(src.read_bytes())
        h.update(json.dumps(
            {k: entry.get(k) for k in ('name', 'description', 'featured')},
            sort_keys=True, default=str,
        ).encode('utf-8'))
    return h.hexdigest()


def _data_fingerprint(description: str, sc: dict, config: dict) -> str:
    subset = {k: config.get(k) for k in (
        'links', 'license', 'type', 'client_side', 'server_side', 'video', 'optifine',
    )}
    return hashes.data_hash(description, sc, subset)


def _push_images(s, site_id, auth, image_list, images_dir, icon, img_fp,
                 content, use_hashes, site_store, project_type, verbosity):
    """Sync one site's icon + gallery (or fetch existing URLs when unchanged).

    Returns (image_urls, avatar_url). avatar_url is set only for CurseForge
    when the icon was uploaded this run, else None.
    """
    do_images = hashes.decide('images', img_fp, upload_set=content, use_hashes=use_hashes, prior=site_store)
    avatar = None
    if do_images:
        avatar = s.upload_icon(site_id, auth, prepare_icon(icon, verbosity=verbosity))
        urls = s.upload_images(site_id, auth, image_list, images_dir, verbosity, project_type) if image_list else {}
        if use_hashes:
            site_store['images'] = img_fp
    else:
        if verbosity >= 1 and image_list:
            print(f'  [{s.label}] gallery unchanged, skipping')
        urls = s.gallery_urls(site_id, auth, project_type) if image_list else {}
    return urls, avatar


def run_push(
    *,
    project: Project,
    config: dict,
    puppy_home: Path,
    site: str | None,
    version: str | None,
    content: set[str] | None = None,
    verbosity: int,
    auth: dict = None,
    all_labels: list[str] | None = None,
) -> None:
    content = content or set()
    config = dict(config)
    config['projects'] = build_projects_context(puppy_home)
    config = apply_env_sides(config)

    use_hashes = config.get('use_hashes', True)
    puppy_dir = project.puppy_dir
    store = hashes.load(puppy_dir)

    icon = _resolve_asset(config.get('icon'), puppy_dir, _find_icon, config)
    _validate_square(icon)

    if auth is None:
        auth = _load_auth(puppy_home)
    project_type = config.get('type', 'pack')
    visitor = SiteVisitor(site, project_type=project_type)
    if verbosity >= 1 and not site:
        for s in SITES:
            if s not in visitor:
                print(f'  [{s.label}] skipping — type "{project_type}" not supported')

    cf_token = auth.get('curseforge', {}).get('token')
    cf_id = config.get('curseforge', {}).get('id')
    mr_token = auth.get('modrinth', {}).get('token', '')
    mr = config.get('modrinth', {})
    mr_id = mr.get('id') or mr.get('slug')
    pmc_cookie = auth.get('planetminecraft', '')
    pmc_id = config.get('planetminecraft', {}).get('id')

    missing = []
    if CURSEFORGE in visitor and cf_id and not cf_token:
        missing.append(CURSEFORGE)
    if MODRINTH in visitor and mr_id and not mr_token:
        missing.append(MODRINTH)
    if PMC in visitor and pmc_id and not pmc_cookie:
        missing.append(PMC)
    if missing:
        raise SystemExit(f'Credentials missing for: {", ".join(s.label for s in missing)} — run: puppy auth')

    images_source = config.get('images_source')
    images_dir = Path(images_source) if images_source else puppy_dir / 'images'
    image_list = config.get('images', [])
    img_fp = _images_fingerprint(icon, image_list, images_dir)

    avatars: dict[str, str | None] = {}
    image_urls_by_site: dict[str, dict[str, str]] = {}

    # Phase 1: images (icon + gallery) must happen before descriptions render,
    # because descriptions reference image CDN URLs.
    for s, site_id in ((CURSEFORGE, cf_id), (MODRINTH, mr_id), (PMC, pmc_id)):
        if s not in visitor or not site_id:
            continue
        site_store = store.setdefault(s.name, {})
        try:
            urls, avatar = _push_images(
                s, site_id, auth, image_list, images_dir, icon, img_fp,
                content, use_hashes, site_store, project_type, verbosity,
            )
        except AuthExpiredError as e:
            if use_hashes:
                hashes.save(puppy_dir, store)
            raise SystemExit(f'{s.label} auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth')
        except SiteError as e:
            if use_hashes:
                hashes.save(puppy_dir, store)
            raise SystemExit(f'{s.label} error: {e}')
        avatars[s.name] = avatar
        if urls:
            image_urls_by_site[s.name] = add_image_name_aliases(urls, image_list)

    # Phase 2: render descriptions (central, all sites).
    discovery = ContentDiscovery(puppy_home, project.root)
    descriptions: dict[str, str] = {}
    for s in SiteVisitor(site, project_type=project_type):
        site_config = ConfigSynthesizer(puppy_home, project.root, site=s).get_running_config()
        site_config['projects'] = config['projects']
        if s.name in site_config:
            config = _deep_merge(config, {s.name: site_config[s.name]})
        body, source = discovery.find_description(site=s)
        if body:
            rendered = render(body, site_config, source=str(source), site=s,
                              image_urls=image_urls_by_site.get(s.name))
            if source and source.suffix == '.md':
                rendered = s.convert_md(rendered)
            descriptions[s.name] = rendered

    config = dict(config)
    config['description'] = []

    # Phase 3: file change detection (per site).
    zip_path, local_sha = _resolve_file(config, puppy_dir, version, project, content, use_hashes)

    def _site_file_should(s, site_id) -> bool:
        if not zip_path:
            return False
        site_store = store.setdefault(s.name, {})
        forced = 'file' in content
        if not use_hashes:
            return forced
        if forced:
            return True
        return s.file_changed(site_id, auth, local_sha, site_store, hashes.HASH_FILE)

    def _make_task(s, site_id):
        def task():
            site_store = store.setdefault(s.name, {})
            desc = descriptions.get(s.name, '')
            sc = {'name': config.get('name', ''), 'summary': config.get('summary', ''), **config.get(s.name, {})}
            fp = _data_fingerprint(desc, sc, config)
            if hashes.decide('data', fp, upload_set=content, use_hashes=use_hashes, prior=site_store):
                _run_site(s, site_id, config, avatars.get(s.name), desc, auth, verbosity)
                if use_hashes:
                    site_store['data'] = fp
            elif verbosity >= 1:
                print(f'  [{s.label}] data unchanged, skipping')
            if _site_file_should(s, site_id):
                _upload_site(s, site_id, auth, zip_path, version, config, puppy_dir, verbosity)
                if use_hashes:
                    site_store['file'] = local_sha
        return task

    tasks = [
        (s.label, _make_task(s, site_id))
        for s, site_id in ((CURSEFORGE, cf_id), (MODRINTH, mr_id), (PMC, pmc_id))
        if s in visitor and site_id
    ]

    try:
        run_sites_parallel(tasks, all_labels=all_labels, verbosity=verbosity)
    finally:
        if use_hashes:
            hashes.save(puppy_dir, store)

    if verbosity >= 1:
        print(f'[{project.name}] push complete')


def _resolve_file(config, puppy_dir, version, project, content, use_hashes):
    """Resolve the zip and its SHA-512 if file upload is in scope, else (None, None)."""
    file_explicit = 'file' in content
    if not (file_explicit or use_hashes):
        return None, None
    has_spec = bool(config.get('minecraft') or config.get('versions')) and bool(version)
    if not has_spec:
        if file_explicit:
            raise SystemExit(
                f"[{project.name}] push -c file requires 'minecraft:' or 'versions:' "
                f"and a version in puppy.yaml"
            )
        return None, None
    zip_path = _resolve_zip(config, puppy_dir, version, project)
    return zip_path, hashlib.sha512(zip_path.read_bytes()).hexdigest()


def _load_auth(puppy_dir: Path) -> dict:
    auth_path = puppy_dir / 'auth.yaml'
    if not auth_path.exists():
        return {}
    try:
        return yaml.safe_load(auth_path.read_text()) or {}
    except yaml.YAMLError as e:
        raise SystemExit(f'{auth_path}: {e}')


def _site_error(s, e) -> SystemExit:
    if isinstance(e, AuthExpiredError):
        return SystemExit(f'{s.label} auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site {s.auth_arg}')
    return SystemExit(f'{s.label} error: {e}')


def _run_site(s, project_id, config, avatar_url, description, auth, verbosity):
    try:
        s.push(
            project_id=project_id,
            config=config,
            description=description,
            avatar_url=avatar_url,
            auth=auth,
            verbosity=verbosity,
        )
    except (AuthExpiredError, SiteError) as e:
        raise _site_error(s, e)


def _upload_site(s, project_id, auth, zip_path, version, config, puppy_dir, verbosity):
    try:
        s.upload_artifact(project_id, auth, zip_path, version, config, puppy_dir, verbosity)
    except (AuthExpiredError, SiteError) as e:
        raise _site_error(s, e)
