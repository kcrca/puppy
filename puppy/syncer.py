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
from puppy.sites import SITES, SiteVisitor


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


def _image_hash(src: Path, entry: dict) -> str:
    meta = json.dumps(
        {k: entry.get(k) for k in ('name', 'description', 'featured')},
        sort_keys=True, default=str,
    )
    return hashes.compute(src.read_bytes() + b'\x00' + meta.encode('utf-8'))


def _data_fingerprint(description: str, sc: dict, config: dict) -> str:
    subset = {k: config.get(k) for k in (
        'links', 'license', 'type', 'client_side', 'server_side', 'video', 'optifine',
    )}
    return hashes.data_hash(description, sc, subset)


_ICON_KEY = '@icon'


def _local_image_hashes(image_list: list, images_dir: Path, icon) -> dict[str, str]:
    """Per-asset image hashes (icon + each gallery image) computed from local files."""
    result: dict[str, str] = {}
    if icon and icon.exists():
        result[_ICON_KEY] = hashes.compute(icon.read_bytes())
    for entry in image_list:
        try:
            src = find_image(entry['file'], images_dir)
        except SystemExit:
            continue
        result[src.stem] = _image_hash(src, entry)
    return result


def _push_images(s, site_id, auth, image_list, images_dir, icon,
                 content, use_hashes, site_store, project_type, verbosity):
    """Sync one site's icon + gallery per asset.

    The icon and each gallery image are hashed individually (stored under
    site_store['images'] as {'@icon': h, '<stem>': h, ...}); only assets whose
    hash changed are re-uploaded. Returns (image_urls, avatar_url); avatar_url is
    set only when CurseForge re-uploaded the icon this run.
    """
    forced = 'images' in content
    if not use_hashes and not forced:
        # images category not selected → leave the gallery untouched, just fetch URLs
        urls = s.gallery_urls(site_id, auth, project_type) if image_list else {}
        return urls, None

    prior = site_store.get('images') if isinstance(site_store.get('images'), dict) else {}

    def _changed(key, h):
        return forced or prior.get(key) != h

    new_hashes: dict[str, str] = {}
    avatar = None

    # icon (independent asset)
    icon_hash = hashes.compute(icon.read_bytes()) if (icon and icon.exists()) else None
    if icon_hash is not None:
        new_hashes[_ICON_KEY] = icon_hash
        if _changed(_ICON_KEY, icon_hash):
            avatar = s.upload_icon(site_id, auth, prepare_icon(icon, verbosity=verbosity))

    # gallery (per-image)
    changed: set[str] = set()
    for entry in image_list:
        try:
            src = find_image(entry['file'], images_dir)
        except SystemExit:
            continue
        h = _image_hash(src, entry)
        new_hashes[src.stem] = h
        if _changed(src.stem, h):
            changed.add(src.stem)

    removed = bool({k for k in prior if k != _ICON_KEY} - set(new_hashes))

    if image_list and (changed or removed):
        urls = s.upload_images(site_id, auth, image_list, images_dir, verbosity, project_type, changed)
    elif image_list:
        if verbosity >= 1:
            print(f'  [{s.label}] gallery unchanged, skipping')
        urls = s.gallery_urls(site_id, auth, project_type)
    else:
        urls = {}

    if use_hashes:
        site_store['images'] = new_hashes
    return urls, avatar


