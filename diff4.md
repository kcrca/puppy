# README Review — Fourth Pass

## Errors

**Line 224: "The logo is not pulled down from any site"**
Still wrong — `logo.png` and `banner.png` are now harvested on import, which the post-import tree on lines 209–210 correctly shows.
This sentence should either be removed or replaced with what *is* true: that logo and banner are harvested the same as the icon.

**Line 226: "whichever it finds first"**
Still the ambiguous phrasing.

**`[PROJECT] [...]` in usage syntax (line 499)**
Still uppercase; still not described in Subcommands.

**`banner` missing from "Basic Puppy" prose (line 122)**
"The pack itself, its icon, and its logo can be specified in the yaml" — `banner` is still absent, and the yaml example below it shows only `zip`, `logo`, and `icon`.

---

## Spelling / Grammar (new)

**Line 375: "run though Jinja2"** — "though" should be "through".

**Line 457: `` '/signature`) `` ** — the closing backtick inside the string literal should be a single quote: `` '/signature') ``; also a double space before `top`.

**Line 458: "the the invocation"** — doubled "the".

---

## Ambiguous

**Line 247: "this fits into expansion"**
"this" is still vague — it's unclear whether "this" refers to the multi-pack structure or something else.
