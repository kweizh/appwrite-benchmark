# Appwrite Databases: One-to-Many Relationship Between Collections

## Background
Appwrite Databases support **relationships** between collections so related documents can be linked, queried together, and cascaded on delete. Your team wants to model a classic blogging schema in which a single **author** can write **many posts**, with a two-way relationship so it is easy to navigate from an author to all of their posts and from a post back to its author.

You will write a Node.js script (using the official `node-appwrite` Server SDK) that creates this schema against a real Appwrite project. The Appwrite endpoint, project ID, and API key are provided via environment variables. To make the task safe to run concurrently, every resource must be scoped with the value of `ZEALT_RUN_ID`.

## Requirements
- Create a new **database** whose ID is `blog_${run-id}` (use the same value for the database name) via `databases.create`.
- Create two **collections** inside that database:
  - `authors` collection (ID and name both `authors`).
  - `posts` collection (ID and name both `posts`).
- Add the following string **attributes** with `databases.createStringAttribute`:
  - `authors.name`: size `255`, required `true`.
  - `posts.title`: size `255`, required `true`.
  - `posts.body`: size `10000`, required `true`.
- Add a **two-way one-to-many relationship** from `authors` to `posts` using `databases.createRelationshipAttribute`:
  - relationship type: `RelationshipType.OneToMany`.
  - `twoWay`: `true`.
  - parent-side attribute key (on `authors`): `posts`.
  - child-side attribute key (on `posts`, the `twoWayKey`): `author`.
  - `onDelete`: `RelationMutate.SetNull` (deleting an author keeps the posts but nulls out their `author` reference).
- Wait until every attribute, including the relationship attribute, reaches `status === "available"` before exiting (otherwise subsequent verification will race).
- The script must NOT model the relation with plain string fields — the relationship MUST be created with `databases.createRelationshipAttribute`.

## Implementation Hints
- Install/use the `node-appwrite` Server SDK. The SDK exposes `Client`, `Databases`, `ID`, `RelationshipType`, and `RelationMutate`.
- Read `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, and `ZEALT_RUN_ID` from environment variables.
- After issuing the `createRelationshipAttribute` request, poll `databases.getAttribute(databaseId, 'authors', 'posts')` (and/or the child-side `databases.getAttribute(databaseId, 'posts', 'author')`) until `status === 'available'`. The API call returns `202 Accepted` and the attribute is built asynchronously.
- Refer to the Appwrite docs:
  - https://appwrite.io/docs/products/databases/relationships
  - https://appwrite.io/docs/references/cloud/server-nodejs/databases#createRelationshipAttribute

## Acceptance Criteria
- Project path: /home/user/myproject
- Entry point: a Node.js script that can be executed by the verifier. The verifier will invoke it with `node /home/user/myproject/index.js`.
- The script reads `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, and `ZEALT_RUN_ID` from environment variables.
- The **last non-empty line** of stdout MUST be a single JSON object with exactly the keys `databaseId`, `authorsCollectionId`, and `postsCollectionId`, e.g.:
  ```json
  {"databaseId":"blog_zr-abc123","authorsCollectionId":"authors","postsCollectionId":"posts"}
  ```
- When the script exits successfully, the following must be true in the configured Appwrite project (verified via the Server SDK / REST API):
  - A database with the printed `databaseId` exists.
  - A collection `authorsCollectionId` exists inside that database with a required string attribute `name` (size 255).
  - A collection `postsCollectionId` exists inside that database with required string attributes `title` (size 255) and `body` (size 10000).
  - The `authors` collection has a **relationship attribute** with key `posts` whose `relationType` is `oneToMany`, `twoWay` is `true`, and `twoWayKey` is `author`, with `onDelete` equal to `setNull` and `status` equal to `available`.
  - The `posts` collection has the corresponding **child-side relationship attribute** with key `author`, `relationType` `oneToMany`, `twoWay` `true`, `twoWayKey` `posts`, and `status` `available`.
  - The relationship MUST be created via `databases.createRelationshipAttribute`; modeling the relation through plain string foreign-key fields is NOT acceptable.

