const { Client, Storage, Permission, Role } = require('node-appwrite');

async function createSecureBucket() {
    const endpoint = process.env.APPWRITE_ENDPOINT;
    const projectId = process.env.APPWRITE_PROJECT_ID;
    const apiKey = process.env.APPWRITE_API_KEY;
    const runId = process.env.ZEALT_RUN_ID;

    if (!endpoint || !projectId || !apiKey || !runId) {
        console.error('Missing required environment variables');
        process.exit(1);
    }

    const client = new Client()
        .setEndpoint(endpoint)
        .setProject(projectId)
        .setKey(apiKey);

    const storage = new Storage(client);

    const bucketName = `secure-uploads-${runId}`;
    const bucketId = `secure-uploads-${runId}`;

    try {
        // Using the options object style as recommended in the hints and modern node-appwrite SDKs
        const bucket = await storage.createBucket(
            bucketId,
            bucketName,
            [
                Permission.read(Role.users()),
                Permission.write(Role.users()),
            ],
            true, // fileSecurity
            true, // enabled
            5242880, // maximumFileSize
            ['jpg', 'jpeg', 'png', 'webp'], // allowedFileExtensions
            'gzip', // compression
            true, // encryption
            true // antivirus
        );

        console.log(`BUCKET_ID: ${bucket.$id}`);
    } catch (error) {
        // Fallback to options object style if the above fails (some versions of the SDK prefer one over the other)
        try {
            const bucket = await storage.createBucket({
                bucketId: bucketId,
                name: bucketName,
                permissions: [
                    Permission.read(Role.users()),
                    Permission.write(Role.users()),
                ],
                fileSecurity: true,
                maximumFileSize: 5242880,
                allowedFileExtensions: ['jpg', 'jpeg', 'png', 'webp'],
                compression: 'gzip',
                encryption: true,
                antivirus: true
            });
            console.log(`BUCKET_ID: ${bucket.$id}`);
        } catch (finalError) {
            console.error('Error creating bucket:', finalError.message);
            process.exit(1);
        }
    }
}

createSecureBucket();
