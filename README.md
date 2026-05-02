# Introduction

If you have a texture pack, and you want others to use it, you have to put it out there.
Currently, there are three major sites for publishing packs: CurseForge, Modrinth, and Planet Minecraft
(abbreviated here as CF, MR, and PMC).
This creates a problem: How do you publish to all three sites without manually logging into each, pasting in the content, uploading the zip file, ...

Puppy helps you with all this.
It can take your description, screenshots, zip files, icons, etc. and update all the sites with the same information in one command.
It tries to require as little as possible from you to do the work.

# Getting Started

## Installation

Puppy is written in Python (it's there in the name: "**p**ack **up**load in **py**thon").
So you'll need Python, version 3.11 or higher.

You also need a tool called PackUploader.
This is some really cool stuff that communicates with these sites, doing all the hard work.
Puppy uses it as a communication worker for its site-specific work.
So you need a copy, but you don't have to personally interact with it beyond installation.
Typically this will live in your home folder.
So go to your home folder, and then follow the [**Installation** instructions for PackUploader](https://github.com/ewanhowell5195/PackUploader#installation).
Go on, we'll wait right here.

Finally, you need puppy itself.
The most isolated way to install it is to use pipx, which creates a run environment just for puppy without
installing anything elsewhere.

```bash
pip install pipx      # or: brew install pipx  (macOS)
pipx ensurepath       # adds ~/.local/bin to PATH (once)
pipx install git+https://github.com/kcrca/puppy
```

## Basic Puppy

Now let's get to your specific pack.

Suppose you have a pack called Neon, and you keep it in a git repository in your home directory.
(We're going to be using Unix paths here, but this works on Windows, too.)
So go to the top level of your repo and get started with puppy:

```bash
cd ~/neon
puppy init
```

This creates a folder called `puppy`, and within it a few files:

```
~/neon/
└── puppy/                      ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore                  ← must contain auth.yaml for security reasons
    ├── puppy.yaml                  ← shared config
    └── description.md              ← empty project description
```

First, there is `auth.yaml` which has the login information for the sites.
It is important that this not be in a public repo, so puppy requires it to be ignored by `.gitignore`.
Then there is `puppy.yaml` which has the global configuration for the work you want puppy to do.

### Authentication (`auth.yaml`)

Now we're going to send you right back to PackUploader for the [**Authentication** instructions](https://github.com/ewanhowell5195/PackUploader#authentication)
***except*** that you need to put that information in `puppy/auth.yaml` instead.
Of course, if you're not using a site, just don't change its data in `auth.yaml`.

### Settings (`puppy.yaml`)

The file `puppy.yaml` contains global settings for the pack and the sites. Let's go through the fields:

* `name`: Name of the pack.
* `pack`: lowercase version of **name**, often used as a slug or part of a file path.
* `version`: Current version of your pack.
* `minecraft`: Version of minecraft your pack is targeted for.
* `resolution`: Resolution of your pack, as a single integer (8, 16, 32, …)
* `progress`: Percentage of possible textures that your pack covers
* `summary`: The single-line summary of your pack.
* `license`: The license you are using for your pack.
* `links`: relevant external URLs for its own home page, donation sites for fans of your pack, etc.
  These are of the form: `home: https://neon-pack.org/`, `patreon: https://patreon.com/…` and so on.

Now we need to set up details for the various sites.

#### Setup for New Sites

If you want to create a new project at a site, here is the information that puppy needs to create a populated project.
Here is a simple `puppy.yaml` to start with:

```yaml
pack: neon
version: 1.0
minecraft: 26.1
resolution: 16
progress: 100
summary: Neon glow for blocks.
license: MIT

curseforge:
  slug: neon

modrinth:
  slug: neon

planetminecraft:
```

Then you run `puppy create` to create the projects.

This creates your pack's project on the sites.
This might be good if you're just getting started.
But you probably already have your pack, so let's fill this out.

The file `description.md` has a Markdown version of your description of your pack. 
For now let's just presume you want some text, images, and the like;
we will talk about expansion later.
Just create a `description.md`, which will be converted for each site to its native language.

The pack itself, and its icon, logo, and banner can be specified in the yaml, such as:

```yaml
zip: '{{top}}/neon_1.0.zip'
logo: '{{top}}/neon.png'
icon: '{{top}}/icon.png'
banner: '{{top}}/banner.png'
```

This will use the top-level file `neon_1.0.zip` (`~/neon/neon_1.0.zip`) for the zip file, and get the icon and logo from the top level as well.
(You could instead copy them into the puppy directory.)

You probably also want an image gallery.
That's pretty simple as well.
You can create an `images.yaml` file that looks something like this:

```yaml
source: '{{top}}/gallery'

images:
- name: Overview
  description: A general overview of the pack
  file: overview
  embed: true
  featured: true
- name: Mobs
  description: Here's an overview of the mobs!
  file: mobs
```

This looks for a directory `gallery` at your top level, and pulls images from there. 
This example has two files, named "Overview" and "Mobs".
Their sources are (respectively) `~/neon/gallery/overview.png` and `~/neon/gallery/mobs.png`
The `description` field is used as an image caption / title.
The image can be pretty much any common image type, but the sites usually require png files so puppy will convert them to png if needed.
Of course, that will be done each time it runs, so you might want to just give it png files in the first place.

The `embed` tag, if `true`, says to also include the image where `{{ images }}` appears in the description;
`featured` will mark the image as featured on sites that support it.

That's all you need for a simple setup:

```
~/neon/
└── puppy/                      ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore                  ← must contain auth.yaml for security reasons
    ├── puppy.yaml                  ← shared config
    ├── icon.png                    ← the pack icon
    ├── description.md              ← description of your pack
    └── images.yaml                 ← the image library
```

After you successfully create remote projects, the data from them is pulled back and placed in puppy.yaml.
So you will see many fields populated there from the site.

#### Setup for Existing Sites

If you already have a project at an existing site, you can pull the data from it to start your settings.
You just provide the id and (for PMC) the slug.
These are stored in the site-specific parts of `puppy.yaml`.

```yaml
curseforge:
  id: 123345

modrinth:
  id: XYZZY

planetminecraft:
  id: 12345
  slug: neon-is-glowing
```

(Any site you don't give info for will be skipped.)

Then run `puppy pull`.
You can run puppy from either the top dir (`~/neon`) or anywhere under the puppy dir (`~/neon/puppy`).

If this runs successfully, `puppy.yaml` will now have a ton of other data, pulled from the site.

```
~/neon/
└── puppy/                      ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore                  ← must contain auth.yaml for security reasons
    ├── puppy.yaml                  ← shared config
    ├── icon.png                    ← the pack icon
    ├── logo.png                    ← the pack logo
    ├── banner.png                  ← the pack banner
    ├── images/                     ← image gallery
    │   ├── images.yaml                 ← image metadata
    │   ├── overview.png                ← an image gallery image
    │   └── mobs.png                    ← an image gallery image
    ├── curseforge/                 ← CurseForge's site data
    │   └── description.html            ← description used at CurseForge
    ├── modrinth/                   ← Modrinth's site data
    │   └── description.md              ← description used at Modrinth
    └── planetminecraft/            ← Planet Minecraft's site data
```

A few things to note:

* The icon, logo, and banner images are downloaded only if they don't exist locally.
  This means that the first site to provide each will be the one used.
* The icon isn't available from PMC.
* The `images` data is a union of the images downloaded from all the sites, in the order they were accessed.
  This means that the _last_ site to provide each will be the one used.
* PMC doesn't have a way to get the current description, sigh.

But most importantly, this is more complicated than you need when using puppy, except in some rare cases.
Your best move will be to merge this data to be simpler.
Specifically, puppy is simplest when you have one top-level `description.md` file.

* If you were manually making them all the same, just take the one from Modrinth and remove the others, and remove their directories.
* If you had different content, but don't care to continue that, merge any differences you want to preserve from the HTML and BBCode versions before removing anything.
* If you do want them different, just leave them as they are.

If your existing Modrinth site is far from your best description, this will take more work.
You can find HTML to markdown and BBCode to markdown converters that could be helpful to get a markdown file to get you started.

# Multiple Packs/Projects

There are several ways to make your description customized to different sites and other things.
But before we get to that, we need to talk about how you can have multiple pack projects generated from a single repo.

Even if you aren't supporting multiple packs it fits into expansion, so its worth knowing.
It isn't very complex, so you can certainly handle it.

With one pack, the puppy home (`~/neon/puppy`) is also the *project home.*
With multiple packs, the puppy home holds values that are shared across all the projects,
and each project has a subdirectory that is its own project home, for its individual values.
During expansion, then, a distinction is made between puppy home and project home.
If you only have one project, these are the same directory.

If you have multiple packs, the first thing you have to do is tell that to puppy, via the `projects` field in `puppy.yaml`:

```yaml
projects:
  - neon
  - dark
```

You then create a subdirectory for each project.
That directory has the project-specific parts of the top-level `puppy.yaml`:

```
~/neon/
└── puppy/                      ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore                  ← must contain auth.yaml for security reasons
    ├── puppy.yaml                  ← shared config for all projects
    ├── neon/                       ← Neon's project home
    │   ├── puppy.yaml              ← shared config for Neon
    │   └── images/                     ← Neon's image gallery
    │       ├── images.yaml                 ← Neon's image metadata
    │       ├── overview.png                ← a Neon image gallery image
    │       └── mobs.png                    ← a Neon image gallery image
    ├── dark/                       ← Dark's project home
    │   ├── puppy.yaml              ← shared config for Dark
    │   └── images/                     ← Dark's image gallery
    │       ├── images.yaml                 ← Dark's image metadata
    │       ├── overview.png                ← a Dark image gallery image
    │       └── mobs.png                    ← a Dark image gallery image
    ├── curseforge/                 ← CurseForge's site data
    │   └── description.html            ← description used at CurseForge
    ├── modrinth/                   ← Modrinth's site data
    │   └── description.md              ← description used at Modrinth
    └── planetminecraft/            ← Planet Minecraft's site data
        └── description.bbcode          ← description used at Planet Minecraft
```

For a single pack, the puppy home _is_ the project home for the one project you've got.

## Information Priority

When puppy is looking for information of any kind (besides the stuff in `auth.yaml`), it looks for it in this order:

1. The project's site data
2. The project's data
3. The site's data
4. The global data

So for each upload, the complete puppy.yaml that's used is a merge of all these specific puppy.yaml files (that exist) in a reverse of that order, so more specific values overwrite less-specific ones.

## Advanced Configuration

If you need it, you can have site-specific directories in each project's home.
And each of these directories can have `puppy.yaml` that will override other less-specific values.

So the most complicated puppy directory you're ever likely to see looks like this:

```
~/neon/
└── puppy/                      ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore                  ← must contain auth.yaml for security reasons
    ├── puppy.yaml                  ← shared config for all projects
    ├── icon.png                    ← the pack icon
    ├── neon/                       ← Neon's project home
    │   ├── puppy.yaml              ← shared config for Neon
    │   ├── images/                     ← Neon's image gallery
    │   │   ├── images.yaml                 ← Neon's image metadata
    │   │   ├── overview.png                ← a Neon image gallery image
    │   │   └── mobs.png                    ← a Neon image gallery image
    │   ├── curseforge/                 ← Neon's CurseForge site data
    │   │   ├── puppy.yaml                  ← Neon's overrides for CurseForge
    │   │   └── foo.html                    ← file used for CurseForge generation
    │   ├── modrinth/                   ← Neon's Modrinth site data
    │   │   ├── puppy.yaml                  ← Neon's overrides for Modrinth
    │   │   └── foo.md                      ← file used for Modrinth generation
    │   └── planetminecraft/            ← Neon's Planet Minecraft site data
    │       ├── puppy.yaml                  ← Neon's overrides for Planet Minecraft
    │       └── foo.bbcode                  ← file used for Planet Minecraft generation
    ├── dark/                       ← Dark's project home
    │   ├── puppy.yaml              ← shared config for Dark
    │   ├── images/                     ← Dark's image gallery
    │   │   ├── images.yaml                 ← Dark's image metadata
    │   │   ├── overview.png                ← a Dark image gallery image
    │   │   └── mobs.png                    ← a Dark image gallery image
    │   ├── curseforge/                 ← Dark's CurseForge site data
    │   │   ├── puppy.yaml                  ← Dark's overrides for CurseForge
    │   │   └── foo.html                    ← file used for CurseForge generation
    │   ├── modrinth/                   ← Dark's Modrinth site data
    │   │   ├── puppy.yaml                  ← Dark's overrides for Modrinth
    │   │   └── foo.md                      ← file used for Modrinth generation
    │   └── planetminecraft/            ← Dark's Planet Minecraft site data
    │       ├── puppy.yaml                  ← Dark's overrides for Planet Minecraft
    │       └── foo.bbcode                  ← file used for Planet Minecraft generation
    ├── curseforge/                 ← CurseForge's site data
    │   ├── puppy.yaml                  ← Shared overrides for CurseForge
    │   └── xyzzy.html                  ← file used for CurseForge generation
    ├── modrinth/                   ← Modrinth's site data
    │   ├── puppy.yaml                  ← Shared overrides for Modrinth
    │   └── xyzzy.md                    ← file used for Modrinth generation
    └── planetminecraft/            ← Planet Minecraft's site data
        ├── puppy.yaml                  ← Shared overrides for Planet Minecraft
        └── xyzzy.bbcode                ← file used for Planet Minecraft generation
```

Each of these can be omitted if you don't need it. I'm hoping you never see all this in your own work,
but it's there if you need it.

# Expansion

The description is central to your public face, and so it is central to puppy.
In its simplest form, this is just the `summary` property from `puppy.yaml` plus the contents of `description.md`. 
For basic text and images, this will be all you need.

But there are cases where you definitely want more than this.
As one example, each website has its own user feedback system.
So that section where you ask people to tell the system they think your stuff is cool requires site-specific customization.
That needs to be different for each system.

First, values inside yaml files and the text in `description.md` is run through Jinja2, which uses a pretty common template expansion syntax.
The most relevant here is that values inside `{{ }}` are treated specially.
They reference other values to build text dynamically.
So your `description.md` could have text like this:

```
This is version {{ version }} of Neon.
```

The text `{{ version }}` will be replaced with the value of the `version` from `puppy.yaml`.
So when you change that version, the description will always be up to date.

The full syntax has a lot of options, including conditional expansion.
You can [read more about it](https://jinja.palletsprojects.com/en/stable/templates/) if you want more control.

We also define a few path-related variables to make it easier to name files.
For example, your `images.yaml` file can set the `source` value to `{{top}}/gallery`,
which will look for the gallery subdirectory of the top of your repo (`~/neon/gallery`).
Besides `top` (`~/neon`), the other values defined for this are `puppy` (`~/neon/puppy`) and `project` (same as `puppy` for a single pack, `~/neon/puppy/neon` for multi-pack).

For another example, when it comes to users showing you they like your work,
CF and Modrinth only allow them to show that by following your pack, but PMC gives many engagement options.
(Though CF is planning to add favorites, they say).

The way to handle this in puppy is to use parameter expansion.
Your `description.md` would have something like this:

```description.md
And if you like this pack, {{ like }}!

```
Your `puppy.yaml` could have a segment that looks like this:

```yaml
like: 'follow this pack'

planetminecraft:
  like: 'give me a diamond, favorite this pack, and subscribe to my content'
```

This says that the default value for the `like` parameter is simple, but a specific override exists for PMC.

In the uploaded descriptions, the value of `like` will be replaced for each site with its particular brand of liking.
And the text will be good for every site.

You can use any yaml value in your expansion, including values inside other values.

If you have larger amounts of text than you want to put in a yaml file, you can include other files.
For example, suppose your `description.md` contains "{{ disclaimer }}" and there is no yaml value for that.
Puppy will look in its home for a file to insert there, first in the site's specific directory, then in the top.
It will also look for files in the specific language of the site, then in `.md` files.

Here are some specific examples.
First, let's look at the simplest single pack case.
Suppose `description.md` contains `{{ foo }}`, what will puppy look for?
We will use "<site>" to name the specific site being pushed to, 
and "<ext>" to mean the site-specific language file extension ("html" for CF, "md" for Modrinth, "bbcode" for PMC).

1. `foo` in `~/neon/puppy/<site>/puppy.yaml`
2. `foo` in `~/neon/puppy/puppy.yaml`
3. `~/neon/puppy/<site>/foo.<ext>`
4. `~/neon/puppy/<site>/foo.md`
5. `~/neon/puppy/foo.<ext>`
6. `~/neon/puppy/foo.md`

Now let's consider the multipack case.
You will see that this is the same as the above with the project added in as a priority before the basic puppy home.
We will use `<project>` to mean the project home:

1. `foo` in `~/neon/puppy/<project>/<site>/puppy.yaml`
2. `foo` in `~/neon/puppy/<project>/puppy.yaml`
3. `foo` in `~/neon/puppy/<site>/puppy.yaml`
4. `foo` in `~/neon/puppy/puppy.yaml`
5. `~/neon/puppy/<project>/<site>/foo.<ext>`
6. `~/neon/puppy/<project>/<site>/foo.md`
7. `~/neon/puppy/<site>/foo.<ext>`
8. `~/neon/puppy/<site>/foo.md`
9. `~/neon/puppy/foo.<ext>`
10. `~/neon/puppy/foo.md`


You can include a specific file using the `read` function.
You can use an absolute path, or one of  `top`, `puppy`, or `project` to create a path, as in `{{ read( top + '/signature') }}`.
Relative paths start from the file that contains the invocation of `read`.

## Intra-Site Links

Another area where you want your description to adapt to each site is to have links to other projects on the site.
This might be to a sibling pack, or to an unrelated project.
For this you simply use something like `{{ projects.dark.url }}`, as in `\[the Dark project\]({{ projects.dark.url }})`.
This will be expanded to the correct URL on each site.

For unrelated projects, you can make them accessible by adding this to your `puppy.yaml`:

```yaml
linked_projects:
  restworld:
    slug: restworld
    planetminecraft:
      slug: restworld-texturepack-testing-world
```

This says that the slug for the restworld project is `restworld` except on PMC, where it's that longer thing.
Then you can use `{{ projects.restworld.url }}` in your description to reference it.

# Pre-Check

Of course, once you add this kind of thing, you want to know whether puppy is generating what you want it to.
This is why there's a dry-run mechanism.

`puppy --dry-run push` will create a web page that has all the content for the push, and print out the URL and open it in your web browser.
The page has a table at the top for the values it will set for each site,
a tab for each site to show you the generated description,
and at the bottom the image gallery.
(The `--no-open` option will suppress the automatic opening of the file.)

# Running Puppy

Puppy has several commands, and many options.
Some of them only apply to some commands, but others apply universally.

The overall syntax is:

```
puppy [-h] [-n] [-v | -vv] [-d PATH] [-s SITE[,SITE]] [-V STRING] [-p] [-f] [-I] [--no-open] [--worker PATH] [{push,create,pull,init,clean}] [project ...]
```

## Global Options

* **-h**, **--help**: show help.
* **-v**: High-level progress output.
* **-vv**: Even more debug output.
* **-d**, **--dir _PATH_**: Project directory (default: current working directory).
* **-s**, **--site _SITENAME_**: Limit action to one or more sites (comma-separated). You can use the abbreviations "cf", "mr", and "pmc" for sites.
* **--worker _PATH_**: PackUploader worker directory (default: `~/PackUploader`).

## Subcommands

* **init**: Set up the puppy directory in the current directory, or **--dir** points.
* **create**: Create project on the site(s). If run from a terminal, this will prompt for confirmation.
    * **-f**, **--force**: Skip the confirmation prompt.
* **pull**: Pull data from the site(s). This will not overwrite existing images, but it will merge new data into yaml files.
    * **-I**, **--images**: Also pull logo, icon, banner, and image gallery.
* **push**: Push description, metadata, logo, icon, and banner.
    * **-I**, **--images**: Also push image gallery.
    * **-p**, **--pack**: Also push the `.zip` file. This will be skipped if site-specific data says it is not needed.
    * **-f**, **--force**: With `--pack`, pushes the `.zip` no matter what.
    * **-V**, **--version _VERSION_**: Use this version, overriding other information.
    * **-n**, **--dry-run**: Create a pre-check HTML page, printing the URL and opening it.
    * **--no-open**: With `-n`, suppresses opening the file.
* **clean**: Clean up the worker directory, resetting it back to its original state.

## Projects

If you have multiple projects, you can list specific ones on the command line after the subcommand.

# `puppy.yaml` Properties

Here are the values that puppy looks at in the `puppy.yaml` files.
Remember that the yaml values used during runs are created by merging any existing relevant `puppy.yaml` files.
So when these are in the top level `puppy.yaml`, they can be overridden in lower levels.

## Identity

| Field | Meaning |
|---|---|
| `name` | Display name. Title-cased if all-lowercase input (`neon` → `Neon`). Derived from directory name if absent; written back automatically. |
| `pack` | Internal slug. Lowercase alphanumeric only. Derived from `name` or directory if absent; written back automatically. |
| `slug` | Default slug for all sites. Per-site `slug` overrides this. |
| `version` | Version string used by `push`. Overridden by `-V` on the CLI. |
| `summary` | One-line description shown in site search results. |
| `github` | Source repository URL. Set automatically from `links.source`; used by PU for CF source link and Modrinth `source_url`/`issues_url`. Can be set directly to override. |

## Pack Content

| Field | Meaning |
|---|---|
| `icon` | Explicit path to the icon PNG. Discovered automatically (single `.png` in project dir, excluding `banner.png` and `logo.png`) if absent. Must be square. |
| `banner` | Explicit path to the banner image (`banner.png` in project dir if absent). Staged to the worker as `thumbnail.png` (PU's name for it). |
| `logo` | Explicit path to the logo image (`logo.png` in project dir if absent). Displayed at fixed aspect ratio (1280×256). |
| `zip` | Explicit path to the zip artifact. Discovered automatically (single `.zip` in project dir) if absent. |
| `optifine` | `true`/`false` — whether the pack requires OptiFine. Default `false`. |
| `video` | YouTube video ID for an associated video. |
| `after_push` | Message printed after all projects are pushed (not during dry-run). When set inside a site block, prints only when that site is active, prefixed with the site label. |
| `minecraft` | Game version for artifact upload. String → exact version; dict → passed as-is. Required for `push --pack` unless `versions` is set. |
| `versions` | Explicit Minecraft version list. Alternative to `minecraft`. |

## Description & Templates

| Field | Meaning |
|---|---|
| `md_html_tags` | List of HTML tags to protect during Markdown conversion and map to site equivalents (e.g. `<u>` → `[u]` for PMC). Default `['u']`. |

## Multi-Pack

| Field | Meaning |
|---|---|
| `projects` | List of project subdirectory names. Puppy iterates these in order. |
| `linked_projects` | Map of external projects (outside this puppy home) to inject into the Jinja `projects.*` context. Each entry has per-site sub-objects. |

## Neutral Metadata (expand to all sites automatically)

| Field | Meaning |
|---|---|
| `resolution` | Pack resolution in pixels (e.g. `16`). Sets CF `mainCategory: 16x`, Modrinth tier tags, and PMC `resolution`/`tags`. |
| `progress` | Completion percentage 0–100. Sets PMC `progress`. Ignored by CF and Modrinth. |
| `license` | SPDX identifier (e.g. `CC-BY-4.0`). Sets CF `license` (last hyphen → space) and Modrinth `license` unchanged. Ignored by PMC. |
| `links.home` | Project home page URL. Sets CF `socials.website` and PMC `website.link`. |
| `links.source` | Source repository URL. Sets top-level `github` (used by PU for CF and Modrinth). |
| `links.issues` | Issue tracker URL. Stored but not yet applied to any site (requires PU change). |
| `links.patreon` | Patreon donation URL. CF: first donation key wins as `{type, value}`. Modrinth: `donation.patreon`. |
| `links.kofi` | Ko-fi donation URL. Same expansion as `patreon`. |
| `links.paypal` | PayPal donation URL. Same expansion. |
| `links.buyMeACoffee` | Buy Me a Coffee URL. Same expansion. |
| `links.github_sponsors` | GitHub Sponsors URL. CF: `type: github`. Modrinth: `donation.github`. |
| `links.other` | Catch-all donation URL. Same expansion. |

## CurseForge block (`curseforge:`)

| Field | Meaning |
|---|---|
| `id` | CurseForge project ID. Written by `pull`/`create`. |
| `slug` | Project slug on CurseForge. |
| `mainCategory` | Main category string (e.g. `16x`). Set by `resolution`; override here. |
| `additionalCategories` | Map of category name → `true`/`false`. |
| `license` | License string (e.g. `CC-BY 4.0`). Set by `license`; override here. |
| `donation` | `{type: platform, value: url}`. Set from first `links.*` donation key; override here. |
| `socials` | Map of social platform names → URLs. `website` set from `links.home`; others (discord, patreon, github, etc.) set directly. |

## Modrinth block (`modrinth:`)

| Field | Meaning |
|---|---|
| `id` | Modrinth project ID. Written by `pull`/`create`. Resolved from `slug` automatically if absent. |
| `slug` | Project slug on Modrinth. |
| `type` | Project type: `resourcepack`, `mod`, `modpack`, etc. Default `resourcepack`. Affects the Modrinth URL path segment. |
| `license` | SPDX license. Set by `license`; override here. |
| `tags` | Map of resolution tier name → `true`/`false` (e.g. `16x: true`). Set by `resolution`; override individual tiers here. |
| `donation` | Map of platform name → URL (`patreon`, `kofi`, `paypal`, `buyMeACoffee`, `github`, `other`). Set from `links.*`; override here. |
| `discord` | Discord server URL. |

## Planet Minecraft block (`planetminecraft:`)

| Field | Meaning |
|---|---|
| `id` | PMC project ID. Written by `pull`/`create`. |
| `slug` | Project slug on PMC. |
| `resolution` | Resolution integer. Set by `resolution`; override here. |
| `progress` | Completion percentage 0–100. Set by `progress`; override here. |
| `tags` | List of tag strings (e.g. `['16x', '16x16']`). Neutral `resolution` appends to this; add others here. |
| `category` | PMC category string. |
| `modifies` | Map of modification target → `true`/`false`. |
| `website.link` | Website URL. Set from `links.home`; override here. |
| `website.title` | Website display title shown alongside the link. |
| `credit` | Credit string displayed on the PMC project page. |
