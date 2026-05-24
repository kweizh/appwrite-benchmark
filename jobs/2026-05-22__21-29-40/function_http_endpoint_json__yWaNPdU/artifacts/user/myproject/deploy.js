const { Client, Functions, Role } = require('node-appwrite');
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
    console.error('Missing environment variables');
    process.exit(1);
  }

  const client = new Client()
    .setEndpoint(endpoint)
    .setProject(projectId)
    .setKey(apiKey);

  const functions = new Functions(client);
  const functionId = `greeting-fn-${runId}`;

  // 1. Create function if not exists
  try {
    await functions.get(functionId);
    console.log(`Function ${functionId} already exists.`);
  } catch (e) {
    console.log(`Creating function ${functionId}...`);
    await functions.create(
      functionId,
      functionId,
      'node-22',
      [Role.any()],
      undefined, // events
      undefined, // schedule
      undefined, // timeout
      undefined, // enabled
      undefined, // logging
      'src/main.js'
    );
  }

  // 2. Package src directory
  const archivePath = path.join(__dirname, 'code.tar.gz');
  await tar.c(
    {
      gzip: true,
      file: archivePath,
      cwd: __dirname
    },
    ['src']
  );
  console.log('Packaged src directory.');

  // 3. Create deployment
  console.log('Creating deployment...');
  const deployment = await functions.createDeployment(
    functionId,
    InputFile.fromPath(archivePath, 'code.tar.gz'),
    true // activate
  );

  const deploymentId = deployment.$id;

  // 4. Poll deployment status
  console.log(`Waiting for deployment ${deploymentId} to be ready...`);
  let status = deployment.status;
  while (status !== 'ready' && status !== 'failed') {
    await new Promise(resolve => setTimeout(resolve, 2000));
    const updatedDeployment = await functions.getDeployment(functionId, deploymentId);
    status = updatedDeployment.status;
    console.log(`Status: ${status}`);
  }

  if (status === 'failed') {
    console.error('Deployment failed');
    process.exit(1);
  }

  // 5. Trigger execution
  console.log('Triggering execution...');
  const execution = await functions.createExecution(
    functionId,
    '', // body
    false, // async
    '/greeting?name=Appwrite',
    'GET'
  );

  const responseBody = execution.responseBody;
  console.log(responseBody);

  // 6. Write to log file
  fs.appendFileSync(path.join(__dirname, 'output.log'), responseBody);
}

deploy().catch(err => {
  console.error(err);
  process.exit(1);
});
