# PackUploader Feature Requests and Bug Reports

## Feature Requests

### PMC download link override
PU hardcodes the PMC alternative download link to the Modrinth or CurseForge URL.
There is no way to supply a custom URL (e.g. a direct zip download link).
When neither Modrinth nor CurseForge slug is available, the link becomes
`https://modrinth.com/resourcepack/null`.
Request: support a configurable `download_url` field that overrides the computed link.

### Set PMC title
The project name is hardcoded to be the title for PMC projects. But it is
common for it to be something like: '{{name}}: {{summary}}'. Being able
to set the title for PMC would be nice.

### Create error message should name the project
When `create.js` fails, the error does not identify which project was being created.
Request: include the project name/id in the error output.

## Bugs

### PMC: null download link when no Modrinth/CF slug
When a project has no Modrinth or CurseForge ID, `createForm` falls through to
`https://modrinth.com/resourcepack/${project.modrinth.slug}` where `slug` is null,
producing the literal URL `https://modrinth.com/resourcepack/null`.
File: `src/planetminecraft.js`, line ~185.

### Image download triggers OS save to ~/Downloads instead of being captured
File: `src/puppeteer.js` `getBuffer()`
When the server sends `Content-Disposition: attachment`, Chromium triggers a file
download rather than a navigable response.
`page.goto()` gets `ERR_ABORTED`, caught and swallowed (~line 65).
`buffer` remains null, `getBuffer` throws "no response body captured", and the file
lands in ~/Downloads instead of `projects/{pack}/images/`.
Fix: intercept `page.on('download')` instead of relying on response capture.

### Image captions not imported — description duplicates name
File: `src/planetminecraft.js` import(), line ~527
Caption parsed as `e.dataset.caption?.split(" - ").slice(1).join(" - ")`, expecting
"Title - Description" format.
If PMC captions don't use that separator, description falls back to the title.

### CF authors portal compatibility — icon upload returns 403
`createProject` uploads icon to `https://authors.curseforge.com/_api/projects/game/432/upload-avatar`
using only a `cookie` header.
Since CF launched their new authors portal, this endpoint returns 403.
Possibly requires an additional header (CSRF token or similar).
File: `src/curseforge.js`, line ~72.
