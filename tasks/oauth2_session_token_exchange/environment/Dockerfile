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

# Pre-create the project directory and install the Appwrite SDKs so the
# initial-state checks pass before the executor writes any code. The task
# requires both the client-web SDK (`appwrite`) and the server SDK
# (`node-appwrite`, used for the seeding/verification path).
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install --silent appwrite@latest node-appwrite@latest

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite OAuth2 server-side token-exchange task: Ubuntu 24.04 with Node.js 20, python3+pytest, and the appwrite + node-appwrite SDKs pre-installed under /home/user/myproject."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - base image: ubuntu:24.04
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - Node.js v20 (via NodeSource setup_20.x) for the Appwrite SDKs
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages used by the verifier scripts: appwrite, requests
#   - /home/user/myproject: pre-initialized npm project with `appwrite` (client-web SDK)
#     and `node-appwrite` (server SDK) installed; the initial-state script seeds
#     `.seed.json` with a userId/secret produced by `users.createToken(userId)`.
