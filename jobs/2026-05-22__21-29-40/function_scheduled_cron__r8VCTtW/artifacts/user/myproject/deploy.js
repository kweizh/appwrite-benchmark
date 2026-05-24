const { Client, Functions } = require('node-appwrite');
const { InputFile } = require('node-appwrite/file');
const tar = require('tar');
const fs = require('fs');
const path = require('path');

async function deploy() {
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

  const functions = new Functions(client);
  const functionId = `cron-fn-${runId}`;
  const archivePath = path.join(__dirname, 'code.tar.gz');

  try {
    // 1. Create the function
    let appwriteFunction;
    try {
      appwriteFunction = await functions.get(functionId);
      console.log(`Function ${functionId} already exists.`);
    } catch (e) {
      console.log(`Creating function ${functionId}...`);
      appwriteFunction = await functions.create(
        functionId,
        `cron-fn-${runId}`,
        'node-22',
        ['any'],
        [], // events
        '*/5 * * * *', // schedule
        15, // timeout (increased from 0 to 15)
        true, // enabled
        false, // logging
        'src/main.js' // entrypoint
      );
    }

    // 2. Package src/ directory
    console.log('Packaging src directory...');
    await tar.c(
      {
        gzip: true,
        file: archivePath,
        cwd: __dirname,
      },
      ['src']
    );

    // 3. Create and activate deployment
    console.log('Creating deployment...');
    const deployment = await functions.createDeployment(
      functionId,
      InputFile.fromPath(archivePath, 'code.tar.gz'),
      true // activate
    );

    const deploymentId = deployment.$id;

    // 4. Poll deployment status
    console.log(`Polling deployment ${deploymentId} status...`);
    let status = deployment.status;
    while (status !== 'ready' && status !== 'failed') {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const updatedDeployment = await functions.getDeployment(functionId, deploymentId);
      status = updatedDeployment.status;
      console.log(`Current status: ${status}`);
    }

    if (status === 'failed') {
      console.error('Deployment failed');
      process.exit(1);
    }

    // 5. Get final function info to confirm schedule
    const finalFunction = await functions.get(functionId);

    // Clean up
    if (fs.existsSync(archivePath)) {
      fs.unlinkSync(archivePath);
    }

    // Final output
    console.log(JSON.stringify({
      $id: finalFunction.$id,
      schedule: finalFunction.schedule
    }));

  } catch (err) {
    console.error('Error during deployment:', err);
    process.exit(1);
  }
}

deploy();
