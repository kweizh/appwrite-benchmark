const { InputFile } = require('node-appwrite/file');
console.log('InputFile:', InputFile);
if (InputFile) {
  console.log('InputFile keys:', Object.keys(InputFile));
}
