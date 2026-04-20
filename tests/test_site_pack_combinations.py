import tempfile
import yaml
from pathlib import Path


def _debug(pack, site, ext):
    return Path(tempfile.gettempdir()) / "puppy" / pack / site / f"description{ext}"


def _setup_sibling(home, name, pack, cf_slug=None, mr_slug=None, pmc_slug=None):
    root = home / name
    (root / "puppy").mkdir(parents=True)
    cfg = {"pack": pack}
    if cf_slug:
        cfg["curseforge"] = {"slug": cf_slug, "id": 1}
    if mr_slug:
        cfg["modrinth"] = {"slug": mr_slug}
    if pmc_slug:
        cfg["planetminecraft"] = {"slug": pmc_slug, "id": 1}
    (root / "puppy" / "puppy.yaml").write_text(yaml.dump(cfg))


def test_sibling_cf_url(project_env, run_puppy):
    _setup_sibling(project_env["home"], "Other", "other", cf_slug="other-cf")
    (project_env["source"] / "description.md").write_text("CF: {{ projects.other.curseforge.url }}")
    run_puppy("push", "-n", "-s", "modrinth")
    content = _debug("neonglow", "modrinth", ".md").read_text()
    assert "curseforge.com/minecraft/texture-packs/other-cf" in content


def test_sibling_pmc_url(project_env, run_puppy):
    _setup_sibling(project_env["home"], "Other", "other", pmc_slug="other-pmc")
    (project_env["source"] / "description.md").write_text("PMC: {{ projects.other.planetminecraft.url }}")
    run_puppy("push", "-n", "-s", "modrinth")
    content = _debug("neonglow", "modrinth", ".md").read_text()
    assert "planetminecraft.com/texture-pack/other-pmc" in content


def test_sibling_all_sites_urls(project_env, run_puppy):
    _setup_sibling(project_env["home"], "Other", "other",
                   cf_slug="other-cf", mr_slug="other-mr", pmc_slug="other-pmc")
    (project_env["source"] / "description.md").write_text(
        "CF={{ projects.other.curseforge.url }} MR={{ projects.other.modrinth.url }} PMC={{ projects.other.planetminecraft.url }}"
    )
    run_puppy("push", "-n", "-s", "modrinth")
    content = _debug("neonglow", "modrinth", ".md").read_text()
    assert "other-cf" in content
    assert "other-mr" in content
    assert "other-pmc" in content


def test_multiple_siblings_each_site(project_env, run_puppy):
    _setup_sibling(project_env["home"], "Alpha", "alpha", mr_slug="alpha-mr")
    _setup_sibling(project_env["home"], "Beta", "beta", mr_slug="beta-mr")
    (project_env["source"] / "description.md").write_text(
        "A={{ projects.alpha.modrinth.url }} B={{ projects.beta.modrinth.url }}"
    )
    run_puppy("push", "-n", "-s", "modrinth")
    content = _debug("neonglow", "modrinth", ".md").read_text()
    assert "alpha-mr" in content
    assert "beta-mr" in content


def test_site_specific_var_with_sibling(project_env, run_puppy):
    _setup_sibling(project_env["home"], "Other", "other", mr_slug="other-mr")
    pmc_dir = project_env["source"] / "planetminecraft"
    pmc_dir.mkdir()
    (pmc_dir / "puppy.yaml").write_text(yaml.dump({"pmc_link": "https://pmc.example.com"}))
    (project_env["source"] / "description.md").write_text(
        "Sibling={{ projects.other.modrinth.url }} Extra={{ pmc_link }}"
    )
    run_puppy("push", "-n", "-s", "planetminecraft")
    content = _debug("neonglow", "planetminecraft", ".bbcode").read_text()
    assert "other-mr" in content
    assert "pmc.example.com" in content


def test_pmc_site_var_isolated_from_modrinth(project_env, run_puppy):
    # planetminecraft/puppy.yaml vars must NOT appear in modrinth's rendering.
    pmc_dir = project_env["source"] / "planetminecraft"
    pmc_dir.mkdir()
    (pmc_dir / "puppy.yaml").write_text(yaml.dump({"pmc_only": "secret"}))
    (project_env["source"] / "description.md").write_text("{% if pmc_only %}{{ pmc_only }}{% endif %}")
    run_puppy("push", "-n")

    pmc_content = _debug("neonglow", "planetminecraft", ".bbcode").read_text()
    mr_content = _debug("neonglow", "modrinth", ".md").read_text()
    assert "secret" in pmc_content
    assert "secret" not in mr_content
