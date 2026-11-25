FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The engine and firms are not committed here; build.sh downloads them from the public repo.
# Pin to a commit for reproducible builds: --build-arg CORNER_SHOP_REF=<sha>
ARG CORNER_SHOP_REF=main
RUN if [ ! -d corner_shop/going_concern ] || [ ! -d corner_shop/firms ]; then \
        CORNER_SHOP_REF="$CORNER_SHOP_REF" sh build.sh; \
    fi \
    && python -c "from corner_shop.environment import FIRMS, load_firm; [load_firm(i) for i in FIRMS]"

EXPOSE 8080

CMD ["python", "server.py"]
