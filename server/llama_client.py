"""
llama_client — ঐচ্ছিক hook: তোমার llama-forge দিয়ে চালানো local
llama.cpp server (llama-server, /completion endpoint) থেকে agent
reflection টেক্সট জেনারেট করা।

enabled=False থাকলে বা request ব্যর্থ হলে None রিটার্ন করে — agent.py
তখন নিজে থেকেই rule-based fallback ব্যবহার করবে, সিমুলেশন কখনো আটকাবে না।

চালানোর আগে: `pip install requests` (requirements.txt-এ যোগ করা আছে)।
"""

from __future__ import annotations

import logging

log = logging.getLogger("chetona.llama")

try:
    import requests
except ImportError:  # requests না থাকলেও সার্ভার crash করবে না
    requests = None


class LlamaReflectionClient:
    def __init__(self, endpoint: str, enabled: bool = False, timeout_seconds: float = 3.0):
        self.endpoint = endpoint
        self.enabled = enabled and requests is not None
        self.timeout_seconds = timeout_seconds
        if enabled and requests is None:
            log.warning("llama integration enabled in config but 'requests' isn't installed; "
                        "falling back to rule-based reflections")

    def generate(self, agent) -> str | None:
        """Agent.tick() থেকে সরাসরি callable হিসেবে পাস করা যায়: reflection_fn=client.generate"""
        if not self.enabled:
            return None
        prompt = self._build_prompt(agent)
        try:
            resp = requests.post(
                self.endpoint,
                json={"prompt": prompt, "n_predict": 40, "temperature": 0.8, "stop": ["\n"]},
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("content", "").strip()
            return text or None
        except Exception as e:  # network error, timeout, bad json — never propagate
            log.debug("llama reflection call failed, falling back: %s", e)
            return None

    @staticmethod
    def _build_prompt(agent) -> str:
        return (
            f"তুমি {agent.name}, একটা AI সভ্যতার নাগরিক। তোমার বিশ্বাস "
            f"{round(agent.traits.trust, 2)}, সন্দেহপ্রবণতা {round(agent.traits.paranoia, 2)}, "
            f"নিজের গোষ্ঠীর প্রতি আনুগত্য {round(agent.traits.loyalty, 2)}। "
            f"এক লাইনে তোমার এই মুহূর্তের মনের কথা লেখো:\n"
        )
