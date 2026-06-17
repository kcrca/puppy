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
        if s is CURSEFORGE:
            avatar = s.upload_icon(site_id, auth, prepare_icon(icon, verbosity=verbosity))
        elif s is MODRINTH:
            s.upload_icon(site_id, auth, prepare_icon(icon, verbosity=verbosity))
        if image_list:
            if s is PMC:
                urls = s.upload_images(site_id, auth, image_list, images_dir, verbosity, project_type)
            else:
                urls = s.upload_images(site_id, auth, image_list, images_dir, verbosity)
        else:
            urls = {}
        if use_hashes:
            site_store['images'] = img_fp
    else:
        if verbosity >= 1 and image_list:
            print(f'  [{s.label}] gallery unchanged, skipping')
        if image_list:
            urls = s.gallery_urls(site_id, auth, project_type) if s is PMC else s.gallery_urls(site_id, auth)
        else:
            urls = {}
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

    cf_avatar = None
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
        if s is CURSEFORGE and avatar is not None:
            cf_avatar = avatar
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
        if s is MODRINTH:
            server_hash = s.latest_file_sha(site_id, auth)
            recorded = site_store.get('file')
            if server_hash and recorded and server_hash != recorded:
                print(f'  [Modrinth] file on site differs from last push — updating {hashes.HASH_FILE}')
                site_store['file'] = server_hash
            return server_hash != local_sha
        return site_store.get('file') != local_sha

    def _cf_task():
        site_store = store.setdefault('curseforge', {})
        desc = descriptions.get('curseforge', '')
        sc = {'name': config.get('name', ''), 'summary': config.get('summary', ''), **config.get('curseforge', {})}
        if hashes.decide('data', _data_fingerprint(desc, sc, config), upload_set=content, use_hashes=use_hashes, prior=site_store):
            _run_cf(project, config, cf_avatar, desc, auth, verbosity)
            if use_hashes:
                site_store['data'] = _data_fingerprint(desc, sc, config)
        elif verbosity >= 1:
            print('  [CurseForge] data unchanged, skipping')
        if _site_file_should(CURSEFORGE, cf_id):
            _upload_cf(cf_id, auth, zip_path, version, config, puppy_dir, verbosity)
            if use_hashes:
                site_store['file'] = local_sha

    def _mr_task():
        site_store = store.setdefault('modrinth', {})
        desc = descriptions.get('modrinth', '')
        sc = {'name': config.get('name', ''), 'summary': config.get('summary', ''), **config.get('modrinth', {})}
        if hashes.decide('data', _data_fingerprint(desc, sc, config), upload_set=content, use_hashes=use_hashes, prior=site_store):
            _run_mr(project, config, desc, auth, verbosity)
            if use_hashes:
                site_store['data'] = _data_fingerprint(desc, sc, config)
        elif verbosity >= 1:
            print('  [Modrinth] data unchanged, skipping')
        if _site_file_should(MODRINTH, mr_id):
            _upload_mr(mr_id, auth, zip_path, version, config, puppy_dir, verbosity)
            if use_hashes:
                site_store['file'] = local_sha

    def _pmc_task():
        site_store = store.setdefault('planetminecraft', {})
        desc = descriptions.get('planetminecraft', '')
        sc = {'name': config.get('name', ''), 'summary': config.get('summary', ''), **config.get('planetminecraft', {})}
        if hashes.decide('data', _data_fingerprint(desc, sc, config), upload_set=content, use_hashes=use_hashes, prior=site_store):
            _run_pmc(project, config, desc, auth, verbosity)
            if use_hashes:
                site_store['data'] = _data_fingerprint(desc, sc, config)
        elif verbosity >= 1:
            print('  [PlanetMinecraft] data unchanged, skipping')
        if _site_file_should(PMC, pmc_id):
            _upload_pmc(pmc_id, auth, zip_path, version, config, puppy_dir, verbosity)
            if use_hashes:
                site_store['file'] = local_sha

    tasks = []
    if CURSEFORGE in visitor and cf_id:
        tasks.append((CURSEFORGE.label, _cf_task))
    if MODRINTH in visitor and mr_id:
        tasks.append((MODRINTH.label, _mr_task))
    if PMC in visitor and pmc_id:
        tasks.append((PMC.label, _pmc_task))

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


def _run_cf(project, config, avatar_url, description, auth, verbosity):
    project_id = config.get('curseforge', {}).get('id')
    try:
        CURSEFORGE.push(
            project_id=project_id,
            config=config,
            description=description,
            avatar_url=avatar_url,
            auth=auth,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'CurseForge auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site cf')
    except SiteError as e:
        raise SystemExit(f'CurseForge error: {e}')


def _upload_cf(project_id, auth, zip_path, version, config, puppy_dir, verbosity):
    try:
        if verbosity >= 1:
            print(f'  [CurseForge] uploading version {version}')
        CURSEFORGE.upload_file(project_id, auth, zip_path, version, config)
        CURSEFORGE.post_upload(puppy_dir, version)
    except AuthExpiredError as e:
        raise SystemExit(f'CurseForge auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site cf')
    except SiteError as e:
        raise SystemExit(f'CurseForge error: {e}')


def _run_mr(project, config, description, auth, verbosity):
    mr = config.get('modrinth', {})
    project_id = mr.get('id') or mr.get('slug')
    try:
        MODRINTH.push(
            project_id=project_id,
            config=config,
            description=description,
            auth=auth,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'Modrinth auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site modrinth')
    except SiteError as e:
        raise SystemExit(f'Modrinth error: {e}')


def _upload_mr(project_id, auth, zip_path, version, config, puppy_dir, verbosity):
    try:
        if verbosity >= 1:
            print(f'  [Modrinth] uploading version {version}')
        MODRINTH.upload_version(project_id, auth, zip_path, version, config)
        MODRINTH.post_upload(puppy_dir, version)
    except AuthExpiredError as e:
        raise SystemExit(f'Modrinth auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site modrinth')
    except SiteError as e:
        raise SystemExit(f'Modrinth error: {e}')


def _run_pmc(project, config, description, auth, verbosity):
    pmc = config.get('planetminecraft', {})
    project_id = pmc.get('id')
    try:
        PMC.push(
            project_id=project_id,
            config=config,
            description=description,
            auth=auth,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'PlanetMinecraft auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site pmc')
    except SiteError as e:
        raise SystemExit(f'PlanetMinecraft error: {e}')


def _upload_pmc(project_id, auth, zip_path, version, config, puppy_dir, verbosity):
    try:
        if verbosity >= 1:
            print(f'  [PlanetMinecraft] submitting version log {version}')
        PMC.submit_log(project_id, auth, version, config)
        PMC.post_upload(puppy_dir, version)
    except AuthExpiredError as e:
        raise SystemExit(f'PlanetMinecraft auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site pmc')
    except SiteError as e:
        raise SystemExit(f'PlanetMinecraft error: {e}')
