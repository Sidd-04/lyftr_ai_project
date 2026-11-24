import os
import json
import hashlib
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import litellm
from litellm.caching.caching import Cache

# Set local model cost map to avoid network calls to github
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

class LLMGateway:
    def __init__(self):
        # Configure LiteLLM cache using LiteLLM's Cache(type='local')
        self.cache = Cache(type="local")
        self.default_model = os.environ.get("DEFAULT_MODEL", "gemini/gemini-2.5-flash")
        self.enable_simulation = os.environ.get("ENABLE_FAILURE_SIMULATION", "true").lower() == "true"
        self._load_keys()

    def _load_keys(self):
        raw_keys = os.environ.get("LLM_API_KEYS", "")
        if raw_keys:
            self.keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        else:
            self.keys = ["dummy-key-1", "dummy-key-2"]

    @property
    def keys_configured(self) -> int:
        return len(self.keys)

    def parse_simulation_header(self, header: Optional[str]) -> Dict[str, int]:
        if not header or not self.enable_simulation:
            return {}
        sim_map = {}
        parts = [p.strip() for p in header.split(",") if p.strip()]
        for part in parts:
            if "=" in part:
                target, status_code = part.split("=", 1)
                target = target.strip()
                try:
                    sim_map[target] = int(status_code.strip())
                except ValueError:
                    continue
        return sim_map

    def get_model_for_key(self, key: str) -> str:
        # Detect provider by key structure if multi-provider pool
        if key.startswith("gsk_"):
            return "groq/openai/gpt-oss-120b"
        elif key.startswith("AIza") or key.startswith("AQ."):
            return "gemini/gemini-2.5-flash"
        return self.default_model

    def compute_cache_key(self, model: str, messages: List[Dict[str, str]]) -> str:
        # Cache key: model + full message list (system prompt + history + new message)
        data = {
            "model": model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages]
        }
        raw_repr = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(raw_repr.encode("utf-8")).hexdigest()

    async def generate_reply(
        self,
        messages: List[Dict[str, str]],
        simulate_header: Optional[str] = None
    ) -> Dict[str, Any]:
        sim_map = self.parse_simulation_header(simulate_header)

        # Primary model for cache keying
        primary_key = self.keys[0] if self.keys else ""
        primary_model = self.get_model_for_key(primary_key)
        cache_key = self.compute_cache_key(primary_model, messages)

        start_time = time.perf_counter()

        # Check Cache first
        cached = self.cache.get_cache(cache_key=cache_key)
        if cached:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "reply": cached["reply"],
                "metadata": {
                    "resolution_source": "LLM_CACHE",
                    "model": cached["model"],
                    "latency_ms": latency_ms,
                    "input_tokens": cached["input_tokens"],
                    "output_tokens": cached["output_tokens"],
                    "key_id": None,
                    "fallback_attempts": 0
                }
            }

        fallback_attempts = 0
        last_error = None

        for idx, key in enumerate(self.keys):
            key_id = f"key_{idx + 1}"
            model_to_use = self.get_model_for_key(key)

            # Check simulated failure
            if "*" in sim_map:
                sim_status = sim_map["*"]
                fallback_attempts += 1
                last_error = f"Simulated error {sim_status}"
                continue
            elif key_id in sim_map:
                sim_status = sim_map[key_id]
                fallback_attempts += 1
                last_error = f"Simulated error {sim_status}"
                continue

            # Attempt live inference
            try:
                # If key starts with mock or dummy or in testing mode without real remote API
                if key.startswith("dummy") or key.startswith("mock") or os.environ.get("MOCK_LLM", "false").lower() == "true":
                    user_msg = messages[-1]["content"] if messages else ""
                    reply_text = f"Response to: {user_msg}"
                    in_tokens = sum(len(m["content"].split()) for m in messages) + 10
                    out_tokens = len(reply_text.split()) + 5
                    await asyncio.sleep(0.05)
                else:
                    response = await asyncio.to_thread(
                        litellm.completion,
                        model=model_to_use,
                        messages=messages,
                        api_key=key
                    )
                    reply_text = response.choices[0].message.content
                    in_tokens = response.usage.prompt_tokens if hasattr(response, 'usage') and response.usage else 25
                    out_tokens = response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else 15

                latency_ms = max(int((time.perf_counter() - start_time) * 1000), 1)

                # Store into cache with primary cache key
                cache_payload = {
                    "reply": reply_text,
                    "model": model_to_use,
                    "input_tokens": in_tokens,
                    "output_tokens": out_tokens
                }
                self.cache.add_cache(result=cache_payload, cache_key=cache_key)

                return {
                    "reply": reply_text,
                    "metadata": {
                        "resolution_source": "LIVE_INFERENCE",
                        "model": model_to_use,
                        "latency_ms": latency_ms,
                        "input_tokens": in_tokens,
                        "output_tokens": out_tokens,
                        "key_id": key_id,
                        "fallback_attempts": fallback_attempts
                    }
                }
            except Exception as e:
                fallback_attempts += 1
                last_error = str(e)
                continue

        # If every key failed
        raise RuntimeError("all providers unavailable")

gateway = LLMGateway()
