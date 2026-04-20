from __future__ import annotations


SITES = ["curseforge", "modrinth", "planetminecraft"]


class SiteVisitor:
    """Iterates over the active sites, respecting an optional filter.

    Construct with the value of the -s/--site CLI flag (or None for all sites).
    """

    def __init__(self, filter: str | None = None):
        if filter:
            requested = [s.strip() for s in filter.split(",")]
            unknown = [s for s in requested if s not in SITES]
            if unknown:
                raise SystemExit(f"Unknown site(s): {', '.join(unknown)}. Valid: {', '.join(SITES)}")
            self.sites = [s for s in SITES if s in requested]
        else:
            self.sites = list(SITES)

    def __iter__(self):
        return iter(self.sites)

    def __contains__(self, site: str) -> bool:
        return site in self.sites

    def id_or_skip(self, site: str, value) -> object:
        """Return value for active sites, None for inactive ones.

        Used when staging project.json: inactive sites get a null ID so the
        worker knows to skip them.
        """
        return value if site in self.sites else None
