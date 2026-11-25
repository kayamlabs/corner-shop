# Agent image. The engine, the firm config and the episode state are root-only; the agent runs as
# the unprivileged user `agent` and plays through `shop`, which may call the engine via sudo.
FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

RUN apt-get update \
    && apt-get install -y --no-install-recommends sudo \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash agent \
    && mkdir -p /app && chown agent:agent /app

COPY going_concern /opt/corner-shop/going_concern
COPY firm.json shop_core.py /opt/corner-shop/
COPY shop /usr/local/bin/shop
COPY shop.sudoers /etc/sudoers.d/corner-shop

RUN chown -R root:root /opt/corner-shop \
    && chmod -R go-rwx /opt/corner-shop \
    && chmod 755 /usr/local/bin/shop \
    && chmod 440 /etc/sudoers.d/corner-shop \
    && visudo -cf /etc/sudoers.d/corner-shop \
    && mkdir -p /var/lib/corner-shop && chmod 700 /var/lib/corner-shop \
    && python3 -I /opt/corner-shop/shop_core.py status > /dev/null \
    && chmod 600 /var/lib/corner-shop/*

WORKDIR /app
