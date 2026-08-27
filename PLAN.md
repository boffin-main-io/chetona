# Chetona — Production Roadmap

এই ডকুমেন্ট বলে দেয় প্রোটোটাইপ থেকে production-grade বানাতে কী কী লাগবে,
আর এই ধাপে ঠিক কতটা বানানো হলো।

## 1. Backend architecture (এই ধাপে বানানো হলো)

```
server/
  config.py        -- config.json থেকে সেটিংস লোড (tick interval, persistence path, llama endpoint)
  persistence.py    -- world state JSON-এ save/load, periodic autosave, crash-safe
  llama_client.py    -- optional local llama.cpp (llama-forge) hook agent reflection-এর জন্য, fallback সহ
  world_manager.py   -- একাধিক World instance ব্যবস্থাপনা (multiplayer-এর ভিত্তি), cross-world infiltration
  world.py, agent.py, faction.py -- আগের core simulation (আপডেট করা)
  main.py         -- WebSocket server, এখন world_id-ভিত্তিক রুটিং
  config.json       -- ডিফল্ট কনফিগ
  tests/          -- pytest ইউনিট টেস্ট (persistence, defection, cohesion)
```

### কী প্রোডাকশন-গ্রেড হলো
- **Persistence**: সার্ভার বন্ধ/ক্র্যাশ হলেও সভ্যতা হারাবে না — প্রতি N tick-এ autosave, startup-এ auto-load।
- **Multi-world**: `world_manager.py` একাধিক named world চালাতে পারে (`?world=alice`, `?world=bob`) — এটাই multiplayer-এর ভিত্তি: দুইজন প্লেয়ারের দুইটা আলাদা civilization, যার একটায় অন্যজন "infiltrate" করতে পারবে cross-world action দিয়ে।
- **LLM hook**: `llama_client.py` local `llama-server` (তোমার `llama-forge` GUI যেটা চালায়) থাকলে তার HTTP endpoint কল করে agent-এর reflection টেক্সট জেনারেট করে; না থাকলে placeholder-এ silently fallback করে — কখনো crash করবে না।
- **Config-driven**: hardcoded constants সরিয়ে `config.json` থেকে সব সেটিংস আসে।
- **Logging**: structured, ফাইলে আর stdout দুটোতেই।
- **Tests**: cohesion/defection/persistence-এর জন্য pytest স্যুট, যাতে future পরিবর্তন সিমুলেশন না ভাঙে।

## 2. এই ধাপে সব বাকি আইটেম শেষ হলো

| # | কাজ | স্ট্যাটাস |
|---|-----|-----------|
| 1 | Android: RecyclerView-ভিত্তিক real UI (agent card, faction bar) | ✅ `AgentAdapter`, `FactionAdapter`, card layouts |
| 2 | Android: reconnect-with-backoff + heartbeat ping | ✅ `ChetonaConnection.kt` — exponential backoff (1s→30s cap), OkHttp built-in ping/pong |
| 3 | World visualization (relationship graph) | ✅ `world.relationship_graph()` + offline canvas force-graph (`graph.html`, `GraphActivity.kt`) — কোনো CDN লাগে না |
| 4 | Auth/session per player | ✅ প্রতি world-এর `owner_token`, প্রথম client claim করে, mutating action-এ token যাচাই হয় |
| 5 | Docker/systemd deployment script | ✅ `deploy/Dockerfile`, `docker-compose.yml`, `install_systemd.sh`, আর Termux/proot-এর জন্য `run_persistent.sh` (auto-restart loop) |
| 6 | Rate-limiting player actions | ✅ `rate_limiter.py` — token-bucket, per-player (owner_token/IP) |

## 3. যা কোড হলো (আপডেট)

সব ফাইল zip-এ আছে। মূল সংযোজন:
- `server/rate_limiter.py`, `server/tests/test_rate_limiter.py`
- `server/world.py` — `relationship_graph()`, `owner_token`, persistence-এ token অন্তর্ভুক্ত
- `server/main.py` — token auth + rate limiting middleware, `graph` action
- `android/.../net/ChetonaConnection.kt` — reconnect/backoff/heartbeat
- `android/.../ui/AgentAdapter.kt`, `FactionAdapter.kt` + `item_agent.xml`, `item_faction.xml`
- `android/.../GraphActivity.kt` + `assets/graph.html`
- `deploy/` — সম্পূর্ণ নতুন ফোল্ডার

## 4. পরিচিত সীমাবদ্ধতা (honest scope note)

- Rate limiter আর CLIENTS ম্যাপ in-memory — সার্ভার রিস্টার্ট করলে limiter reset হয় (world state নয়, সেটা persist হয়)।
- Token চুরি হলে (network sniff) কেউ world দখল করতে পারবে — LAN-ভিত্তিক ক্যাজুয়াল গেমের জন্য যথেষ্ট, কিন্তু ইন্টারনেটে public expose করলে TLS (wss://) লাগবে, যেটা এখনো যোগ করা হয়নি।
- pytest সরাসরি এই sandbox-এ network না থাকায় install/run করা যায়নি — সব টেস্ট manual runner দিয়ে verify করা হয়েছে; তোমার মেশিনে `pip install -r requirements.txt && pytest` সরাসরি চলবে।

