const { Client, Databases, ID, Role, Permission } = require('node-appwrite');

async function run() {
    const endpoint = process.env.APPWRITE_ENDPOINT;
    const projectId = process.env.APPWRITE_PROJECT_ID;
    const apiKey = process.env.APPWRITE_API_KEY;
    const runId = process.env.ZEALT_RUN_ID;

    const client = new Client()
        .setEndpoint(endpoint)
        .setProject(projectId)
        .setKey(apiKey);

    const databases = new Databases(client);

    // 1. Create Database
    const dbName = `tasks_db_${runId}`;
    const db = await databases.create(ID.unique(), dbName);
    const databaseId = db.$id;

    // 2. Create Collection
    const collectionName = 'tasks';
    const collection = await databases.createCollection(
        databaseId,
        ID.unique(),
        collectionName,
        [Permission.read(Role.any())]
    );
    const collectionId = collection.$id;

    // 3. Create Attributes
    await databases.createStringAttribute(databaseId, collectionId, 'title', 255, true);
    await databases.createIntegerAttribute(databaseId, collectionId, 'priority', true, 1, 5);
    await databases.createBooleanAttribute(databaseId, collectionId, 'completed', false, false);
    await databases.createDatetimeAttribute(databaseId, collectionId, 'dueDate', false);

    // 4. Wait for attributes to reach "available" status
    const requiredAttributes = ['title', 'priority', 'completed', 'dueDate'];
    while (true) {
        const result = await databases.listAttributes(databaseId, collectionId);
        const availableAttributes = result.attributes
            .filter(attr => attr.status === 'available')
            .map(attr => attr.key);
        
        const allAvailable = requiredAttributes.every(key => availableAttributes.includes(key));
        if (allAvailable && result.attributes.length >= 4) {
            break;
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    // 5. Create Indexes
    await databases.createIndex(
        databaseId,
        collectionId,
        'priority_idx',
        'key',
        ['priority'],
        ['asc']
    );

    await databases.createIndex(
        databaseId,
        collectionId,
        'title_unique',
        'unique',
        ['title']
    );

    // 6. Print JSON output
    console.log(JSON.stringify({ databaseId, collectionId }));
}

run().catch(err => {
    console.error(err);
    process.exit(1);
});
