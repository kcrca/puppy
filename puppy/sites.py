from __future__ import annotations


SITES = ["curseforge", "modrinth", "planetminecraft"]


class SiteVisitor:
    """Iterates over the active sites, respecting an optional filter.

    Construct with the value of the -s/--site CLI flag (or None for all sites).
    """

    def __init__(self, filter: str | None = None):
        self.active: list[str] = [s for s in SITES if not filter or s == filter]

    def __iter__(self):
        return iter(self.active)

    def __contains__(self, site: str) -> bool:
        return site in self.active

    def id_or_skip(self, site: str, value) -> object:
        """Return value for active sites, None for inactive ones.

        Used when staging project.json: inactive sites get a null ID so the
        worker knows to skip them.
        """
        return value if site in self.active else None
