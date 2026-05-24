FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep jq && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g appwrite-cli@latest && \
    pip3 install --break-system-packages pytest-json-ctrf appwrite requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN appwrite --version

RUN mkdir -p /home/user && chmod 0755 /home/user
RUN mkdir -p /home/user/myproject && chmod 0755 /home/user/myproject

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite CLI task environment: Ubuntu 24.04 + Node.js 20 + appwrite-cli + Python Appwrite SDK for verifying CLI-driven project initialization."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - additional apt package: jq (useful for parsing appwrite CLI JSON output)
#   - Node.js v20 for hosting the appwrite-cli npm package
#   - appwrite-cli (latest) installed globally so `appwrite` is on PATH
#   - python3 packages (--break-system-packages): pytest-json-ctrf, appwrite (admin SDK used by verifier), requests
#   - /home/user/myproject: empty project directory where the solver writes run.sh and appwrite.config.json
