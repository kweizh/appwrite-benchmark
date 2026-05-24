FROM ubuntu:24.04

# Base packages + Node.js 20 + pytest + appwrite + requests
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf appwrite requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Pre-create the project directory and install the latest `node-appwrite`
# Server SDK so both the agent and the verifier can require('node-appwrite')
# and require('node-appwrite/file') without further setup.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install node-appwrite@latest --no-audit --no-fund --silent

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite Storage chunked upload task: Ubuntu 24.04 + Node.js 20 + node-appwrite Server SDK preinstalled in /home/user/myproject."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - apt: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - pip3: pytest-json-ctrf appwrite requests
#   - Node.js 20 from NodeSource
#   - /home/user/myproject contains a package.json with `node-appwrite` (and its `file` subpath) preinstalled
#   - Secrets (APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY) and
#     ZEALT_RUN_ID are provided at runtime; APPWRITE_BUCKET_ID is exported
#     by the initial-state seeding step.
