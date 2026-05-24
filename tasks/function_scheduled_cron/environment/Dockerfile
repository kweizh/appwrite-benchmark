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
  "name": "appwrite-function-scheduled-cron",
  "version": "1.0.0",
  "private": true,
  "description": "Solver scaffold for Appwrite Functions scheduled (CRON) task.",
  "type": "commonjs",
  "dependencies": {
    "node-appwrite": "latest",
    "tar": "latest"
  }
}
JSON

RUN cd /home/user/myproject && npm install --omit=dev --no-audit --no-fund

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite Functions task environment: Node.js 22, node-appwrite SDK and 'tar' preinstalled in /home/user/myproject; Python3 with appwrite + requests for verification."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: appwrite, requests (used by verifier and initial-state checks)
#   - Node.js v22 (installed via NodeSource setup_22.x) for executing node-appwrite SDK calls
#   - /home/user/myproject: solver workspace pre-initialized with package.json
#   - /home/user/myproject/node_modules: node-appwrite + tar npm packages preinstalled (latest)
