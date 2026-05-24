const { Client, Functions } = require('node-appwrite');
const client = new Client();
const functions = new Functions(client);
console.log('Functions.prototype keys:', Object.keys(Object.getPrototypeOf(functions)));
