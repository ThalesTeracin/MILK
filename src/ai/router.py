import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

LOG = Path("logs/ai_router.log")
LOG.parent.mkdir(parents=True, exist_ok=True)

class AIRouter:
    """
    Roteador direto para 9Router local.
    Evita ambiguidades do SDK OpenAI e mostra o HTTP real.
    """

    def __init__(self):
        self.base_url = os.getenv("NINEROUTER_BASE_URL", "").strip().rstrip("/")
        self.model = os.getenv("NINEROUTER_MODEL", "").strip()
        self.api_key = os.getenv("NINEROUTER_API_KEY", "").strip()
        self.timeout = float(os.getenv("AI_TIMEOUT_SECONDS", "45"))
        self.last_error = None

    @property
    def enabled(self):
        return bool(self.base_url and self.model and self.api_key)

    def status(self):
        if not self.enabled:
            return "não configurado"
        return f"9Router Local [{self.model}]"

    def _headers(self):
        # OpenAI-compatible auth expected by 9Router
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _log(self, msg):
        self.last_error = msg
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
        print("⚠️ IA:", msg)

    def _post(self, payload):
        url = f"{self.base_url}/chat/completions"
        try:
            r = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout
            )
        except Exception as e:
            self._log(f"Falha de conexão: {type(e).__name__}: {e}")
            return None

        if r.status_code != 200:
            body = (r.text or "")[:3000]
            self._log(f"HTTP {r.status_code}: {body}")
            return None

        try:
            return r.json()
        except Exception as e:
            self._log(f"Resposta não-JSON: {e} | body={(r.text or '')[:2000]}")
            return None

    # Modelos de raciocinio (o glm-5.3-flash servido pelo 9Router e um)
    # cobram o raciocinio do mesmo orcamento da resposta. Com orcamento
    # curto, "reasoning" enche, "content" volta null e finish_reason vira
    # "length": a IA esta no ar e funcionando, e a MILK dizia "Nao
    # consegui responder agora". Estes tetos deixam folga para pensar e
    # ainda responder.
    TOKENS_CHAT = 1200
    TOKENS_JSON = 800

    def _conteudo(self, data):
        """Texto da resposta, ou None -- dizendo por que, quando vazio."""
        try:
            escolha = data["choices"][0]
            texto = (escolha["message"]["content"] or "").strip()
        except Exception:
            self._log(f"Formato de resposta inesperado: {json.dumps(data, ensure_ascii=False)[:1500]}")
            return None

        if texto:
            return texto

        motivo = escolha.get("finish_reason") or escolha.get("native_finish_reason")
        pensou = bool((escolha.get("message") or {}).get("reasoning"))
        if motivo == "length" and pensou:
            self._log(
                "o modelo gastou todo o max_tokens no raciocínio e não sobrou "
                "resposta. Aumente max_tokens ou troque para um modelo que "
                "não raciocina."
            )
        elif motivo == "length":
            self._log("resposta cortada por max_tokens antes de qualquer conteúdo.")
        else:
            self._log(f"a IA respondeu vazio (finish_reason={motivo!r}).")
        return None

    def test(self):
        if not self.enabled:
            return {"ok": False, "error": "Configuração ausente no .env"}

        data = self._post({
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Responda somente OK."},
                {"role": "user", "content": "Teste de conexão da MILK."}
            ],
            "temperature": 0,
            # 20 tokens nao bastam: modelos de raciocinio (o glm-5.3-flash
            # servido pelo 9Router e um) gastam o orcamento inteiro no campo
            # "reasoning" e devolvem content=null. Com 20, este teste dizia
            # que a IA estava fora do ar enquanto chat() respondia normal --
            # verificado em 28/08/2026.
            "max_tokens": 200
        })

        if not data:
            return {"ok": False, "error": self.last_error}

        try:
            text = (data["choices"][0]["message"]["content"] or "").strip()
        except Exception:
            return {"ok": False, "error": f"Formato inesperado: {json.dumps(data, ensure_ascii=False)[:1500]}"}

        return {"ok": bool(text), "reply": text, "raw": data}

    def chat(self, system, user, history=None, max_tokens=None):
        if not self.enabled:
            return None

        history = history or []
        messages = [{"role": "system", "content": system}]

        for item in history[-8:]:
            role = item.get("role")
            if role in ("user", "assistant"):
                messages.append({
                    "role": role,
                    "content": str(item.get("content", ""))
                })

        messages.append({"role": "user", "content": str(user)})

        data = self._post({
            "model": self.model,
            "messages": messages,
            "temperature": 0.35,
            "max_tokens": max_tokens or self.TOKENS_CHAT
        })

        if not data:
            return None

        return self._conteudo(data)

    def ask_json(self, system, user, max_tokens=None):
        if not self.enabled:
            return None

        data = self._post({
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system + "\nRetorne SOMENTE JSON válido, sem markdown."
                },
                {"role": "user", "content": str(user)}
            ],
            "temperature": 0,
            "max_tokens": max_tokens or self.TOKENS_JSON
        })

        if not data:
            return None

        raw = self._conteudo(data)
        if not raw:
            return None

        try:
            if raw.startswith("```"):
                raw = raw.strip("`").strip()
                if raw.lower().startswith("json"):
                    raw = raw[4:].strip()

            first = raw.find("{")
            last = raw.rfind("}")
            if first >= 0 and last > first:
                raw = raw[first:last+1]

            return json.loads(raw)
        except Exception as e:
            self._log(f"Falha ao interpretar JSON da IA: {e}")
            return None
