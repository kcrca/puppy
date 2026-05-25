# Changelog

## 1.0 — 2026-05-25

Initial release.

- Publish resource packs to CurseForge, Modrinth, and Planet Minecraft from one config
- `puppy init` scaffolds a new project
- `puppy push` uploads to all configured sites; `push -n` for dry run
- `puppy pull` imports an existing project from its live pages
- Template rendering: Jinja2 variables and Markdown in descriptions
- Per-site description and image configuration
- Auth stored separately in `~/.puppy/auth.yaml`
