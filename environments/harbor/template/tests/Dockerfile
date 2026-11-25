# Verifier image: a clean copy of the engine and this task's firm. Nothing from the agent's
# container is used except the episode file, which Harbor copies in as an artifact.
FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b
COPY . /tests/
RUN chmod +x /tests/test.sh && mkdir -p /var/lib/corner-shop /logs/verifier
WORKDIR /tests
