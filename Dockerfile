# syntax=docker/dockerfile:1.7
# atomno-mcp-cbr-rates — minimal image for Glama.ai analyzer + self-hosting.
#
# Build:    docker build -t atomno/atomno-mcp-cbr-rates:0.1.3 .
# Run:      docker run -i --rm atomno/atomno-mcp-cbr-rates:0.1.3
#
# The server speaks MCP over stdio (JSON-RPC). Run with `-i` so stdin/stdout
# stay attached. Glama analyzer launches the container, sends `initialize`
# + `tools/list` over stdio, and validates the response.

FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir .


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /bin/bash mcp
WORKDIR /home/mcp

COPY --from=build /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=build /usr/local/bin/atomno-mcp-cbr-rates /usr/local/bin/atomno-mcp-cbr-rates
COPY --from=build /usr/local/bin/mcp-cbr-rates /usr/local/bin/mcp-cbr-rates

USER mcp

ENTRYPOINT ["atomno-mcp-cbr-rates"]
