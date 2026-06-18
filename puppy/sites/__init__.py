from __future__ import annotations

import urllib.request

from puppy.sites.base import Site
from puppy.sites.curseforge import CurseForgeSite
from puppy.sites.modrinth import ModrinthSite
from puppy.sites.planetminecraft import PlanetMinecraftSite

CURSEFORGE = CurseForgeSite()
MODRINTH = ModrinthSite()
PMC = PlanetMinecraftSite()

SITES: list[Site] = [CURSEFORGE, MODRINTH, PMC]
SITE_MAP: dict[str, Site] = {s.name: s for s in SITES}
_ALIASES: dict[str, str] = {a: s.name for s in SITES for a in s.aliases}


class SiteVisitor:
    """Iterates over the active sites, respecting an optional filter and project_type."""

    def __init__(self, filter: str = None, project_type: str = 'pack'):
        from puppy.project_type import PROJECT_TYPES
        pt = PROJECT_TYPES.get(project_type)
        if filter:
            requested = [_ALIASES.get(s.strip(), s.strip()) for s in filter.split(',')]
            unknown = [s for s in requested if s not in SITE_MAP]
            if unknown:
                raise SystemExit(
                    f'Unknown site(s): {", ".join(unknown)}. Valid: {", ".join(SITE_MAP)}'
                )
            self.sites = [s for s in SITES if s.name in requested]
            if pt is None:
                raise SystemExit(f'Unknown type: "{project_type}"')
            unsupported = [s for s in self.sites if not s.supports(project_type)]
            if unsupported:
                raise SystemExit(
                    f'Site(s) {", ".join(s.label for s in unsupported)} do not support type "{project_type}"'
                )
        else:
            self.sites = [] if pt is None else [s for s in SITES if s.supports(project_type)]

    def __iter__(self):
        return iter(self.sites)

    def __contains__(self, site) -> bool:
        return site in self.sites

    def id_or_skip(self, site, value) -> object:
        """Return value for active sites, None for inactive ones."""
        return value if site in self.sites else None
