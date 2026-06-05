from __future__ import annotations

import urllib.request

from puppy.sites.base import Site
from puppy.sites.curseforge import (
    _CF_API,
    _CF_DASH,
    _cf_game_versions_cache,
    _cf_fetch_game_versions,
    _cf_resolve_game_version_ids,
    _cf_get,
    _cf_post_json,
    _cf_delete,
    _cf_post_multipart,
    _cf_send,
    _SPDX_TO_PU_CF,
    CurseForgeSite,
)
from puppy.sites.modrinth import _SPDX_TO_PU_MR, ModrinthSite
from puppy.sites.planetminecraft import PlanetMinecraftSite

CURSEFORGE = CurseForgeSite()
MODRINTH = ModrinthSite()
PMC = PlanetMinecraftSite()

SITES: list[Site] = [CURSEFORGE, MODRINTH, PMC]
SITE_MAP: dict[str, Site] = {s.name: s for s in SITES}
_ALIASES: dict[str, str] = {a: s.name for s in SITES for a in s.aliases}


class SiteVisitor:
    """Iterates over the active sites, respecting an optional filter.

    Construct with the value of the -s/--site CLI flag (or None for all sites).
    """

    def __init__(self, filter: str = None):
        if filter:
            requested = [_ALIASES.get(s.strip(), s.strip()) for s in filter.split(',')]
            unknown = [s for s in requested if s not in SITE_MAP]
            if unknown:
                raise SystemExit(
                    f'Unknown site(s): {", ".join(unknown)}. Valid: {", ".join(SITE_MAP)}'
                )
            self.sites = [s for s in SITES if s.name in requested]
        else:
            self.sites = list(SITES)

    def __iter__(self):
        return iter(self.sites)

    def __contains__(self, site) -> bool:
        return site in self.sites

    def id_or_skip(self, site, value) -> object:
        """Return value for active sites, None for inactive ones."""
        return value if site in self.sites else None
