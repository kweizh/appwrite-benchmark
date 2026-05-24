FROM node:20-bookworm

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    pip3 install --break-system-packages pytest-json-ctrf requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Pre-create the project directory and install the Appwrite SDKs so the
# initial-state checks pass before the executor writes any code.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install --silent appwrite node-appwrite

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite magic-URL passwordless authentication task: Node.js 20 project with the appwrite client SDK and node-appwrite server SDK pre-installed."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - base image: node:20-bookworm (Node.js v20 on Debian bookworm)
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf, requests
#   - /home/user/myproject: pre-initialized npm project with `appwrite` (client-web SDK)
#     and `node-appwrite` (server SDK) installed
