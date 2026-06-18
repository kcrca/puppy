# Puppy Examples

This directory contains example files for a single-pack project.
Copy them into your pack's `puppy/` directory and edit to suit.

## Single-pack directory layout

```
my-pack/                    ← git repo root
  my-pack-1.0.zip           ← artifact (auto-discovered)
  pack.png                  ← icon (auto-discovered)
  puppy/
    .gitignore              ← must list auth.yaml
    auth.yaml               ← credentials — never commit
    puppy.yaml              ← project config
    description.md          ← shared description template (Jinja2)
    images.yaml             ← image gallery metadata
    curseforge/
      description.html      ← optional: CF-specific override (HTML)
    planetminecraft/
      description.bbcode    ← optional: PMC-specific override (BBCode)
```

For multi-pack repos, each pack gets its own subdirectory under `puppy/`:

```
neon/
  puppy/
    puppy.yaml              ← global config (shared defaults)
    neon/
      puppy.yaml            ← per-pack config
      description.md
    dark/
      puppy.yaml
      description.md
```

## Quickstart

```
cd my-pack
puppy init pack        # create puppy/ skeleton (auth.yaml, .gitignore, puppy.yaml, description.md)
# edit puppy/auth.yaml with your credentials
# edit puppy/puppy.yaml with your project IDs and metadata
puppy push --dry-run   # preview without uploading
puppy push             # update descriptions, images, icon
puppy push -c file     # also upload the zip artifact
```

The files in this directory show what a complete project looks like after filling in the `init` skeleton.
`images.yaml` is not created by `init` — add it when you're ready to manage the image gallery.

## Files in this directory

| File | Purpose |
|------|---------|
| `auth.yaml` | Credential template — copy to `puppy/auth.yaml` |
| `gitignore` | Copy to `puppy/.gitignore` (named without dot so git ignores it here) |
| `puppy.yaml` | Config template — copy to `puppy/puppy.yaml` |
| `description.md` | Description template showing Jinja2 features |
| `images.yaml` | Image gallery metadata example |
