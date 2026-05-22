FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf appwrite requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    cat > package.json <<'JSON'
{
  "name": "appwrite-realtime-document-subscription",
  "version": "1.0.0",
  "private": true,
  "description": "Solver scaffold for the Appwrite Realtime document subscription task.",
  "type": "commonjs",
  "dependencies": {}
}
JSON

RUN cd /home/user/myproject && \
    npm install --no-audit --no-fund appwrite@latest node-appwrite@latest ws@latest

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite Realtime task environment: Node.js 20, appwrite + node-appwrite + ws npm packages preinstalled in /home/user/myproject; Python 3 with the appwrite Python SDK installed."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - Python packages: appwrite (admin SDK used by the verifier), requests
#   - Node.js v20 (installed via NodeSource setup_20.x) for running the realtime subscriber
#   - /home/user/myproject: solver workspace pre-initialized with package.json
#   - /home/user/myproject/node_modules: appwrite (web/client SDK), node-appwrite (server SDK), and ws (WebSocket polyfill) preinstalled
