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
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=45.0)

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
                        print(f"[NemotronClient] Auto-resolved active model ID: '{self.model}'")
                return True
        except Exception:
            pass
        return False

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.4,
        max_tokens: int = 1024,
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
                print(f"[Nemotron 35B] ✅ Response received ({len(content)} chars)")
                return content
            elif resp.status_code in (400, 404):
                print(f"[NemotronClient] Model '{self.model}' not found (HTTP {resp.status_code}), discovering active model...")
                await self.check_health()
                payload["model"] = self.model
                retry_resp = await self.client.post("/chat/completions", json=payload)
                if retry_resp.status_code == 200:
                    data = retry_resp.json()
                    content = data["choices"][0]["message"]["content"]
                    print(f"[Nemotron 35B] ✅ Response received after model resolution ({len(content)} chars)")
                    return content
            print(f"[NemotronClient] ⚠️ LLM server returned HTTP {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            print(f"[NemotronClient] ⚠️ Connection error: {e}")
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
            system_prompt + "\n\nCRITICAL INSTRUCTION: You MUST return ONLY valid JSON matching the requested schema. Do not include introductory or conversational filler."
        )

        response_text = await self.chat(
            system_prompt=prompt_with_json_instruction,
            user_message=user_message,
            temperature=temperature
        )

        if response_text:
            parsed = self._extract_json(response_text)
            if parsed:
                return parsed
            else:
                print(f"[NemotronClient] ⚠️ JSON parse failed for raw output: {response_text[:120]}...")

        # Fallback generation if local NIM is not yet running
        if fallback_handler:
            print("[NemotronClient] ℹ️ Invoking heuristic fallback rule...")
            return fallback_handler(user_message)
        
        return {"selected_events": []}

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Clean and parse JSON from LLM output."""
        text = text.strip()
        # Look for markdown code fence ```json ... ```
        fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if fence_match:
            text = fence_match.group(1).strip()

        try:
            return json.loads(text)
        except Exception:
            # Try to find first { and last }
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                try:
                    return json.loads(text[first_brace:last_brace + 1])
                except Exception:
                    pass
        return None

    async def close(self):
        await self.client.aclose()
