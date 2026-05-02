# Rules for this project

## Commits
- NEVER run `git commit` without first proposing the commit message and receiving explicit approval ("go" or similar). This applies every time, with no exceptions.
- Commit messages are a single line. No "Co-Authored-By" or any other trailers.
- Always run `.venv/bin/pytest` (full suite) and confirm all unit tests pass before proposing a commit.
- Always `git add` relevant files explicitly — never `git add -A` or `git add .`.

## Python style
- Single quotes everywhere. Double quotes only when the string contains a single quote.
- imports only at top of file

## General behaviour
- Approval of one item in a sequence does not imply approval of the next. Wait for explicit confirmation each time.
- If an instruction seems like a bad idea, say so before acting — one or two sentences, then ask.
- Don't be obsequious, don't compliment, be succinct about describing things not asked

## Markdown style
- On our own markdown files, each sentence starts on a new line
