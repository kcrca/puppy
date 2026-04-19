# **Puppy Design Specification (Final Production Blueprint)**

## **1. Design Principles**
* **User-Centric Simplicity:** Defaults favor the user. Puppy acts on all projects and sites unless filtered.
* **Worker-First Execution:** Puppy acts as a thin management layer for `PackUpdate` (pu). It handles staging, factory-resetting the worker, and dependency checks automatically.
* **Implicit Discovery:** Asset discovery (icons, zips, fragments) is preferred over manual path mapping.
* **Integrated Versioning:** All data and harvested IDs reside in the project source directory.
* **Markdown-First:** Content is written in Markdown. Site-specific native files (`.html`, `.bbcode`) act as overrides.
* **Non-Interactive (Fail-Fast):** No prompts. Errors (missing IDs, mismatched versions, security flaws) result in an immediate exit.

## **2. Core Identity & Naming**
* **`pack` (Internal Slug):** The lowercase version of the parent directory name (e.g., `NeonGlow` $\to$ `neonglow`).
* **`name` (Display Name):** * Preserves casing if uppercase letters exist (`NeonGlow`).
    * Converts to Title Case if strictly lowercase (`clean` $\to$ `Clean`).
* **Overrides:** Explicit `name:` or `pack:` keys in any `puppy.yaml` override these derivations.

## **3. Directory Architecture**

For a basic pack named "neon", the structure for a pack (or other project) that is being published via puppy is:

* **Global Root:** `~/neon/`
* **Puppy Root:** `~/neon/puppy/`
* **Security & Auth:** `~/neon/puppy/auth.yaml`
* **Project Root:** `~/neon/puppy/[ProjectName]/`
* **Project Source:** `~/neon/puppy/[ProjectName]/puppy/`
* **Worker Directory:** `~/PackUpdate` (The staging area).
* **Debug Output:** `~/puppy/[ProjectName]/puppy/debug/` (Used for `--dry-run`).

## **4. CLI & Actions**
`puppy [options] [action]`

### **4.1 Actions**
* **`sync` (Default):** Updates metadata, summaries, descriptions, and icons.
* **`publish`:** Performs a full `sync` plus artifact upload. Requires `--version`.
* **`create`:** Registers projects on sites with missing IDs. **Requires `--create` flag.**
* **`import`:** Pulls live site data and reverse-migrates to local `.md` and `.yaml` files.

### **4.2 Options & Flags**
* **`-n/--dry-run`:** Executes the entire pipeline (merging YAML, resolving fragments, translating text) and outputs the final payloads to the `debug/` folder *without* executing the worker or hitting APIs.
* **`-v` / `-vv`:** High-level progress (`-v`) or raw worker stdout/stderr (`-vv`).
* **`-d/--dir [path]`:** Sets project directory. Defaults to CWD.
* **`-s/--site [sitename]`:** Limits action to a specific site (e.g., `modrinth`).
* **`-V/--version [string]`:** Required for `publish`. Matches via `{{project}}*{{version}}.zip`.

## **5. Cascading Configuration & Discovery**

### **5.0 auth.yaml**
auth.yaml should never be committed to any repo. puppy will exit with an error if auth.yaml doesn't
exist, or if it is not in puppy/.gitignore. (No, we won't check the top level of the repo.) We will
add support for other VCS systems as required.

### **5.1 Config Merge (Additive Synthesis)**
1. Global Defaults (`~/puppy/puppy.yaml`)
2. Global Site Overrides (`~/puppy/[sitename]/puppy.yaml`)
3. Project Root (`~/puppy/[ProjectName]/puppy/puppy.yaml`)
4. Project Site Overrides (`~/puppy/[ProjectName]/puppy/[sitename]/puppy.yaml`)
*(Dictionaries merge additively; scalars overwrite).*

### **5.2 Content Discovery (The Cascade)**
For fragments (e.g., `{{ header }}`), Puppy searches:
1. YAML `strings` block.
2. Project Site File.
3. Project General File.
4. Global Site File.
5. Global General File.
* **Extension Priority:** CF/Modrinth (`.html` $\to$ `.md`); PMC (`.bbcode` $\to$ `.md`).

### **5.3 Path Resolution Rules**
* **Internal Files:** Files inside the `puppy/` directories follow the Cascading Discovery logic.
* **External Files:** Paths explicitly referencing locations outside `puppy/` (e.g., `../assets/banner.png` or `/var/www/packs/`) are treated as **literal**. Puppy does not guess extensions or search hierarchies for external references.

## **6. Operational Logic**

### **6.1 Security & Auth Protocol**
* Puppy looks for `~/puppy/auth.yaml` to source API keys.
* **Hard Block:** On startup, Puppy checks `~/puppy/.gitignore`. If `auth.yaml` is not explicitly listed in the ignore file, Puppy throws a fatal error and refuses to run.

### **6.2 Pre-Flight & Worker Hygiene**
* **Dependency Check:** Verifies `git`, `node`, and `npm` exist in the shell environment.
* **Worker Prep:** *Before* populating `~/PackUpdate` with project files, Puppy runs `git reset --hard HEAD` and `git clean -fd` to ensure absolute cleanliness.
* **NPM Install:** If `~/PackUpdate/node_modules` is missing, Puppy automatically runs `npm install` before executing the `pu` script.

### **6.3 Multi-Project Iteration**
If a command (e.g., `puppy sync`) is executed from the global root (`~/puppy/`) without a `--dir` flag, Puppy treats it as a batch operation, iterating through every valid subdirectory and executing the action sequentially.

### **6.4 State Harvesting**
Harvested IDs and Slugs (from `create` or `import`) are automatically written back to the root project `puppy.yaml`.

### **6.5 Artifact Match**
Strict boundary check ensures `1.2` does not accidentally capture `1.2.4`.

### **6.6 Translation & Shielding**
* **Cross-Linking:** Puppy pre-scans all projects, allowing `{{ projects.[other_pack].url }}` to resolve to site-correct links.
* **Shielding:** `valid_tags` (default `['u']`) are protected from Markdown translation and mapped to target-site equivalents (e.g., `<u>` $\to$ `[u]` for PMC). Users own the risk of unsupported HTML tags.
* **Exclusions:** Puppy respects a `.puppyignore` file in the project root to prevent bulky/irrelevant files (e.g., `.psd`, videos) from being staged into `~/PackUpdate`, though best practice dictates keeping the source folder clean natively.

--- 

I believe this completely solidifies the rulebook. Everything from how it reads a file, to how it ensures the worker doesn't leak state, to how it stops you from accidentally committing your API keys to GitHub is codified here.
