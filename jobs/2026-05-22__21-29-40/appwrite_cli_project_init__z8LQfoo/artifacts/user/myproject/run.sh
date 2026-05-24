#!/bin/bash
set -e

# Ensure we are in the project directory
mkdir -p /home/user/myproject
cd /home/user/myproject

# Read environment variables
# ZEALT_RUN_ID, APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY

if [ -z "$ZEALT_RUN_ID" ]; then
    echo "Error: ZEALT_RUN_ID is not set."
    exit 1
fi

DB_ID="cli-${ZEALT_RUN_ID}"
COLLECTION_ID="notes-${ZEALT_RUN_ID}"

# 1. Switch the CLI to non-interactive mode
appwrite client --endpoint "$APPWRITE_ENDPOINT" --project-id "$APPWRITE_PROJECT_ID" --key "$APPWRITE_API_KEY"

# 2. Create appwrite.json
# Note: Using the legacy 'databases' and 'collections' structure as it's well-documented for 'appwrite push collections'
cat <<EOF > appwrite.json
{
    "projectId": "$APPWRITE_PROJECT_ID",
    "projectName": "CLI Project",
    "databases": [
        {
            "\$id": "$DB_ID",
            "name": "$DB_ID",
            "enabled": true
        }
    ],
    "collections": [
        {
            "\$id": "$COLLECTION_ID",
            "databaseId": "$DB_ID",
            "name": "$COLLECTION_ID",
            "enabled": true,
            "attributes": [
                {
                    "key": "body",
                    "type": "string",
                    "size": 255,
                    "required": false,
                    "array": false
                }
            ],
            "indexes": []
        }
    ]
}
EOF

# 3. Push the declared resources to Appwrite non-interactively
# Using 'push collections' as requested (or its modern equivalent if preferred, but 'collections' is specifically mentioned)
# The --all and --force flags ensure it's non-interactive
appwrite push collections --all --force > /dev/null 2>&1

# Output the required JSON object as the very last line
echo "{\"databaseId\":\"$DB_ID\",\"collectionId\":\"$COLLECTION_ID\"}"
