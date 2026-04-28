# Puppy — Outstanding Work

## Unimplemented Features

- **`convert` command**: Convert between description formats — `.bbcode` → `.md`, `.html` → `.md` — using existing transformers plus a well-respected HTML-to-Markdown library for the HTML case. Useful after importing a description manually from PMC or CurseForge.



- **Duplicate check on create (CF and PMC)**: Before creating, warn the user that duplicates are possible on sites without unique name enforcement. For CF, search by name (filtered to texture packs) and show matches, asking if theirs is one of them or a new project — if an existing ID is chosen, run import instead. For PMC there is no API, so only a manual reminder is possible. `--force` should skip any interactive check. Modrinth is not a concern — its API rejects duplicate slugs cleanly. **Open question:** do we only care about conflicts with the user's own existing projects, or also with other people's projects with the same name?


- **Non-pack project types**: Set up for at least some kinds of non-pack projects, like worlds.


- **Handle other VCS systems**: Currently assumes git for the auth.yaml gitignore check. Should detect Mercurial, SVN, etc., or gracefully handle non-VCS directories.
- **`--skip-auth-check` flag**: Bypass the auth.yaml gitignore check for unknown or non-existent VCS systems.

## Design Questions

- **PMC title override**: PMC uses `name` as the project title, but users often want something like "Pack Name: Subtitle".
  Requires a `planetminecraft.title` field in `puppy.yaml` and a one-line patch to PackUploader's `src/planetminecraft.js` line 196: `title: project.config.planetminecraft?.title ?? project.config.name`.
  Defaults to `name` so no breaking change.



- **Jinja conditional wrapping**: No clean syntax for wrapping text in tags conditionally. Options: macro+call block, repeated `{% if %}` tags, or a custom Jinja extension. Verbose in current form.
- **Site abbreviations**: `cf`, `mr`, `pmc` added as aliases — reconsider whether this is a good idea.

## Cleanup

- **Remove "e.g." and "i.e." from spec and code comments**: Replace with plain English ("for example", "that is").

## UX

- **Default verbosity**: Consider making `-v` the default since uploads take a while and silence is confusing. Currently requires explicit `-v` flag.

## Testing Gaps

- **Integration tests on live sites**: End-to-end `create`, `import`, and `push --pack` against real CurseForge, Modrinth, and PMC accounts.
