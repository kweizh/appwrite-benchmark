A collaborative workspace app needs to notify users instantly when a teammate adds a new task to a shared board.

You need to write a client-side JavaScript snippet that subscribes to the Appwrite Realtime API for a specific "Tasks" collection and logs the task payload to the console whenever a new task is added.

**Constraints:**
- You MUST subscribe ONLY to document creation events (do NOT trigger the console log on document updates or deletions).
- Ensure the `Client` is properly initialized with the project endpoint and project ID before initiating the subscription.