def run_push(
    *,
    project: Project,
    config: dict,
    puppy_home: Path,
    site: str | None,
    version: str | None,
    content: set[str] | None = None,
    rehash: bool = False,
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

    # rehash needs credentials only when it must fetch gallery URLs to render a description
    rehash_needs_net = rehash and (not content or 'data' in content) and bool(config.get('images'))
    if not rehash or rehash_needs_net:
        missing = [s for s in SITES if s in visitor and s.ref(config) and not s.has_credentials(auth)]
        if missing:
            raise SystemExit(f'Credentials missing for: {", ".join(s.label for s in missing)} — run: puppy auth')

    images_source = config.get('images_source')
    images_dir = Path(images_source) if images_source else puppy_dir / 'images'
    image_list = config.get('images', [])

    projects_ctx = config['projects']
    discovery = ContentDiscovery(puppy_home, project.root)
    file_in_scope = rehash and (not content or 'file' in content)
    zip_path, local_sha = _resolve_file(
        config, puppy_dir, version, project, content, use_hashes, file_in_scope,
    )

    def _file_should(s, site_id, site_store) -> bool:
        if not zip_path:
            return False
        forced = 'file' in content
        if not use_hashes:
            return forced
        if forced:
            return True
        return s.file_changed(site_id, auth, local_sha, site_store, hashes.HASH_FILE)

    def _render_desc(s, image_urls):
        """Resolve this site's config and render its description; returns (config, desc)."""
        site_config = ConfigSynthesizer(puppy_home, project.root, site=s).get_running_config()
        site_config['projects'] = projects_ctx
        local_config = _deep_merge(config, {s.name: site_config[s.name]}) if s.name in site_config else dict(config)
        local_config['description'] = []
        body, source = discovery.find_description(site=s)
        desc = ''
        if body:
            desc = render(body, site_config, source=str(source), site=s, image_urls=image_urls)
            if source and source.suffix == '.md':
                desc = s.convert_md(desc)
        return local_config, desc

    def _data_fp(s, local_config, desc):
        sc = {'name': local_config.get('name', ''), 'summary': local_config.get('summary', ''),
              **local_config.get(s.name, {})}
        return _data_fingerprint(desc, sc, local_config)

    # Each site runs its full pipeline (images → render → data → file) as one
    # parallel task: images upload concurrently, and a per-site failure is isolated.
    def _make_task(s, site_id):
        def task():
            site_store = store.setdefault(s.name, {})

            # 1. images (icon + gallery) — before render so the description can use CDN URLs
            try:
                urls, avatar = _push_images(
                    s, site_id, auth, image_list, images_dir, icon,
                    content, use_hashes, site_store, project_type, verbosity,
                )
            except (AuthExpiredError, SiteError) as e:
                raise _site_error(s, e)
            image_urls = add_image_name_aliases(urls, image_list) if urls else None

            # 2. render this site's description against its own resolved config
            local_config, desc = _render_desc(s, image_urls)

            # 3. data (description + metadata), hash-gated
            fp = _data_fp(s, local_config, desc)
            if hashes.decide('data', fp, upload_set=content, use_hashes=use_hashes, prior=site_store):
                _run_site(s, site_id, local_config, avatar, desc, auth, verbosity)
                if use_hashes:
                    site_store['data'] = fp
            elif verbosity >= 1:
                print(f'  [{s.label}] data unchanged, skipping')

            # 4. file, hash-gated
            if _file_should(s, site_id, site_store):
                _upload_site(s, site_id, auth, zip_path, version, local_config, puppy_dir, verbosity)
                if use_hashes:
                    site_store['file'] = local_sha
        return task

    def _make_rehash_task(s, site_id):
        """Record current content hashes for the in-scope categories without uploading."""
        cats = content or set(hashes.CATEGORIES)

        def task():
            site_store = store.setdefault(s.name, {})

            if 'images' in cats:
                site_store['images'] = _local_image_hashes(image_list, images_dir, icon)

            if 'data' in cats:
                try:
                    urls = s.gallery_urls(site_id, auth, project_type) if image_list else {}
                except (AuthExpiredError, SiteError) as e:
                    raise _site_error(s, e)
                image_urls = add_image_name_aliases(urls, image_list) if urls else None
                local_config, desc = _render_desc(s, image_urls)
                site_store['data'] = _data_fp(s, local_config, desc)

            if 'file' in cats and zip_path:
                site_store['file'] = local_sha

            if verbosity >= 1:
                print(f'  [{s.label}] rehashed {", ".join(sorted(cats))}')
        return task

    make = _make_rehash_task if rehash else _make_task
    tasks = [
        (s.label, make(s, s.ref(config)))
        for s in SITES
        if s in visitor and s.ref(config)
    ]

    try:
        run_sites_parallel(tasks, all_labels=all_labels, verbosity=verbosity)
    finally:
        if use_hashes or rehash:
            hashes.save(puppy_dir, store)

    if verbosity >= 1:
        print(f'[{project.name}] {"rehash" if rehash else "push"} complete')


def _resolve_file(config, puppy_dir, version, project, content, use_hashes, file_in_scope=False):
    """Resolve the zip and its SHA-512 if file upload is in scope, else (None, None)."""
    file_explicit = 'file' in content
    if not (file_explicit or use_hashes or file_in_scope):
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
