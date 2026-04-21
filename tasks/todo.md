# Tasks

## Plan

- [x] Review the current repository structure, entrypoints, and command registrations
- [x] Verify the real authentication model from code and confirm `token` / `api key` behavior
- [x] Rewrite the root `README.md` with more formal public-facing wording
- [x] Replace outdated install/run instructions with command information that matches the source tree
- [x] Validate the final README against code and record the verification result

## Review

- Rewrote `README.md` into a more formal public-facing document focused on project scope, authentication, configuration, command groups, and representative examples.
- Removed the incorrect `pip install -e .` guidance and documented the actual repository caveat: this checkout does not currently include standalone packaging metadata.
- Confirmed from source that authentication supports either `AIDEE_TOKEN` (`IM-TOKEN`) or `AIDEE_API_KEY` (`X-Api-Key`) for normal usage; both are not required.
- Corrected command examples to match the registered Click interface, including positional device commands such as `device unbind DEVICE_ID` and `device get DEVICE_ID`.
- Verified the command surface by running help commands through a temporary `PYTHONPATH` package shim:
  - `python3 -m cli_anything.aidee.aidee_cli --help`
  - `python3 -m cli_anything.aidee.aidee_cli device --help`
  - `python3 -m cli_anything.aidee.aidee_cli redemption --help`
