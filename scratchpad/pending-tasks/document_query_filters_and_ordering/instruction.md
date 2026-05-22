# Appwrite Databases: Query, Filter, Order, Limit, and Select Documents

## Background
Appwrite Databases lets you filter, sort, paginate, and project documents using the `Query` helper class together with `databases.listDocuments`. In this task you will query an existing collection of products and return only the records that satisfy a set of business rules, formatted as JSON.

The verifier has pre-seeded a database named `products_${run-id}` containing a single collection (id `products`) with 20 documents. Each document has the attributes:
- `name` (string)
- `category` (string) — one of `electronics`, `books`, `clothing`
- `price` (float) — between 10 and 500
- `stock` (integer)

The concrete database id, collection id, and `ZEALT_RUN_ID` are made available to your script via environment variables AND via a small JSON file at `/home/user/myproject/.seed.json`:

```json
{
  "database_id": "products_${run-id}",
  "collection_id": "products"
}
```

## Requirements
Write a Node.js program at `/home/user/myproject/index.js` that uses the official `node-appwrite` Server SDK to query the seeded collection and print the matching documents.

Your query MUST be expressed entirely through `Query` helpers passed to `databases.listDocuments`. It must:
- Filter `category` equal to `"electronics"` using `Query.equal`.
- Filter `price` greater than or equal to `100` using `Query.greaterThanEqual`.
- Order the results by `price` in DESCENDING order using `Query.orderDesc`.
- Return at most 5 documents using `Query.limit`.
- Project only the `name` and `price` fields using `Query.select` (so Appwrite returns only those user attributes; internal `$id`, `$createdAt`, etc. may still be present in the response).

The program must print the `documents` array from the Appwrite response as a single line of JSON to standard output (using `JSON.stringify` with no extra whitespace and no trailing/leading log lines). The JSON line must be the LAST non-empty line on stdout.

## Implementation Hints
- Install/use the `node-appwrite` Server SDK; it exposes `Client`, `Databases`, and `Query`.
- Read `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, and `ZEALT_RUN_ID` from environment variables.
- Read `database_id` and `collection_id` from `/home/user/myproject/.seed.json` (or derive `database_id` from `ZEALT_RUN_ID` — it is `products_${ZEALT_RUN_ID}`).
- The newer Node SDK uses an options-object call style: `databases.listDocuments({ databaseId, collectionId, queries: [...] })`.
- Reference docs:
  - https://appwrite.io/docs/products/databases/queries
  - https://appwrite.io/docs/references/cloud/server-nodejs/databases#listDocuments

## Acceptance Criteria
- Project path: /home/user/myproject
- Entry point: `/home/user/myproject/index.js`, executed by the verifier with `node /home/user/myproject/index.js`.
- The script reads `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, and `ZEALT_RUN_ID` from environment variables.
- The script uses `Query.equal`, `Query.greaterThanEqual`, `Query.orderDesc`, `Query.limit`, and `Query.select` (passed to `databases.listDocuments`).
- The LAST non-empty line of stdout MUST be a single line containing a valid JSON array (the `documents` array as returned by Appwrite, or the equivalent shape).
- After parsing that JSON array:
  - Its length is exactly `5`.
  - Every element's user attributes are exactly `{name, price}` (Appwrite internal fields prefixed with `$` such as `$id`, `$createdAt`, `$updatedAt`, `$permissions`, `$collectionId`, `$databaseId`, `$sequence` are tolerated). No other non-`$` keys are allowed.
  - Every element refers to a document whose stored `category` (verified independently via the admin SDK) is `"electronics"`.
  - Every element has `price >= 100`.
  - The `price` values are non-increasing across the array (descending order).

