import json
import re
import httpx
from typing import Dict, Any, Optional, List


class NemotronClient:
    """
    Client for NVIDIA Nemotron 3.5 Lightning (30B-A3B MoE) NIM.
    Optimized for high-efficiency agentic tool use and reasoning on the DGX Spark.
    Exposes OpenAI-compatible completions interface.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "nemotron-3.5-lightning",
        api_key: str = "not-needed"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=300.0)

    async def check_health(self) -> bool:
        """Verify NIM/vLLM microservice availability and resolve active model name."""
        try:
            resp = await self.client.get("/models")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                if models and isinstance(models, list):
                    first_model_id = models[0].get("id")
                    if first_model_id:
                        self.model = first_model_id
                        print(f"[NemotronClient] [ONLINE] Auto-resolved active model ID: '{self.model}'")
                return True
            else:
                print(f"[NemotronClient] [WARNING] LLM health check returned HTTP {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"[NemotronClient] [OFFLINE] LLM is OFFLINE or unreachable at '{self.base_url}' ({type(e).__name__}: {e})")
        return False

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Send chat completion to Nemotron NIM / vLLM."""
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            resp = await self.client.post("/chat/completions", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                print(f"[Nemotron 35B] [OK] Response received ({len(content)} chars)")
                return content
            elif resp.status_code in (400, 404):
                print(f"[NemotronClient] Model '{self.model}' not found (HTTP {resp.status_code}), attempting auto-discovery...")
                await self.check_health()
                payload["model"] = self.model
                retry_resp = await self.client.post("/chat/completions", json=payload)
                if retry_resp.status_code == 200:
                    data = retry_resp.json()
                    content = data["choices"][0]["message"]["content"]
                    print(f"[Nemotron 35B] [OK] Response received after model resolution ({len(content)} chars)")
                    return content
            print(f"[NemotronClient] [WARNING] LLM server returned HTTP {resp.status_code}: {resp.text[:150]}")
        except httpx.ConnectError:
            print(f"[NemotronClient] [OFFLINE] LLM is OFFLINE (Connection refused at {self.base_url}).")
        except httpx.TimeoutException:
            print(f"[NemotronClient] [TIMEOUT] LLM request timed out at {self.base_url}.")
        except Exception as e:
            print(f"[NemotronClient] [ERROR] LLM connection error: {type(e).__name__}: {e}")
        return ""

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        fallback_handler: Optional[Any] = None,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Request structured JSON reasoning from Nemotron.
        Includes robust markdown JSON extraction and heuristic fallback.
        """
        prompt_with_json_instruction = (
            system_prompt + "\n\nCRITICAL INSTRUCTION: Output ONLY the final JSON object in a ```json ... ``` code block. Do NOT include thinking explanations, meta-commentary, or conversational text outside the JSON."
        )

        response_text = await self.chat(
            system_prompt=prompt_with_json_instruction,
            user_message=user_message,
            temperature=temperature,
            max_tokens=8192
        )

        if response_text:
            parsed = self._extract_json(response_text)
            if parsed:
                return parsed
            else:
                print(f"[NemotronClient] [INVALID JSON] LLM returned malformed JSON. Raw output: {response_text[:200]}...")
        else:
            print("[NemotronClient] [OFFLINE] No response received from LLM.")

        # Fallback generation if local NIM is offline or returned bad JSON
        if fallback_handler:
            print("[NemotronClient] [FALLBACK] Invoking heuristic fallback rule...")
            return fallback_handler(user_message)
        
        return {"selected_events": []}

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Clean and parse JSON from LLM output, handling reasoning preambles, fences, and minor syntax flaws."""
        if not text:
            return None

        # 1. Strip <think>...</think> reasoning tags if present
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
        if not cleaned:
            cleaned = text.strip()

        # 2. Look for all ```json ... ``` or ``` ... ``` blocks (test from last to first)
        fences = list(re.finditer(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned))
        for match in reversed(fences):
            candidate = match.group(1).strip()
            res = self._try_parse_json(candidate)
            if res is not None:
                return res

        # 3. Try parsing the whole cleaned text
        res = self._try_parse_json(cleaned)
        if res is not None:
            return res

        # 4. Find all { ... } boundaries
        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            candidate = cleaned[first_brace:last_brace + 1]
            res = self._try_parse_json(candidate)
            if res is not None:
                return res

        return None

    def _try_parse_json(self, s: str) -> Optional[Dict[str, Any]]:
        """Helper to parse JSON with trailing comma & single quote sanitization."""
        if not s:
            return None
        s = s.strip()
        try:
            val = json.loads(s)
            if isinstance(val, dict):
                return val
        except Exception:
            pass

        # Clean trailing commas: e.g. ", }" or ", ]"
        cleaned_s = re.sub(r',\s*([\]}])', r'\1', s)
        try:
            val = json.loads(cleaned_s)
            if isinstance(val, dict):
                return val
        except Exception:
            pass

        return None

    async def close(self):
        await self.client.aclose()
