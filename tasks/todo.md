# Tasks

## Plan

- [x] Review repository structure, CLI entrypoints, core modules, and tests
- [x] Identify the real public-facing scope of the project from code instead of old README text
- [x] Rewrite the root `README.md` as the primary English project document
- [x] Add a Chinese project introduction document at `docs/README.zh-CN.md`
- [x] Record validation results and repository-state caveats for public release

## Review

- The old README contained outdated path assumptions such as `cd agent-harness` and only described a subset of the implemented command surface.
- The rewritten documentation now reflects the actual command groups and module structure present in the repository.
- The docs explicitly describe the authentication model (`IM-TOKEN`), session persistence behavior, REPL support, and the difference between source layout and a fully packaged public release.
- Test execution was attempted, but the active environment does not have `pytest` installed, so verification in this pass is limited to code inspection and command-surface consistency checks.
