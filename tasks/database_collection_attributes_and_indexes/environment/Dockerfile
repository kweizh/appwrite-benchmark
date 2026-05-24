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

RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install node-appwrite@latest --silent

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite Databases task environment with Node.js 20, node-appwrite SDK, and the Python Appwrite SDK for verification."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]

# Container contents:
#   - apt packages: curl wget ca-certificates git python3 python3-pip python3-pytest bash ripgrep nodejs (v20)
#   - pip3 packages: pytest-json-ctrf appwrite requests
#   - Node.js v20 with the `node-appwrite` server SDK pre-installed in /home/user/myproject
#   - /home/user/myproject: working directory for the solver's index.js script
