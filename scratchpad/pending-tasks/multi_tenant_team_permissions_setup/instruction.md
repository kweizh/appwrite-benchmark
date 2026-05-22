You are building a multi-tenant SaaS application where data belongs to specific teams, but system administrators require global oversight of the platform.

You need to write a backend Node.js script that inserts a new document into a "Projects" collection. The script must assign permissions so that members of a specific team (using `[TEAM_ID]`) have read and write access, while granting read-only access to any user holding the label "Admin".

**Constraints:**
- You MUST use `Role.team('[TEAM_ID]')` for team-level access.
- You MUST use `Role.label('Admin')` to grant the administrative read access.
- Ensure you do not attempt to assign permissions for a team the executing API key or user does not own, avoiding `401 Unauthorized` errors.