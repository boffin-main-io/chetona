"""
Chetona civilization server — লোকাল মেশিনে চালানোর জন্য।

চালানো:
    pip install -r requirements.txt
    python main.py

Android app কানেক্ট করবে: ws://<এই মেশিনের IP>:8765/?world=<world_id>
world_id না দিলে "default" ব্যবহার হয়। প্রতিটা আলাদা world_id একটা
আলাদা, স্বাধীন civilization — এটাই multiplayer-এর ভিত্তি: দুই প্লেয়ার
দুই world_id ব্যবহার করবে, আর "infiltrate" action দিয়ে একে অপরের
civilization-এ প্রভাব ফেলতে পারবে।

প্রোটোকল (JSON message over WebSocket):
    -> {"action": "snapshot"}
    -> {"action": "graph"}
    -> {"action": "whisper_rumor", "target_id": "...", "content": "...", "credibility": 0.6}
    -> {"action": "sow_distrust", "a_id": "...", "b_id": "..."}
    -> {"action": "incite_defection", "agent_id": "...", "credibility": 0.7}
    -> {"action": "infiltrate", "target_world": "...", "target_id": "...", "content": "...", "credibility": 0.4}
    <- world.snapshot() এর JSON, প্রতিটা request-এর পর ওই world-এর client-দের broadcast হয়

Auth: প্রতিটা world তৈরি হওয়ার সময় একটা owner_token জেনারেট হয়। যে client
প্রথম কানেক্ট করে সেই world তৈরি করে, সে প্রথম "snapshot" মেসেজে
"claim_token" ফিল্ডে টোকেনটা একবার পায় — সেটা সেভ করে রাখতে হবে। এরপর
mutating action (whisper/distrust/defection/infiltrate) পাঠাতে হলে
কানেকশনের query string-এ ?token=<owner_token> দিতে হবে, নাহলে
"unauthorized" error আসবে। snapshot/graph পড়ার জন্য টোকেন লাগে না —
স্পেকটেট করা বা infiltrate-এর target হওয়ার জন্য permission লাগে না,
শুধু নিজের world-এ action নেওয়ার জন্য লাগে।
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from urllib.parse import parse_qs, urlparse

import websockets
from websockets.server import WebSocketServerProtocol

import persistence
from config import load_config
from llama_client import LlamaReflectionClient
from rate_limiter import RateLimiter
from world_manager import WorldManager

cfg = load_config("config.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(cfg["log_file"], encoding="utf-8")],
)
log = logging.getLogger("chetona.main")

llama_client = LlamaReflectionClient(
    endpoint=cfg["llama"]["endpoint"],
    enabled=cfg["llama"]["enabled"],
    timeout_seconds=cfg["llama"]["timeout_seconds"],
)
manager = WorldManager(cfg, reflection_fn=llama_client.generate)
rate_limiter = RateLimiter(
    capacity=cfg["rate_limit"]["capacity"],
    refill_per_second=cfg["rate_limit"]["refill_per_second"],
)

# world_id -> set of connected clients, so broadcasts only go to that world's players
CLIENTS: dict[str, set[WebSocketServerProtocol]] = {}


def _world_id_from_request(ws: WebSocketServerProtocol) -> str:
    try:
        query = parse_qs(urlparse(ws.request.path).query)
        return query.get("world", ["default"])[0]
    except Exception:
        return "default"


async def broadcast_snapshot(world_id: str) -> None:
    clients = CLIENTS.get(world_id)
    if not clients:
        return
    world, _ = manager.get_or_create(world_id)
    payload = json.dumps({"type": "snapshot", "data": world.snapshot()})
    await asyncio.gather(*(c.send(payload) for c in clients), return_exceptions=True)


def _token_from_request(ws: WebSocketServerProtocol) -> str:
    try:
        query = parse_qs(urlparse(ws.request.path).query)
        return query.get("token", [""])[0]
    except Exception:
        return ""


MUTATING_ACTIONS = {"whisper_rumor", "sow_distrust", "incite_defection", "infiltrate"}


async def handler(ws: WebSocketServerProtocol) -> None:
    world_id = _world_id_from_request(ws)
    client_token = _token_from_request(ws)
    world, is_new = manager.get_or_create(world_id)
    CLIENTS.setdefault(world_id, set()).add(ws)
    log.info("client connected to world '%s': %s", world_id, ws.remote_address)

    try:
        first_message: dict = {"type": "snapshot", "data": world.snapshot()}
        if is_new:
            # whoever creates the world claims it — reveal the token once so
            # the client can persist it locally for future mutating actions
            first_message["claim_token"] = world.owner_token
            log.info("world '%s' created and claimed", world_id)
        await ws.send(json.dumps(first_message))

        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send(json.dumps({"type": "error", "error": "invalid json"}))
                continue

            action = msg.get("action")
            try:
                if action in MUTATING_ACTIONS and client_token != world.owner_token:
                    result = {"ok": False, "error": "unauthorized: wrong or missing token for this world"}
                elif action in MUTATING_ACTIONS and not rate_limiter.allow(client_token or str(ws.remote_address)):
                    result = {"ok": False, "error": "rate limited: slow down"}
                elif action == "snapshot":
                    result = {"ok": True}
                elif action == "graph":
                    result = {"ok": True, "graph": world.relationship_graph()}
                elif action == "whisper_rumor":
                    result = world.whisper_rumor(
                        msg.get("target_id", ""), msg.get("content", ""),
                        float(msg.get("credibility", 0.5)),
                    )
                elif action == "sow_distrust":
                    result = world.sow_distrust(msg.get("a_id", ""), msg.get("b_id", ""))
                elif action == "incite_defection":
                    result = world.incite_defection(
                        msg.get("agent_id", ""), float(msg.get("credibility", 0.5))
                    )
                elif action == "infiltrate":
                    target_world_id = msg.get("target_world", "")
                    target_world, _ = manager.get_or_create(target_world_id)
                    result = target_world.infiltrate_from(
                        world, msg.get("target_id", ""), msg.get("content", ""),
                        float(msg.get("credibility", 0.4)),
                    )
                    await broadcast_snapshot(target_world_id)
                else:
                    result = {"ok": False, "error": f"unknown action: {action}"}
            except Exception as e:  # a malformed action should never crash the server
                log.exception("error handling action '%s'", action)
                result = {"ok": False, "error": str(e)}

            await ws.send(json.dumps({"type": "action_result", "data": result}))
            await broadcast_snapshot(world_id)
    finally:
        CLIENTS.get(world_id, set()).discard(ws)
        log.info("client disconnected from world '%s': %s", world_id, ws.remote_address)


async def tick_loop() -> None:
    while True:
        await asyncio.sleep(cfg["tick_interval_seconds"])
        manager.tick_all()
        for world_id in list(CLIENTS.keys()):
            await broadcast_snapshot(world_id)


async def main() -> None:
    log.info("Chetona server starting on ws://%s:%d (llama hook: %s)",
              cfg["host"], cfg["port"], "on" if llama_client.enabled else "off")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler for these

    async with websockets.serve(handler, cfg["host"], cfg["port"]):
        tick_task = asyncio.create_task(tick_loop())
        await stop_event.wait()
        tick_task.cancel()
        log.info("shutting down — saving all worlds")
        manager.save_all()


if __name__ == "__main__":
    asyncio.run(main())
