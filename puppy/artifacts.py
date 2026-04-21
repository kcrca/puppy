import re
from pathlib import Path


class ArtifactFinder:
    def __init__(self, search_dir: Path):
        self.search_dir = Path(search_dir)

    def find(self, *, project: str, version: str) -> Path:
        pattern = re.compile(rf'^{re.escape(project)}.*[-_.]{re.escape(version)}\.zip$')
        matches = [p for p in self.search_dir.iterdir() if pattern.match(p.name)]
        if not matches:
            raise FileNotFoundError(
                f'No artifact found for {project} version {version}'
            )
        if len(matches) > 1:
            raise FileNotFoundError(
                f'Ambiguous artifacts for {project} version {version}: {matches}'
            )
        return matches[0]
