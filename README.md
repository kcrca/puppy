# Introduction

If you have a texture pack, mod, and/or world save, and you want others to use it, you have to put it out there.
Currently, there are three major sites for publishing minecraft projects:
[CurseForge](https://curseforge.com), [Modrinth](https://modrinth.com), and [Planet Minecraft](https://planetminecraft.com)
(abbreviated here as **CF**, **MR**, and **PMC**).
This creates a problem: How do you publish to all three sites without manually logging into each, pasting the same stuff in the content, uploading the zip file, ...

Puppy helps you with all this.
It can take your description, screenshots, zip files, icons, etc. and update all the sites with the same information in one command.
It tries to require as little as possible from you to do the work.

## Acknowledgements

Puppy was originally a front end to the tool [PackUploader](https://github.com/ewanhowell5195/PackUploader), by Ewan Howell,
that deals exclusively with texture packs.
I outgrew it, but it gave me both impetus and knowledge for writing puppy,
and I am grateful for both.

# Getting Started

## Installation

Puppy is written in Python (it's right there in the name: "**p**ack **up**load in **py**thon").
So you'll need Python, version 3.11 or higher.
I'll leave you to the internet to figure out how to get python if you don't have it already.

And of course you need puppy itself.
Puppy is installed from its GitHub repository.
The most isolated way is to use `pipx`, which creates a run environment just for puppy without installing anything elsewhere.

```bash
pip install pipx      # or: brew install pipx  (macOS)
pipx ensurepath       # adds ~/.local/bin to PATH (once)
pipx install git+https://github.com/kcrca/puppy
```

Plain `pip install git+https://github.com/kcrca/puppy` works too, into whatever environment is active.

## Basic Puppy

Now let's get to your specific project.
The examples below use a texture pack, but mods and world saves work the same way, just with a different type set in the configuration,
as you'll see later.
CurseForge and PlanetMinecraft take all three; Modrinth takes packs and mods.

Suppose you have a pack called Neon, and you keep it in a git repository in your home directory.
(We're going to be using Unix paths here, but this works on Windows, too.)
So go to the top level of your repo and get started with puppy:

```bash
cd ~/neon
puppy init pack
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

First, there is `auth.yaml` which has the security information for the sites.
It is important that this not be checked into a public repo, so puppy requires it to be ignored by `.gitignore`.
Then there is `puppy.yaml` which has the global configuration for the work you want puppy to do.

You may find the ['examples'](examples/) folder useful, as it has an annotated [`puppy.yaml`](examples/puppy.yaml) file to give you some help.

### Authentication (`auth.yaml`)

To do its job, puppy needs to use your credentials on each site so it can work on your behalf.
The different sites need different authentication setups, some combination of cookies and/or access tokens.
All stored in `auth.yaml`.

Puppy can help you get the cookies.
It knows how to pull them from Firefox's saved state.
(Firefox is not required for anything else, you can use your favorite browser otherwise.)

**NOTE** that cookies expire, so you will need to get new cookies occassionally.
If you start getting "authentication expired" messages, that's the time.

Run Firefox and log in to Curseforge and PlanetMinecraft, then quit the browser.
Then run `puppy auth` and it will copy the relevant cookies into `auth.yaml`.
This will fill in the `cookie:` fields in `auth.yaml`.

Curseforge and Modrinth require access tokens.
You have to create these and put them in auth.yaml

For Curseforge,
go to the [CurseForge API Token page](https://legacy.curseforge.com/account/api-tokens).
and create a token (or choose an existing one if you prefer).
Copy that token, and paste it into `auth.yaml`, as in:

```
curseforge:
    token: <paste token here>
    cookie: <cookies from running "puppy auth">
```

The process is the same for Modrinth, except of course you use the 
[Modrinth API Token page](https://modrinth.com/settings/pats).
You need to give the token permissions to create, read, and write projects and versions.
In `auth.yaml`, you put the token here:

```
modrinth:
    token: <paste token here>
```

In short, each site needs:

* **CurseForge** — a token *and* a cookie.
* **Modrinth** — a token only.
* **Planet Minecraft** — a cookie only.

#### Getting Cookies Manually

If you can use `puppy auth`, you can skip this section.
But if for some reason you can't or won't use Firefox for `puppy auth`, you can get the cookies manually.
You have to get into the developer data sections, which is why we provide the automatic system.
But you can do it.

In your browser, turn on the developer tools window.

* **Chrome**: Click the three-dot menu in the top-right corner, select `More tools > Developer tools`.
* **Safari**: Enable `Settings > Advanced > Show features for web developers`, then use `Option + Command + I`.

In both cases, you will have an extra window open up that lets you do developer stuff.
This window will give you access to the cookies, under the `Application` tab in Chrome, or the `Storage` tab in Safari.
(If you're using a different browser, this might be a bit different, you'll have to figure it out.)

Let's start with Curseforge.
Go to the [CurseForge Author's page](https://authors.curseforge.com), and log in if you aren't already.
Find the `Cookies` tab in the developer tools window.
You need to copy out two cookies, `CobaltSession` and `AuthorsUser`.
Find each in the cookie list, and copy each one's value into your `auth.yaml`, 
which will then look something like this:

```
curseforge:
    cookie: CobaltSession=abcdef; AuthorsUser=ghifjk
    token: ...
```

Now log in to [Planet Minecraft](https://planetminecraft.com), then copy the name and value for the cookie `pmc_autologin` and put it in `auth.yaml`:

```
planetminecraft:
    cookie: pmc_autologin=lmnop
```

That's it, you're done, close the developer tools window.

### Project Settings (`puppy.yaml`)

The file `puppy.yaml` contains global settings for the pack and the sites. Let's go through the major fields:

* `sites`: List of sites to use; if absent, all three sites are used.
* `name`: Name of the pack.
* `handle`: Identifier for this project — lowercase, no spaces.
  Used as the default slug on sites that don't have an explicit `slug:` set, and as part of artifact file names.
* `version`: Current version of your pack.
* `summary`: The single-line summary of your pack.
* `license`: The license you are using for your pack.
* `minecraft`: Version of minecraft your pack is targeted for.
* `progress`: Percentage of possible textures that your pack covers
* `resolution`: Resolution of your pack, as a single integer (8, 16, 32, …)
* `links`: relevant external URLs for its own home page, donation sites for fans of your pack, etc.
  These are of the form: `home: https://neon-pack.org/`, `patreon: https://patreon.com/…` and so on.

Now we need to set up details for the various sites.

#### Setup for New Sites

If you want puppy to create a new project at a site, here is a simple `puppy.yaml` to start with:

```yaml
type: pack
handle: neon
version: 1.0
minecraft: 1.21.4
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

Then you run `puppy create` to create the project on each site.

This might be good if you're just getting started.
But you probably already have your pack, so let's fill this out.

The file `description.md` has a Markdown version of your description of your pack. 
For now let's just presume you want some text, images, and the like;
we will talk about expansion later.
Just create a `description.md`, which will be converted for each site to its native description language.

The pack zip and its icon are specified in the yaml.
`{{top}}` is a template variable for your repo's top level (`~/neon` here); these are covered under "Expansion".

```yaml
file: '{{top}}/neon_1.0.zip'
icon: '{{top}}/icon.png'
```

This uses the top-level file `neon_1.0.zip` (`~/neon/neon_1.0.zip`) for the artifact, and `icon.png` for the icon.
(You could instead copy them into the puppy directory.)

(`logo.png` and `banner.png` are *downloaded* by `pull` when a site provides them, but puppy does not upload logos or banners.)

### Image Gallery

You probably also want an image gallery.
That's pretty simple as well.
You can create an `images.yaml` file that looks something like this:

```yaml
source: '{{top}}/gallery'

images:
- name: Overview
  description: A general overview of the pack
  file: overview
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

`featured` marks the image as featured on sites that support it.
To place a specific gallery image inside your description text, reference it by name with the image variables described under "Expansion" (e.g. `{{ images.overview }}` or `{{ img("overview") }}`).

That's all you need for a normal setup:

```
~/neon/
└── puppy/                      ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore                  ← must contain auth.yaml for security reasons
    ├── puppy.yaml                  ← shared config
    ├── icon.png                    ← the pack icon
    ├── images.yaml                 ← the image library
    └── description.md              ← description of your pack
```

After you successfully create remote projects, some data from them is pulled back and placed in puppy.yaml.
So you will see many fields populated there from the site.

This is about as complex as most single projects need to be.
Later we will talk about multi-project setups (such as a family of related texture packs),
but they are mostly this same information spread out a bit.

## Per-site Settings

Per-site settings can be embedded in puppy.yaml under the site:

```yaml
modrinth:
  category:
    - blocks
    - environment
```

## Project Description

Typically you will want the description to be the same (or very similar) across all the sites.
For this, you can write your description in `description.md` in Markdown.
It will be expanded for each site into that site's description language (HTML for CurseForge, Markdown for Modrinth, and BBCode for Planet Minecraft).

It can be this simple, but you may want parts of it to vary from site to site — see "Expansion" below.

## Expansion

The description is central to your public face, and so it is central to puppy.
In its simplest form, this is just the `summary` property from `puppy.yaml` plus the contents of `description.md`. 
For basic text and images, this will be all you need.

But there may be cases where you want more than this.
As one example, each website has its own user feedback system.
So that section where you ask people to tell the system they think your stuff is cool requires site-specific customization.
That needs to be different for each system.

First, values inside yaml files and the text in `description.md` is run through Jinja2, which uses a pretty common template expansion syntax.
The most relevant here is that values inside `{{ }}` are treated specially.
They reference other values to build text dynamically.
So your `description.md` could have text like this:

```
Neon is currently at version {{ version }}.
```

The text `{{ version }}` will be replaced with the value of the `version` field from `puppy.yaml`.
So when you change that version, the description will always be up to date.

The full syntax has a lot of options, including conditional expansion.
You can [read more about it](https://jinja.palletsprojects.com/en/stable/templates/) if you want more control.

### Field Expansion

This expansion is also done for fields in the yaml files.
So if you want your pack's own version to be the same as the minecraft version, you could say:

```yaml
minecraft: "26.2"
version: "{{minecraft}}"
```

## Images

Your description may well inline one of your gallery images.
Each site has different URLs, but puppy helps you not worry about it.

```md
This image shows you how cool my crafting table is: {{ img('crafting-table') }}!
```

This will look in your `images.yaml` for an image named `crafting-table` (or the file `crafting-table.png`).

## Simple Path Names

We also define a few path-related variables to make it easier to name files.
For example, your `images.yaml` file can set the `source` value to `{{top}}/gallery`,
which will look for the gallery subdirectory of the top of your repo (`~/neon/gallery`).
Besides `top` (`~/neon`), the other values defined for this are `puppy` (`~/neon/puppy`) and `project` (same as `puppy` for a single pack, `~/neon/puppy/neon` for multi-pack).

## More on Expanding Values

For another example, when it comes to users showing you they like your work,
CF and Modrinth only allow them to show that by following your pack, but PMC gives many engagement options.
(Though CF is planning to add favorites, they say).

The way to handle this in puppy is to use parameter expansion.
Your `description.md` would have something like this:

```description.md
And if you like this pack, please {{ like }}!

```
Your `puppy.yaml` could have a segment that looks like this:

```puppy.yaml
like: 'follow this pack'

planetminecraft:
  like: 'give me a diamond, favorite this pack, and subscribe to my content'
```

This says that the default value for the `like` parameter is simple, but a specific override exists for PMC.

In the uploaded descriptions, the value of `like` will be replaced for each site with its particular brand of liking.
And the text will be good for every site.

You can use any yaml value in your expansion, including values inside other values.

If you prefer, you can create (say) a `planetminecraft` directory inside the `puppy` directory and put these values in a `puppy.yaml` in that directory.
Usually this is done when you also want a separate `images.yaml` file. or some other more complex setup.

## Including Files

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

# Setup for Existing Sites

If you already have a project at an existing site, you can pull the data from it to start your settings.
For each site you want to connect, add either the `slug` or the numeric `id` to the site block in `puppy.yaml`.
Puppy resolves the numeric ID automatically from the slug before pulling, so `slug` alone is usually enough.

**CurseForge** — The slug is the last part of your project's public URL:
for `https://www.curseforge.com/minecraft/texture-packs/neon-is-glowing`, the slug is `neon-is-glowing`.
Puppy resolves the numeric ID by searching the authors API (authenticated), which works even for projects pending approval, then falls back to scraping the public project page.
If your auth cookie is expired, puppy will say so — run `puppy auth --site cf` to fix it.
If resolution still fails, the slug is probably wrong, or you can set `curseforge.id` manually.
Find the numeric ID at [authors.curseforge.com/projects](https://authors.curseforge.com/projects) — it appears in the URL when you open your project there.

**Modrinth** — the slug is in the project URL:
`https://modrinth.com/resourcepack/neon-is-glowing` → slug is `neon-is-glowing`.

**Planet Minecraft** — the slug is the full URL slug including the trailing numeric ID:
`https://www.planetminecraft.com/texture-pack/neon-is-glowing-6911690` → slug is `neon-is-glowing-6911690`.
Puppy extracts the numeric ID from the suffix automatically.
You can also set `id: 6911690` directly if you prefer.

```yaml
curseforge:
  slug: neon-is-glowing        # numeric id resolved automatically via auth cookie

modrinth:
  slug: neon-is-glowing        # numeric id resolved automatically via API

planetminecraft:
  slug: neon-is-glowing-6911690   # numeric id extracted from slug suffix
  # or: id: 6911690
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
    ├── curseforge/                 ← CurseForge's site data
    │   ├── description.html        ← description used at CurseForge
    │   └── images/                 ← image gallery
    │       ├── images.yaml         ← image metadata
    │       ├── overview.png        ← an image gallery image
    │       └── mobs.png            ← an image gallery image
    ├── modrinth/                   ← Modrinth's site data
    │   ├── description.md          ← description used at Modrinth
    │   └── images/                 ← image gallery
    │       ├── images.yaml         ← image metadata
    │       ├── overview.png        ← an image gallery image
    │       └── mobs.png            ← an image gallery image
    └── planetminecraft/            ← Planet Minecraft's site data
        └── images/                 ← image gallery
            ├── images.yaml         ← image metadata
            ├── overview.png        ← an image gallery image
            └── mobs.png            ← an image gallery image
```

A few things to note:

* Puppy helps you present a unified view, but it can't figure out how create that from the separate sites' data.
  More on this below.
* Assets are downloaded only if they don't already exist locally.
* The icon isn't available from PMC.
* PMC doesn't have a way to get the current description, sigh.

The most important thing is that this is more complicated than you need when using puppy, except in some rare cases.
Your best move will be to merge this data to be simpler,
so it looks more like the simple setup above.
Specifically, puppy is simplest when you have one top-level `description.md` file.

* If you were manually making them all the same, just take the one from Modrinth and remove the others, and remove their directories.
  But read the expansion below for adapting it to different sites or situations.
* If you had different content, but don't care to continue that, merge any differences you want to preserve from the other versions.
* If you do want them different, just leave them as they are, but you'll need to get the bbcode version for Planet Minecraft and put it in `description.bbcode`.

If your existing Modrinth site is far from your best description, this will take more work.
You can find HTML to markdown and BBCode to markdown converters that could be helpful to get a markdown file to get you started.

For most people, who want all the sites for a project to be the same, you can end up with this much simpler tree:

```
~/neon/
└── puppy/                      ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore                  ← must contain auth.yaml for security reasons
    ├── puppy.yaml                  ← shared config
    ├── icon.png                    ← the pack icon
    ├── description.md              ← description used everywhere
    └── images/                     ← image gallery used everywhere
        ├── images.yaml             ← image metadata
        ├── overview.png            ← an image gallery image
        └── mobs.png                ← an image gallery image
```

And if your images are stored elsewhere in your repo, you only need an `images.yaml` that points there, rather than a `images` directory at all.
So many projects will look even simpler:

```
~/neon/
└── puppy/                      ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore                  ← must contain auth.yaml for security reasons
    ├── puppy.yaml                  ← shared config
    ├── icon.png                    ← the pack icon
    ├── description.md              ← description used everywhere
    └── images.yaml                 ← image gallery used everywhere
```

This is how most projects will look.

### Publishing Your Pack (`push`)

Once your `puppy.yaml`, description, icon, and gallery are in place, one command publishes everything to every configured site:

```bash
puppy push
```

This is the command you'll use most: it updates the description, metadata, icon, pack, and gallery on each site.
By default puppy uploads only what changed since the last push (tracked in `puppy/hashes.yaml`), so re-running it is cheap.

**Preview before you publish.** `push` writes to live, public sites. Before your first real push — or any time you're unsure — do a dry run:

```bash
puppy push -n
```

This runs the whole pipeline without contacting the sites and opens a local HTML page showing exactly what each site would receive.
Nothing is uploaded until you run `puppy push` without `-n`.

You *really* should use this before doing the actual push.

# Multiple Packs/Projects

There are several ways to make your description customized to different sites and other things.
But before we get to that, we need to talk about how you can have multiple pack projects generated from a single repo.

Even if you aren't supporting multiple packs it fits into expansion, so it's worth knowing.
This isn't very complex, so you can certainly handle it.

With one pack, the puppy home (`~/neon/puppy`) is also the *project home.*
With multiple packs, the puppy home holds values that are shared across all the projects,
and each project has a subdirectory that is its own project home, for its individual values.
During expansion, then, a distinction is made between puppy home and project home.

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
    │   ├── puppy.yaml              ← Neon's config
    │   └── images/                     ← Neon's image gallery
    │       ├── images.yaml                 ← Neon's image metadata
    │       ├── overview.png                ← a Neon image gallery image
    │       └── mobs.png                    ← a Neon image gallery image
    ├── dark/                       ← Dark's project home
    │   ├── puppy.yaml              ← Dark's config
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

Again, for a single pack, the puppy home _is_ the project home for the one project you've got.

## Information Priority

When puppy is looking for information of any kind (besides the stuff in `auth.yaml`), it looks for it in this order:

1. The project's site data (Neon's data for Modrinth)
2. The project's data (Neon's data)
3. The site's data (Modrinth's data)
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
    │   ├── puppy.yaml              ← Neon's config
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
    │   ├── puppy.yaml              ← Dark's config
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

Of course, once you have this kind of potential complexity, you want to know whether puppy is generating what you want it to.
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
puppy [-h] [-n] [-q] [-d PATH] [-s SITE[,SITE]] [-c CATEGORIES] [--rehash] [--no-open] [{push,pull,init,auth,create}] [project ...]
```

The `-c/--content` flag names content categories — `file` (`f`), `images` (`i`, gallery + icon), and `data` (`d`, description + metadata) — and works the same way for both `push` and `pull`.
Combine them as `-c fid` or `--content file,images`, or use `-c all`.

Puppy can be run in the top level directory (`~/neon`), the puppy directory (`~/neon/puppy`) or any subdirectory of the puppy directory.
The `-d PATH` option lets you run it from anywhere, where `PATH` is any of these directories.

## Global Options

* `-h`, `--help`: show help.
* `-q`, `--quiet`: Suppress progress output (progress is shown by default).
* `-d`, `--dir PATH`: Project directory (default: current working directory).
* `-s`, `--site SITENAME`: Limit action to one or more sites (comma-separated). You can use the abbreviations "cf", "mr", and "pmc" for sites.

## Subcommands

* **init `<type>`**: Set up the puppy directory for the given project type (`pack`, `mod`, or `world`). Creates `puppy.yaml` with skeleton entries for the sites that support that type and the appropriate neutral fields.
* **auth**: Fetch authorization cookies from a Firefox session.
* **create**: Create the project on the site(s) from the slugs and settings in `puppy.yaml`, then pull the new projects' data back into your config.
* **pull**: Pull data from the site(s). This will not overwrite existing images, but it will merge new data into yaml files.
    * `-c images`, `--content images`: Also pull logo, icon, banner, and image gallery.
      (`-c file` is not valid for pull — there is no file to download.)
* **push**: Push description, metadata, icon, gallery, and (when current) the artifact file. (Logos and banners are not uploaded.)
  By default (`use_hashes: true` in `puppy.yaml`) puppy uploads only what changed since the last push, tracked by content hashes stored in `puppy/hashes.yaml`.
    * `-c`, `--content CATEGORIES`: Force-upload the named categories regardless of the hash check.
      Other categories still upload on this run if their hash changed.
      When `use_hashes: false`, hashing is off and `-c` is the *only* thing that uploads (default `data`).
    * `--rehash`: Record the current content as already-uploaded — write `hashes.yaml` for the in-scope categories (`-c`, else all) without uploading anything.
      Handy after a fresh checkout where the sites are already current, or after editing content directly on a site, so the next push does not re-upload everything.
    * `-n`, `--dry-run`: Create a pre-check HTML page, printing the URL and opening it.
    * `--no-open`: With `-n`, suppresses opening the file.

### Hashing

The field `use_hashes` says whether to use hashes to avoid uploading files that seem to be unchanged. 
This is a purely local database, which works fine if you only run puppy from one machine, or one repo that has hashes.yaml in it and is kept up to date.
But otherwise it doesn't, which is why you can disable it.

A small detail: Modrinth tells puppy the hash code value it currently has, which puppy believes over the value in `hashes.yaml`.

## Projects

If you have multiple projects, you can list specific ones on the command line after the subcommand, such as `puppy push neon` to only work with the `neon` project.

# `puppy.yaml` Properties

Here are the values that puppy looks at in the `puppy.yaml` files.
Remember that the yaml values used during runs are created by merging any existing relevant `puppy.yaml` files.
So when these are in the top level `puppy.yaml`, they can be overridden in lower levels.

## Identity and Behavior

| Field             | Meaning |
|-------------------|---------|
| `name`            | Display name. Title-cased if all-lowercase input (`neon` → `Neon`). Derived from directory name if absent; written back automatically. |
| `handle`          | Internal slug. Lowercase alphanumeric only. Derived from `name` or directory if absent; written back automatically. |
| `slug`            | Default slug for all sites. Per-site `slug` overrides this. |
| `type`            | Project type: `pack`, `mod`, or `world`. Required. Determines which sites are active and which fields apply. |
| `version`         | Current project version, used by `push`. |
| `summary`         | One-line description shown in site search results. |
| `github`          | Source repository URL. Set automatically from `links.source`; used for CF source link and Modrinth `source_url`/`issues_url`. Can be set directly to override. |
| `use_hashes`      | Whether `push` skips uploads whose content is unchanged since the last push, tracked in `puppy/hashes.yaml`. Default `true`. When `false`, push uploads only the categories named with `-u` Default: `true`. |
| `projects`        | List of project subdirectory names. Puppy iterates these in order. |
| `linked_projects` | Map of external projects (outside this puppy home) to inject into the Jinja `projects.*` context. Each entry has per-site sub-objects. |
| `md_html_tags`    | List of HTML tags to protect during Markdown conversion and map to site equivalents (e.g. `<u>` → `[u]` for PMC). Default `['u']`. |   #</u> to close the 'u' tag for vi's syntax highlighting

## Neutral Metadata (expand to all sites automatically)

These values are used with whichever sites they make sense, and often translated.
For example, `resolution` matters for all packs, but for no other project types.
So in a pack project it will be provided to every site, and in other projects it generates a warning.
But different sites represent resolution differently, and puppy translates it to each.

Values that have meaning only to some of the sites are simply ignored for the sites that don't support them.
For example, `progress` is currently only used by one site (Planet Minecraft).
But if someday one of the other sites were to support it, puppy would start to send it to that site.
The principle is that these values are site-independent in their meaning (the project isn't 50% at one site at 75% at another),
so they should not be set for individual sites as long as puppy can understand how to use them wherever they are relevant.

| Field                   | Types | Meaning |
|-------------------------|-------|---------|
| `bedrock`               | all   | Whether this is a bedrock project. |
| `icon`                  | all   | Path of the icon PNG. Discovered automatically (single `.png` in project dir, excluding `banner.png` and `logo.png`) if absent. Must be square. |
| `file`                  | all   | Path of the zip artifact. Discovered automatically (single `.zip` in project dir) if absent. |
| `optifine`              | pack  | `true`/`false` — whether the pack requires OptiFine. Default `false`. |
| `video`                 | all   | YouTube video ID for an associated video. |
| `after_push`            | all   | Message printed after all projects are pushed. Useful to remind you of something. When set inside a site block, prints only when that site is active, prefixed with the site label. |
| `minecraft`             | all   | Game version for artifact upload. String → exact version; dict → passed as-is. Required for `push -c file` unless `versions` is set. |
| `versions`              | all   | Explicit Minecraft version list. Alternative to `minecraft`. |
| `loaders`               | mod   | List of mod loaders (e.g. `[fabric, forge]`). Valid for `mod` only. Sets Modrinth `loaders` and resolves to CF game version IDs. |
| `client_side`           | mod   | `required`, `optional`, or `unsupported`. Valid for `mod` only. Sets Modrinth `client_side`. |
| `server_side`           | mod   | `required`, `optional`, or `unsupported`. Valid for `mod` only. Sets Modrinth `server_side`. |
| `resolution`            | pack  | Pack resolution in pixels (e.g. `16`). Sets the CF primary category (`16x`), Modrinth `resolution`, and PMC `resolution`/`tags`. |
| `progress`              | all   | Completion percentage 0–100. Sets PMC `progress`. Ignored by CF and Modrinth. |
| `license`               | all   | SPDX identifier (e.g. `CC-BY-4.0`). Sets CF `license` (last hyphen → space) and Modrinth `license` unchanged. Ignored by PMC. |
| `changelog`             | all   | Release notes text included in version file uploads (`push -c file`) on all sites. |
| `socials.discord`       | all   | Discord server URL. Sets Modrinth `discord_url` and CF `socials.discord`. Per-site `modrinth.discord` and `curseforge.socials.discord` override this. |
| `links.home`            | all   | Project home page URL. Sets CF `socials.website` and PMC `website.link`. |
| `links.source`          | all   | Source repository URL. Sets top-level `github` (used for CF and Modrinth). |
| `links.issues`          | all   | Issue tracker URL. Sets Modrinth `issues_url`. |
| `links.wiki`            | all   | Wiki URL. Sets Modrinth `wiki_url`. |
| `links.patreon`         | all   | Patreon donation URL. CF: first donation key wins as `{type, value}`. Modrinth: `donation.patreon`. |
| `links.kofi`            | all   | Ko-fi donation URL. Same expansion as `patreon`. |
| `links.paypal`          | all   | PayPal donation URL. Same expansion. |
| `links.buyMeACoffee`    | all   | Buy Me a Coffee URL. Same expansion. |
| `links.github_sponsors` | all   | GitHub Sponsors URL. CF: `type: github`. Modrinth: `donation.github`. |
| `links.other`           | all   | Catch-all donation URL. Same expansion. |

The donation-related `links` have some interesting handling.
Planet Minecraft doesn't use them. 
CurseForge only uses one donation link, so the first one listed is used there.
Modrinth uses all the listed ones.

If you want all the details about translating the neutral fields into their actual site-specific values, you can find them in the puppy specification.
Generally speaking, with the above exception, it does what you would expect.

## CurseForge block (`curseforge:`)

| Field          | Meaning |
|----------------|---------|
| `id`           | CurseForge project ID. Written by `pull`/`create`. Resolved from `slug` automatically if absent. |
| `slug`         | Project slug on CurseForge. |
| `category`     | CurseForge category. A string or a list. For packs the `resolution` tier is always the primary category, and anything you put in `category` becomes an additional subcategory (e.g. `category: Data Packs` → primary `16x`, subcategory `Data Packs`). For mods/worlds (no `resolution`) the first entry is the primary category and the rest are subcategories. |
| `mainCategory` | Legacy fallback for the primary category; used only when `category` is unset. Prefer `category`. |
| `license`      | License string (e.g. `CC-BY 4.0`). Set by `license`; override here. |
| `donation`     | `{type: platform, value: url}`. Set from the first `links.*` donation link; override here. |
| `socials`      | Map of social platform names → URLs. `website` set from `links.home`; others (discord, patreon, github, etc.) set directly. |

## Modrinth block (`modrinth:`)

| Field        | Meaning |
|--------------|---------|
| `id`         | Modrinth project ID. Written by `pull`/`create`. Resolved from `slug` automatically if absent. |
| `slug`       | Project slug on Modrinth. |
| `category`   | A Modrinth content category, or a list of them (e.g. `vanilla-like`). |
| `resolution` | Resolution tier (e.g. `16`). Auto-set from the neutral `resolution`; override here. |
| `license`    | SPDX license. Set by `license`; override here. |
| `donation`   | Map of platform name → URL (`patreon`, `kofi`, `paypal`, `buyMeACoffee`, `github`, `other`). Set from `links.*`; override here. |
| `discord`    | Discord server URL. |

## Planet Minecraft block (`planetminecraft:`)

| Field           | Meaning |
|-----------------|---------|
| `id`            | PMC project ID. Written by `pull`/`create`. Resolved from `slug` automatically if the slug ends in `-{id}` (e.g. `name-6911690`), or by fetching the public project page. |
| `slug`          | Project slug on PMC. |
| `resolution`    | Resolution integer. Set by `resolution`; override here. |
| `progress`      | Completion percentage 0–100. Set by `progress`; override here. |
| `tags`          | List of tag strings (e.g. `['16x', '16x16']`). Neutral `resolution` appends to this; add others here. |
| `category`      | PMC category string. |
| `modifies`      | Map of modification target → `true`/`false`. |
| `download`      | If set, skips uploading the file to PMC and uses this URL as the primary download link instead. Accepts `curseforge` or `modrinth` as shorthands. If not set, `push -c file` uploads the file to PMC. |
| `alt_download`  | An extra external link shown on PMC alongside the primary download. When `download:` is set, fills the second link slot. When `download:` is not set (file upload to PMC), fills the first link slot. |
| `website.link`  | Website URL. Set from `links.home`; override here. |
| `website.title` | Website display title shown alongside the link. |
| `credit`        | Credit string displayed on the PMC project page. |
