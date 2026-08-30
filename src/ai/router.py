import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

from core.config import config_path

load_dotenv()

LOG = Path("logs/ai_router.log")
LOG.parent.mkdir(parents=True, exist_ok=True)


class Provedor:
    """
    Um gateway OpenAI-compatible ja resolvido: o que estava em
    config/providers.json depois de o .env sobrepor endereco, modelo e
    chave.
    """

    def __init__(self, ident, label, base_url, model, api_key):
        self.id = ident
        self.label = label
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    def __repr__(self):
        return f"<Provedor {self.id} {self.model}>"


class AIRouter:
    """
    Roteador para gateways OpenAI-compatible, em cadeia.

    A ordem vem de AI_PROVIDER_ORDER; os enderecos, de
    config/providers.json, com o .env podendo sobrepor cada campo. O
    primeiro provedor configurado responde; se ele estiver fora do ar ou
    devolver erro HTTP, a vez passa para o proximo.

    Ate a fase 33 esta classe falava com um gateway so, lido direto de
    NINEROUTER_*: com o 9Router desligado a MILK ficava muda, sem ter
    para onde cair. AI_PROVIDER_ORDER e providers.json ja existiam no
    .env e no repositorio, mas nenhum codigo em execucao os lia.

    A queda para o proximo provedor acontece so no transporte -- conexao
    recusada, timeout, HTTP diferente de 200. Resposta 200 com conteudo
    vazio nao troca de provedor: isso e orcamento de tokens curto, e
    repetir noutro gateway daria o mesmo resultado, gastando o dobro.
    """

    def __init__(self):
        self.timeout = float(os.getenv("AI_TIMEOUT_SECONDS", "45"))
        self.last_error = None
        self.provedores = self._carregar_provedores()

    # ------------------------------------------------------------------
    # Montagem da cadeia
    # ------------------------------------------------------------------

    def _carregar_provedores(self):
        catalogo = self._catalogo()

        ordem = [
            item.strip()
            for item in os.getenv("AI_PROVIDER_ORDER", "").split(",")
            if item.strip()
        ]
        # Sem ordem declarada vale a ordem do arquivo, para que quem
        # nunca rodou o configurador ainda tenha uma cadeia. Chaves
        # iniciadas por "_" sao comentario (a convencao ja usada em
        # config/settings.json), nao provedor.
        if not ordem:
            ordem = [ident for ident in catalogo if not ident.startswith("_")]

        provedores = []
        for ident in ordem:
            cfg = catalogo.get(ident)
            if not isinstance(cfg, dict):
                self._log(
                    f"provedor '{ident}' está em AI_PROVIDER_ORDER mas não "
                    "existe em providers.json -- ignorado"
                )
                continue

            provedor = self._resolver(ident, cfg)
            if provedor is not None:
                provedores.append(provedor)

        return provedores

    def _catalogo(self):
        caminho = config_path("providers.json")
        try:
            # utf-8-sig: o arquivo pode ter sido salvo por editor do
            # Windows com BOM, e json.loads engasga com ele.
            return json.loads(caminho.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            self._log(f"providers.json não encontrado em {caminho}")
            return {}
        except Exception as e:
            self._log(f"providers.json inválido: {type(e).__name__}: {e}")
            return {}

    def _resolver(self, ident, cfg):
        """Devolve o Provedor pronto, ou None quando falta configuração."""
        base_url = self._do_env(cfg.get("base_url_env")) or (cfg.get("base_url") or "").strip()
        model = self._do_env(cfg.get("model_env")) or (cfg.get("model") or "").strip()
        api_key = self._do_env(cfg.get("api_key_env"))

        if not base_url or not model:
            return None
        if cfg.get("requires_key", True) and not api_key:
            return None

        return Provedor(ident, cfg.get("label", ident), base_url, model, api_key)

    @staticmethod
    def _do_env(nome):
        if not nome:
            return ""
        return os.getenv(nome, "").strip()

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    @property
    def ativo(self):
        """O provedor que responde primeiro, ou None."""
        return self.provedores[0] if self.provedores else None

    @property
    def enabled(self):
        return bool(self.provedores)

    @property
    def base_url(self):
        return self.ativo.base_url if self.ativo else ""

    @property
    def model(self):
        return self.ativo.model if self.ativo else ""

    @property
    def api_key(self):
        return self.ativo.api_key if self.ativo else ""

    def status(self):
        if not self.provedores:
            return "não configurado"

        texto = f"{self.ativo.label} [{self.ativo.model}]"
        reservas = len(self.provedores) - 1
        if reservas:
            texto += f" (+{reservas} de reserva)"
        return texto

    def _headers(self, provedor):
        # Auth OpenAI-compatible, aceita por 9Router, OmniRoute e FreeLLMAPI
        cabecalhos = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if provedor.api_key:
            cabecalhos["Authorization"] = f"Bearer {provedor.api_key}"
        return cabecalhos

    def _log(self, msg):
        self.last_error = msg
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
        print("⚠️ IA:", msg)

    # ------------------------------------------------------------------
    # Transporte
    # ------------------------------------------------------------------

    def _post(self, payload):
        if not self.provedores:
            self._log("nenhum provedor configurado no .env")
            return None

        falhas = []
        for provedor in self.provedores:
            # Cada gateway tem o proprio nome de modelo; o payload chega
            # com o do ativo e precisa ser reescrito a cada tentativa.
            corpo = dict(payload)
            corpo["model"] = provedor.model

            data = self._tentar(provedor, corpo)
            if data is not None:
                return data

            falhas.append(f"{provedor.label} ({self.last_error})")

        self._log("nenhum provedor da cadeia respondeu: " + " | ".join(falhas))
        return None

    def _tentar(self, provedor, payload):
        url = f"{provedor.base_url}/chat/completions"
        try:
            r = requests.post(
                url,
                headers=self._headers(provedor),
                json=payload,
                timeout=self.timeout
            )
        except Exception as e:
            self._log(f"{provedor.label}: falha de conexão: {type(e).__name__}: {e}")
            return None

        if r.status_code != 200:
            body = (r.text or "")[:3000]
            self._log(f"{provedor.label}: HTTP {r.status_code}: {body}")
            return None

        try:
            return r.json()
        except Exception as e:
            self._log(
                f"{provedor.label}: resposta não-JSON: {e} | "
                f"body={(r.text or '')[:2000]}"
            )
            return None

    # Modelos de raciocinio (o glm-5.3-flash servido pelo 9Router e um)
    # cobram o raciocinio do mesmo orcamento da resposta. Com orcamento
    # curto, "reasoning" enche, "content" volta null e finish_reason vira
    # "length": a IA esta no ar e funcionando, e a MILK dizia "Nao
    # consegui responder agora". Estes tetos deixam folga para pensar e
    # ainda responder.
    # Ajustáveis pelo .env: quem trocar para um modelo que não raciocina
    # pode baixar, e quem pedir resposta longa a um que raciocina precisa
    # subir. 2000 cobre o raciocínio do glm-5.3-flash mais uma resposta de
    # alguns parágrafos. Medido contra o 9Router real: com 1200 o conteúdo
    # nem começava; com 2000 a resposta saía cortada no meio da frase e o
    # ask_json com 800 ainda estourava no raciocínio, derrubando o NLU
    # para o chat. Custa latência -- uma resposta levou 49 s -- mas
    # resposta cortada é pior do que resposta lenta.
    TOKENS_CHAT = int(os.getenv("AI_MAX_TOKENS_CHAT", "3000"))
    TOKENS_JSON = int(os.getenv("AI_MAX_TOKENS_JSON", "1500"))

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
