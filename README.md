# MS ChatGPT MCP Bridge

This server exposes Home Assistant entities and a limited set of control tools to ChatGPT over MCP.

## Requirements

- Python 3.11+
- A reachable Home Assistant HTTPS URL
- The bridge key created in the Home Assistant integration
- A separate strong MCP API key for ChatGPT

## Configure

Copy `.env.example` to `.env` and set:

- `HA_BRIDGE_URL`: Home Assistant base URL, e.g. `https://ha.example.com`
- `HA_BRIDGE_KEY`: key configured in the Home Assistant integration
- `MCP_API_KEY`: a different random key used by the ChatGPT connector
- `HOST` and `PORT`: bind settings

Never commit `.env`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env
python server.py
```

MCP endpoint: `http://127.0.0.1:8000/mcp`

For ChatGPT, deploy behind HTTPS and configure the custom MCP connector with the HTTPS `/mcp` URL. Important: the included bearer-key middleware is for local/dev testing and is not, by itself, a supported ChatGPT custom-connector authentication flow. Current ChatGPT custom MCP setup documents OAuth or no authentication; for a public deployment, replace this middleware with a compliant OAuth 2.1 authorization server before connecting. Do not deploy the endpoint unauthenticated. ChatGPT connector availability and action permissions depend on account plan/workspace settings.

## Docker

```bash
docker compose up --build -d
```

Put a real `.env` beside `docker-compose.yml` before starting.

## Supported tools

- `list_devices(domain)` — list entities and states
- `get_device_state(entity_id)` — inspect one entity
- `control_device(entity_id, action, service_data)` — invoke an allowlisted service

This is a starter project. Before public multi-user deployment, add per-user HA connections, rate limiting, audit logging, robust schema validation, and a security review.
