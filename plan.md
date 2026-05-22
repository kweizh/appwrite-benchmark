# Evaluation Dataset Research: Appwrite

## 1. Library Overview
*   **Description**: Appwrite is an open-source, end-to-end backend-as-a-service (BaaS) that abstracts complex backend tasks into a set of REST, GraphQL, and Realtime APIs. It provides developers with tools for authentication, databases, file storage, serverless functions, and messaging.
*   **Ecosystem Role**: A major open-source alternative to Firebase and Supabase. It is designed to be platform-agnostic, supporting Web, Flutter, Android, iOS, and various server-side languages (Node.js, Python, PHP, Ruby, etc.).
*   **Project Setup**:
    *   **Cloud**: Create an account at [cloud.appwrite.io](https://cloud.appwrite.io), create a project, and obtain the Project ID and Endpoint.
    *   **Self-Hosted**: Install via Docker:
        ```bash
        docker run -it --rm \
            --volume /var/run/docker.sock:/var/run/docker.sock \
            --volume "$(pwd)"/appwrite:/usr/src/code/appwrite:rw \
            --entrypoint="install" \
            appwrite/appwrite:latest
        ```
    *   **CLI**: Install and initialize a project:
        ```bash
        npm install -g appwrite-cli
        appwrite login
        appwrite init project
        ```

## 2. Core Primitives & APIs

### Authentication (Account & Users)
Manages user registration, login, and sessions.
*   **API**: `account.create()`, `account.createEmailPasswordSession()`, `account.get()`.
*   **Code Example (Client-side)**:
    ```javascript
    import { Client, Account, ID } from "appwrite";
    const client = new Client().setEndpoint('https://cloud.appwrite.io/v1').setProject('<ID>');
    const account = new Account(client);

    // Create a new user
    await account.create(ID.unique(), 'email@example.com', 'password123');
    // Login
    await account.createEmailPasswordSession('email@example.com', 'password123');
    ```
*   **Docs**: [Authentication API](https://appwrite.io/docs/products/auth)

### Databases (Collections & Documents)
NoSQL-like database structure (Databases > Collections > Documents).
*   **API**: `databases.createDocument()`, `databases.listDocuments()`, `databases.updateDocument()`.
*   **Code Example (Server-side)**:
    ```javascript
    import { Client, Databases, ID, Permission, Role } from "node-appwrite";
    const databases = new Databases(serverClient);

    const result = await databases.createDocument(
        '[DATABASE_ID]',
        '[COLLECTION_ID]',
        ID.unique(),
        { title: 'Hello Appwrite', content: 'Dataset research...' },
        [Permission.read(Role.any()), Permission.write(Role.user('[USER_ID]'))]
    );
    ```
*   **Docs**: [Databases API](https://appwrite.io/docs/products/databases)

### Functions (Serverless)
Custom backend logic triggered by events or HTTP requests.
*   **API**: `functions.createExecution()`.
*   **Pattern**: Functions receive a `context` object containing `req`, `res`, `log`, and `error`.
*   **Docs**: [Functions API](https://appwrite.io/docs/products/functions)

### Storage (Buckets & Files)
Manages file uploads and image transformations.
*   **API**: `storage.createFile()`, `storage.getFilePreview()`.
*   **Docs**: [Storage API](https://appwrite.io/docs/products/storage)

## 3. Real-World Use Cases & Templates
*   **Collaborative Apps**: Realtime synchronization for chat or project management tools using the [Realtime API](https://appwrite.io/docs/apis/realtime).
*   **SaaS Boilerplates**: Multi-tenant structures using [Teams](https://appwrite.io/docs/products/auth/teams) and [Labels](https://appwrite.io/docs/products/auth/labels).
*   **AI Workflows**: Functions that trigger on document creation to process data via OpenAI or Hugging Face ([Function Templates](https://github.com/appwrite/templates)).
*   **SSR Applications**: Authentication flows for Next.js or Nuxt.js using session cookies or JWTs ([SSR Guide](https://appwrite.io/docs/products/auth/server-side-rendering)).

## 4. Developer Friction Points
*   **Permission Ownership**: A common pitfall where users try to assign permissions they don't "own" (e.g., sharing a document with a team they aren't in), resulting in `401 Unauthorized` errors.
*   **3rd Party Cookie Restrictions**: When accessing files in restricted buckets via direct URLs, browsers often block the session cookie, causing 401 errors even for logged-in users. Developers must use the SDK or authenticated proxying.
*   **SSR Auth Complexity**: Synchronizing authentication state between the server (Node.js) and the client (Browser) requires complex cookie management that often leads to "unauthorized" errors on the server side.
*   **Function Cold Starts & Scopes**: Debugging why a function fails to execute due to missing "scopes" in the API key or incorrect environment variable configuration.

## 5. Evaluation Ideas
*   **Simple**: Create a "Profile" collection where users can only read and write their own documents.
*   **Simple**: Implement a file upload form that generates a 200x200px thumbnail preview using the Storage API.
*   **Intermediate**: Build a real-time notification system where a message appears to all team members when a new document is added.
*   **Intermediate**: Create an Appwrite Function that automatically translates a "comment" document into another language using an external AI API.
*   **Advanced**: Implement a secure multi-tenant SaaS dashboard where "Admins" can see all data but "Members" can only see data belonging to their Team.
*   **Advanced**: Set up a full SSR authentication flow in Next.js that protects specific routes and fetches data server-side using the Appwrite JWT.
*   **Advanced**: Build a "Database Sync" function that mirrors Appwrite collection changes to an external Meilisearch or Algolia index.

## 6. Sources
1.  [Appwrite llms.txt](https://appwrite.io/llms.txt): Comprehensive documentation overview.
2.  [Appwrite Official Docs](https://appwrite.io/docs): Detailed API references and guides.
3.  [Appwrite GitHub Issues](https://github.com/appwrite/appwrite/issues): Source for common developer friction points and bugs.
4.  [Appwrite Function Templates](https://github.com/appwrite/templates): Collection of starter logic for serverless functions.
5.  [Appwrite Blog: Production Ready Backend](https://appwrite.io/blog/post/building-a-production-ready-backend-with-appwrite): Best practices and security considerations.