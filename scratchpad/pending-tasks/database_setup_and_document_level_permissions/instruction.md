You are building a user profile system using Appwrite Databases where users must have strict ownership over their data. 

You need to write a Node.js script using the `node-appwrite` SDK that creates a new profile document in an existing "Profiles" collection. The document must be configured securely so that only the specific user who created it can read and update it.

**Constraints:**
- You MUST use the `Permission.read()` and `Permission.write()` methods combined with `Role.user('[USER_ID]')` to assign the exact permissions.
- Do NOT assign global or wild-card roles (like `Role.any()`) to the document.