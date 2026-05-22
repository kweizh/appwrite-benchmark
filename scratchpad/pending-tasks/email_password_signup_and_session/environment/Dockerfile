FROM ubuntu:24.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    pip3 install --break-system-packages pytest-json-ctrf requests appwrite && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/user && chmod 0755 /home/user

# Pre-create the project directory and install both Appwrite Node SDKs so the
# initial-state checks pass before the executor writes any code.
RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install --silent node-appwrite@latest appwrite@latest

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite email/password signup and session task: Ubuntu 24.04 with Node.js 20, both Appwrite Node SDKs (node-appwrite + appwrite) pre-installed in /home/user/myproject, and the Python appwrite admin SDK for verification."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - base image: ubuntu:24.04
#   - always required apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep
#   - always required pip3 packages: pytest-json-ctrf
#   - additional pip3 packages: requests, appwrite (Python admin SDK for verifier)
#   - Node.js 20 (from NodeSource) for running the solver script
#   - /home/user/myproject: npm-initialized project directory with
#       * node-appwrite (server SDK with admin/users API)
#       * appwrite (client-web SDK with account/session API)
