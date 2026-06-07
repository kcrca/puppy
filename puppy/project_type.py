from __future__ import annotations

_UNIVERSAL = frozenset({'license', 'title', 'links', 'after_push'})
_PACK_ONLY = frozenset({'resolution', 'progress'})
_MOD_ONLY = frozenset({'client_side', 'server_side', 'loaders'})
_ALL_NEUTRAL = _UNIVERSAL | _PACK_ONLY | _MOD_ONLY


class ProjectType:
    name: str
    valid_neutral_fields: frozenset[str]
    supported_site_names: frozenset[str]

    def warn_inapplicable(self, config: dict) -> dict:
        offenders = sorted(f for f in _ALL_NEUTRAL - self.valid_neutral_fields if f in config)
        if not offenders:
            return config
        print(f'warning: {", ".join(offenders)} not applicable for project_type "{self.name}"; ignored')
        config = dict(config)
        for f in offenders:
            del config[f]
        return config


class _Pack(ProjectType):
    name = 'pack'
    valid_neutral_fields = _UNIVERSAL | _PACK_ONLY
    supported_site_names = frozenset({'curseforge', 'modrinth', 'planetminecraft'})


class _Mod(ProjectType):
    name = 'mod'
    valid_neutral_fields = _UNIVERSAL | _MOD_ONLY
    supported_site_names = frozenset({'curseforge', 'modrinth'})


class _World(ProjectType):
    name = 'world'
    valid_neutral_fields = _UNIVERSAL
    supported_site_names = frozenset({'curseforge', 'modrinth'})


PACK = _Pack()
MOD = _Mod()
WORLD = _World()

PROJECT_TYPES: dict[str, ProjectType] = {
    t.name: t for t in [PACK, MOD, WORLD]
}
