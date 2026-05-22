FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Pre-create the project directory and install `node-appwrite` so the initial
# state (SDK installed; importable from the project) matches test_initial_state.py.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install node-appwrite@latest --no-audit --no-fund --silent

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite Storage bucket creation task: Ubuntu 24.04 + Node.js 20 + node-appwrite SDK preinstalled in /home/user/myproject."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - Node.js v20 installed via NodeSource for the `node-appwrite` Server SDK
#   - /home/user/myproject: working directory with `node-appwrite` preinstalled (package.json + node_modules)
#   - No secrets baked in; APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY, and ZEALT_RUN_ID are provided at runtime
