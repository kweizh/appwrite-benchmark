const { Client, Storage, ID, Permission, Role } = require('node-appwrite');
const { InputFile } = require('node-appwrite/file');

async function run() {
    const endpoint = process.env.APPWRITE_ENDPOINT;
    const project = process.env.APPWRITE_PROJECT_ID;
    const key = process.env.APPWRITE_API_KEY;
    const runId = process.env.ZEALT_RUN_ID;

    if (!endpoint || !project || !key || !runId) {
        console.error('Missing required environment variables');
        process.exit(1);
    }

    const client = new Client()
        .setEndpoint(endpoint)
        .setProject(project)
        .setKey(key);

    const storage = new Storage(client);
    const bucketId = `bkt-${runId}`;
    const filePath = '/home/user/myproject/sample.bin';

    try {
        // Create bucket
        await storage.createBucket(bucketId, bucketId);

        // Upload file with progress
        const file = await storage.createFile(
            bucketId,
            ID.unique(),
            InputFile.fromPath(filePath, 'sample.bin'),
            [Permission.read(Role.any())],
            (progress) => {
                const log = {
                    chunksTotal: progress.chunksTotal,
                    chunksUploaded: progress.chunksUploaded,
                    progress: progress.progress,
                    sizeUploaded: progress.sizeUploaded,
                    id: progress.$id
                };
                process.stderr.write(JSON.stringify(log) + '\n');
            }
        );

        console.log(file.$id);
    } catch (error) {
        console.error(error);
        process.exit(1);
    }
}

run();
