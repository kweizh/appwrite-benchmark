const { Client, Databases, ID, RelationshipType, RelationMutate } = require('node-appwrite');

async function run() {
    const endpoint = process.env.APPWRITE_ENDPOINT;
    const projectId = process.env.APPWRITE_PROJECT_ID;
    const apiKey = process.env.APPWRITE_API_KEY;
    const runId = process.env.ZEALT_RUN_ID;

    if (!endpoint || !projectId || !apiKey || !runId) {
        console.error('Missing environment variables');
        process.exit(1);
    }

    const client = new Client()
        .setEndpoint(endpoint)
        .setProject(projectId)
        .setKey(apiKey);

    const databases = new Databases(client);

    const databaseId = `blog_${runId}`;
    const authorsCollectionId = 'authors';
    const postsCollectionId = 'posts';

    try {
        // Create Database
        await databases.create(databaseId, databaseId);

        // Create Collections
        await databases.createCollection(databaseId, authorsCollectionId, authorsCollectionId);
        await databases.createCollection(databaseId, postsCollectionId, postsCollectionId);

        // Create Attributes
        await databases.createStringAttribute(databaseId, authorsCollectionId, 'name', 255, true);
        await databases.createStringAttribute(databaseId, postsCollectionId, 'title', 255, true);
        await databases.createStringAttribute(databaseId, postsCollectionId, 'body', 10000, true);

        // Create Relationship
        // One-to-Many from authors to posts
        await databases.createRelationshipAttribute(
            databaseId,
            authorsCollectionId, // parent
            RelationshipType.OneToMany,
            false, // hasMany (OneToMany implies many on child side) - wait, Appwrite SDK signature:
            // createRelationshipAttribute(databaseId, collectionId, relatedCollectionId, type, twoWay, key, twoWayKey, onDelete)
            postsCollectionId, // relatedCollectionId
            RelationshipType.OneToMany,
            true, // twoWay
            'posts', // key (on authors)
            'author', // twoWayKey (on posts)
            RelationMutate.SetNull // onDelete
        );

        // Wait for attributes to be available
        const attributesToWait = [
            { collectionId: authorsCollectionId, key: 'name' },
            { collectionId: postsCollectionId, key: 'title' },
            { collectionId: postsCollectionId, key: 'body' },
            { collectionId: authorsCollectionId, key: 'posts' },
            { collectionId: postsCollectionId, key: 'author' }
        ];

        for (const attr of attributesToWait) {
            await waitForAttribute(databases, databaseId, attr.collectionId, attr.key);
        }

        console.log(JSON.stringify({
            databaseId,
            authorsCollectionId,
            postsCollectionId
        }));

    } catch (error) {
        console.error(error);
        process.exit(1);
    }
}

async function waitForAttribute(databases, databaseId, collectionId, key) {
    let available = false;
    while (!available) {
        try {
            const attribute = await databases.getAttribute(databaseId, collectionId, key);
            if (attribute.status === 'available') {
                available = true;
            } else if (attribute.status === 'failed') {
                throw new Error(`Attribute ${key} in collection ${collectionId} failed to create`);
            } else {
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        } catch (error) {
            if (error.code === 404) {
                // Might not be created yet in the internal queue
                await new Promise(resolve => setTimeout(resolve, 1000));
            } else {
                throw error;
            }
        }
    }
}

run();
