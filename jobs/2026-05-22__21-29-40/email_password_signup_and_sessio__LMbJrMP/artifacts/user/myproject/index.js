const { Client: ServerClient, Users, ID: ServerID } = require('node-appwrite');
const { Client: ClientClient, Account } = require('appwrite');
const crypto = require('crypto');

async function run() {
    const endpoint = process.env.APPWRITE_ENDPOINT;
    const projectId = process.env.APPWRITE_PROJECT_ID;
    const apiKey = process.env.APPWRITE_API_KEY;
    const runId = process.env.ZEALT_RUN_ID;

    if (!endpoint || !projectId || !apiKey || !runId) {
        console.error('Error: Missing required environment variables (APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY, ZEALT_RUN_ID)');
        process.exit(1);
    }

    const email = `harbor-${runId}@example.com`;
    const password = crypto.randomBytes(16).toString('hex');

    try {
        // Step 1 – Server-side signup
        const serverClient = new ServerClient()
            .setEndpoint(endpoint)
            .setProject(projectId)
            .setKey(apiKey);
        
        const users = new Users(serverClient);
        
        console.error(`Creating user: ${email}`);
        await users.create(ServerID.unique(), email, undefined, password);
        console.error('User created successfully (server-side).');

        // Step 2 – Client-side session
        const clientClient = new ClientClient()
            .setEndpoint(endpoint)
            .setProject(projectId);
        
        const account = new Account(clientClient);
        
        console.error('Creating session (client-side)...');
        const session = await account.createEmailPasswordSession(email, password);
        
        // Step 3 – Output
        // Print the returned session's $id value as the last non-empty line of stdout
        console.log(session.$id);
        process.exit(0);
    } catch (error) {
        console.error('An error occurred:');
        console.error(error);
        process.exit(1);
    }
}

run();
