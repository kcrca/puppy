# Puppy — Outstanding Work

## Unimplemented Features

- **`convert` command**: Convert between description formats — `.bbcode` → `.md`, `.html` → `.md` — using existing transformers plus a well-respected HTML-to-Markdown library for the HTML case. Useful after importing a description manually from PMC or CurseForge.



- **Duplicate check on create (CF and PMC)**: Before creating, warn the user that duplicates are possible on sites without unique name enforcement. For CF, search by name (filtered to texture packs) and show matches, asking if theirs is one of them or a new project — if an existing ID is chosen, run import instead. For PMC there is no API, so only a manual reminder is possible. `--force` should skip any interactive check. Modrinth is not a concern — its API rejects duplicate slugs cleanly. **Open question:** do we only care about conflicts with the user's own existing projects, or also with other people's projects with the same name?


- **Non-pack project types**: Set up for at least some kinds of non-pack projects, like worlds.


- **Handle other VCS systems**: Currently assumes git for the auth.yaml gitignore check. Should detect Mercurial, SVN, etc., or gracefully handle non-VCS directories.
- **`--skip-auth-check` flag**: Bypass the auth.yaml gitignore check for unknown or non-existent VCS systems.

## Design Questions

- **`links.issues` not applied**: The neutral `links.issues` field is accepted but not wired to any site.
  Modrinth derives `issues_url` from `source` automatically (`github + "/issues"`).
  To support an independent issues URL, ask Ewan to read `project.config.links?.issues` in PU's modrinth.js.

- **PMC description import**: PMC blocks non-browser HTTP, so the description can't be fetched with `urllib`.
  Ask Ewan to include the BBCode description string in PU's import JSON output — it already has the data (via `getDescription()`), it just doesn't write it out.
  Once available, puppy would save it to `planetminecraft/description.bbcode`.

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

- **Modrinth API mock**: Add a reusable `fake_modrinth` fixture (or similar) that intercepts `urllib.request.urlopen` calls to `api.modrinth.com` and returns canned responses.
  This would let tests cover `needs_upload`, `resolve_id`, and donation/tag expansion without hitting the network.
  Similar mocks needed for CurseForge (`authors.curseforge.com`) and the CF description API.

- **Integration tests on live sites**: End-to-end `create`, `import`, and `push --pack` against real CurseForge, Modrinth, and PMC accounts.
