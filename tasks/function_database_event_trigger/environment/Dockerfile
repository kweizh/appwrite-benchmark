FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf appwrite requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    cat > package.json <<'JSON'
{
  "name": "appwrite-function-database-event-trigger",
  "version": "1.0.0",
  "private": true,
  "description": "Solver scaffold for Appwrite Functions database-event-trigger task.",
  "type": "commonjs",
  "dependencies": {
    "node-appwrite": "^17.0.0",
    "tar": "^7.4.3"
  }
}
JSON

RUN cd /home/user/myproject && npm install --omit=dev --no-audit --no-fund

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite Functions task environment for database-event-trigger: Node.js 22, node-appwrite SDK, 'tar' npm package preinstalled in /home/user/myproject; Python 3 with the appwrite SDK and requests for verifier scripts."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - verifier pip3 packages: appwrite (python SDK), requests
#   - Node.js v22 (NodeSource setup_22.x) for executing node-appwrite SDK calls
#   - /home/user/myproject: solver workspace pre-initialized with package.json
#   - /home/user/myproject/node_modules: latest node-appwrite + tar npm packages preinstalled
