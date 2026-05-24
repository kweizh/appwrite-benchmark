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

RUN mkdir -p /home/user/myproject && \
    cd /home/user/myproject && \
    npm init -y >/dev/null && \
    npm install --silent node-appwrite@latest

LABEL Author="generate-harbor-tasks"
LABEL Description="Appwrite Users updateLabels task: Ubuntu 24.04 + Node 20 + node-appwrite + Python appwrite admin SDK."

CMD ["/bin/bash", "-c", "trap : TERM INT; sleep infinity & wait"]
