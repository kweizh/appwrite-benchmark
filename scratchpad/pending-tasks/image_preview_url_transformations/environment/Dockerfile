FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf appwrite requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Pre-create the project directory and install the Appwrite Web SDK (`appwrite`),
# the Server SDK (`node-appwrite`, available if needed), and `dotenv`. The
# initial-state test will additionally create `bkt-${ZEALT_RUN_ID}` /
# `img-${ZEALT_RUN_ID}` and write `/home/user/myproject/.env` at runtime.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install appwrite@latest node-appwrite@latest dotenv --no-audit --no-fund --silent

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite image preview URL task: Ubuntu 24.04 + Node.js 20 + appwrite/node-appwrite/dotenv preinstalled in /home/user/myproject."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: appwrite (Python SDK), requests (used by HTTP-based verification helpers)
#   - Node.js v20 installed via NodeSource for the `appwrite` (Web) and `node-appwrite` (Server) SDKs
#   - /home/user/myproject: working directory with `appwrite`, `node-appwrite`, and `dotenv` preinstalled
#   - No secrets baked in; APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY, ZEALT_RUN_ID provided at runtime
