import os
import httpx
import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Scope, Receive, Send

load_dotenv()

HA_URL = os.environ["HA_BRIDGE_URL"].rstrip("/")
HA_KEY = os.environ["HA_BRIDGE_KEY"]
MCP_KEY = os.environ["MCP_API_KEY"]
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

mcp = FastMCP("MS Smart Home Bridge", host=HOST, port=PORT)

async def ha_get(path: str):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{HA_URL}/api/ms_smart_home_bridge/{path}",
            headers={"X-Bridge-Key": HA_KEY},
        )
        response.raise_for_status()
        return response.json()

async def ha_post(payload: dict):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{HA_URL}/api/ms_smart_home_bridge/service",
            headers={"X-Bridge-Key": HA_KEY},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def list_devices(domain: str = "") -> list:
    """List available Home Assistant entities and their current states."""
    items = await ha_get("states")
    if domain:
        items = [item for item in items if item["entity_id"].startswith(domain + ".")]
    return items

@mcp.tool()
async def get_device_state(entity_id: str) -> dict:
    """Get the current state of a Home Assistant entity."""
    items = await ha_get("states")
    for item in items:
        if item["entity_id"] == entity_id:
            return item
    raise ValueError("Entity not found or not exposed by the Home Assistant bridge")

@mcp.tool()
async def control_device(entity_id: str, action: str, service_data: dict | None = None) -> dict:
    """Control an exposed light, switch, fan, climate device, cover, or scene."""
    if "." not in entity_id:
        raise ValueError("entity_id must include a domain, e.g. light.living_room")
    domain = entity_id.split(".", 1)[0]
    allowed = {
        "light": {"turn_on", "turn_off", "toggle"},
        "switch": {"turn_on", "turn_off", "toggle"},
        "fan": {"turn_on", "turn_off", "toggle", "set_percentage"},
        "climate": {"set_temperature", "set_hvac_mode", "turn_on", "turn_off"},
        "cover": {"open_cover", "close_cover", "stop_cover"},
        "scene": {"turn_on"},
    }
    if action not in allowed.get(domain, set()):
        raise ValueError("Action is not allowed for this entity domain")
    return await ha_post({
        "domain": domain,
        "service": action,
        "entity_id": entity_id,
        "service_data": service_data or {},
    })

class BearerKeyMiddleware:
    """Simple bearer-key gate for the MCP HTTP endpoint."""
    def __init__(self, app: ASGIApp, api_key: str):
        self.app = app
        self.api_key = api_key.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http" and scope.get("path", "").rstrip("/") == "/mcp":
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"")
            expected = b"Bearer " + self.api_key
            if auth != expected:
                body = b'{"error":"unauthorized"}'
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())],
                })
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)

if __name__ == "__main__":
    app = BearerKeyMiddleware(mcp.streamable_http_app(), MCP_KEY)
    uvicorn.run(app, host=HOST, port=PORT)
