You are building a server-side rendered (SSR) Next.js application that requires specific routes to be protected from unauthenticated visitors.

You need to implement an SSR authentication check in a Next.js App Router `page.tsx` file. The code must extract the Appwrite session cookie from the incoming request, create an authenticated `node-appwrite` server client, and fetch the current user's account details to render the page.

**Constraints:**
- You MUST properly catch unauthorized access attempts and redirect the user to `/login` if the session cookie is missing or invalid.
- You MUST use the `node-appwrite` SDK (not the client SDK) to validate the session securely on the server.