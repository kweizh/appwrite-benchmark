# Appwrite CLI: Initialize Project and Push a Collection

## Background
Your team wants to drive Appwrite resource setup from a shell pipeline so that every CI run can reproducibly create and tear down a database with a collection. You will use the Appwrite CLI (`appwrite-cli`, the official `appwrite` command) in non-interactive mode to authenticate against an Appwrite Cloud project, write a project configuration file declaring a database and a collection, and push the schema to Appwrite.

The CLI must be driven without any interactive prompts and without using the language SDKs directly to create resources.

## Requirements
- Place all your project files under `/home/user/myproject/`.
- Write a runnable shell script `/home/user/myproject/run.sh` that, when executed with `bash`, performs the full workflow end-to-end.
- Read `ZEALT_RUN_ID`, `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, and `APPWRITE_API_KEY` from the environment.
- Use the Appwrite CLI (`appwrite`) — NOT the Appwrite SDK — to:
  1. Switch the CLI to non-interactive mode using the project ID, endpoint, and API key.
  2. Create / write an `appwrite.config.json` (or equivalent multi-file Appwrite project config) that declares:
     - a database with id `cli-${ZEALT_RUN_ID}` and name `cli-${ZEALT_RUN_ID}` (or any human-readable name).
     - a single collection / table inside that database with id `notes-${ZEALT_RUN_ID}` and one string attribute / varchar column `body` (size 255, not required).
  3. Push the declared resources to Appwrite non-interactively using the CLI's push command (e.g. `appwrite push collections --all --force`, or the modern `appwrite push tables --all --force` equivalent, depending on CLI version).
- After the push, the script's very last line on stdout MUST be a single JSON object with the database id and collection id, exactly in the form: `{"databaseId":"cli-${ZEALT_RUN_ID}","collectionId":"notes-${ZEALT_RUN_ID}"}`.

## Implementation Hints
- Read the run id from `ZEALT_RUN_ID` and use it to suffix the database and collection ids so the task is safe to retry.
- The CLI is already on PATH (`appwrite --version`). Configure it with `appwrite client --endpoint ... --project-id ... --key ...` to enter non-interactive mode.
- The `appwrite.config.json` schema supports both the legacy `databases` + `collections` arrays and the newer `tablesDB` + `tables` arrays; either is acceptable as long as the resulting Appwrite database and collection have the required ids and attribute.
- Use the CLI's non-interactive push flags (`--all --force`) to skip prompts.
- For the final stdout line, you can either echo a literal JSON object based on the config you just wrote, or read the ids back via `appwrite databases list` / `appwrite tables-db list` and `jq`.
- Make sure `run.sh` exits with status 0 on success.

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: `bash /home/user/myproject/run.sh`
- The script must use the Appwrite CLI (`appwrite ...`) to push the database/collection. Do not call the Appwrite SDK directly to create the resources.
- After the script finishes:
  - A database with id `cli-${ZEALT_RUN_ID}` exists in the target Appwrite project.
  - That database contains a collection (or table) with id `notes-${ZEALT_RUN_ID}`.
  - The collection has an attribute (or column) named `body` of string/varchar type.
- The very last line of the script's stdout is a JSON object exactly in the form:
  ```json
  {"databaseId":"cli-<ZEALT_RUN_ID>","collectionId":"notes-<ZEALT_RUN_ID>"}
  ```
  where `<ZEALT_RUN_ID>` is substituted with the actual run id.
- The script exits with status 0.

