const { Client, Teams, Users, ID } = require('node-appwrite');

async function run() {
    const endpoint = process.env.APPWRITE_ENDPOINT;
    const projectId = process.env.APPWRITE_PROJECT_ID;
    const apiKey = process.env.APPWRITE_API_KEY;
    const zealtRunId = process.env.ZEALT_RUN_ID;

    if (!endpoint || !projectId || !apiKey || !zealtRunId) {
        console.error('Missing required environment variables');
        process.exit(1);
    }

    const client = new Client()
        .setEndpoint(endpoint)
        .setProject(projectId)
        .setKey(apiKey);

    const teams = new Teams(client);
    const users = new Users(client);

    try {
        // Step 1 – Create a team
        const teamName = `Engineering-${zealtRunId}`;
        const team = await teams.create(ID.unique(), teamName);
        console.error(`Team created: ${team.$id}`);

        // Step 2 – Create a user
        const userEmail = `member-${zealtRunId}@example.com`;
        const userName = `Member ${zealtRunId}`;
        const user = await users.create(ID.unique(), userEmail, undefined, 'TempPassw0rd!', userName);
        console.error(`User created: ${user.$id}`);

        // Step 3 – Create a membership
        // teams.createMembership(teamId, roles, email?, userId?, phone?, url?, name?)
        const membership = await teams.createMembership(
            team.$id,
            ['member'],
            undefined, // email
            user.$id,  // userId
            undefined, // phone
            undefined, // url (skip email confirmation)
            userName   // name
        );
        console.error(`Membership created: ${membership.$id}`);

        // Step 4 – Output
        const output = {
            teamId: team.$id,
            userId: user.$id,
            membershipId: membership.$id
        };
        console.log(JSON.stringify(output));

    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

run();
