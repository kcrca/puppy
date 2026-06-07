from __future__ import annotations

from typing import NamedTuple

_UNIVERSAL = frozenset({'license', 'title', 'links', 'after_push'})
_PACK_ONLY = frozenset({'resolution', 'progress'})
_MOD_ONLY = frozenset({'client_side', 'server_side', 'loaders'})
_ALL_NEUTRAL = _UNIVERSAL | _PACK_ONLY | _MOD_ONLY


class ProjectInfo(NamedTuple):
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


PACK = ProjectInfo('pack', _UNIVERSAL | _PACK_ONLY, frozenset({'curseforge', 'modrinth', 'planetminecraft'}))
MOD = ProjectInfo('mod', _UNIVERSAL | _MOD_ONLY, frozenset({'curseforge', 'modrinth'}))
WORLD = ProjectInfo('world', _UNIVERSAL, frozenset({'curseforge', 'planetminecraft'}))

PROJECT_TYPES: dict[str, ProjectInfo] = {
    t.name: t for t in [PACK, MOD, WORLD]
}
