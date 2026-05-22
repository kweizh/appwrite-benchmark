You have a "Comments" collection and want to automatically translate new comments using an AI workflow without blocking the client application.

You need to write an Appwrite Function in Node.js that triggers when a new comment document is created. The function should extract the `content` field from the event payload, call a mock external translation API, and then update the original document with the newly translated text.

**Constraints:**
- The function MUST extract the document ID and payload from the `context.req` object provided by the Appwrite runtime.
- Do NOT hardcode the database ID or collection ID; retrieve them from environment variables.