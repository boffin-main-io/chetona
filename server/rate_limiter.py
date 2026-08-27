"""
RateLimiter — token-bucket, প্রতিটা player (owner_token বা IP দিয়ে
আলাদা করা) কে নির্দিষ্ট হারে mutating action করতে দেয়।

গেম ব্যালান্সের জন্য জরুরি: rate-limit ছাড়া একজন player সেকেন্ডে
হাজারবার whisper_rumor পাঠিয়ে বাকি সবার আগেই পুরো সভ্যতার trait
জোর করে বদলে দিতে পারতো।
"""

from __future__ import annotations

import time


class TokenBucket:
    def __init__(self, capacity: int, refill_per_second: float):
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def try_consume(self, amount: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.last_refill = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False


class RateLimiter:
    def __init__(self, capacity: int = 5, refill_per_second: float = 0.5):
        """ডিফল্ট: ৫টা action burst-এ, তারপর প্রতি ২ সেকেন্ডে ১টা পুনরায় পাওয়া যায়।"""
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.buckets: dict[str, TokenBucket] = {}

    def allow(self, identity: str) -> bool:
        bucket = self.buckets.get(identity)
        if bucket is None:
            bucket = TokenBucket(self.capacity, self.refill_per_second)
            self.buckets[identity] = bucket
        return bucket.try_consume()
