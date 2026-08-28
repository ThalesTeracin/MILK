# Fase 33 — Presence + Avatar + Skills — Plano de Implementação

> **Para executores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> superpowers:subagent-driven-development (recomendado) ou
> superpowers:executing-plans para implementar tarefa a tarefa. Os passos
> usam caixas (`- [ ]`) para acompanhamento.

**Objetivo:** Uma única fonte de verdade para o estado da MILK, as skills
alcançáveis por voz, e a interface livre para animar enquanto o cérebro
trabalha.

**Arquitetura:** Um módulo em `core/` passa a ser dono do estado de
atividade, guardando em memória e publicando em `data/milk_runtime_state.json`
com carimbo de tempo — o mini overlay, que roda em outro processo, lê dali e
sabe distinguir estado vivo de estado velho. O `AdvancedSkillRouter`, hoje
órfão, entra no `MilkCore.handle` antes do NLU e passa a usar o
`PermissionManager` da fase 2 em vez do seu próprio conjunto `RISKY`. E
`handle()` sai da thread do Tk para uma thread de trabalho, para o avatar
continuar animando durante uma chamada de IA longa.

**Stack:** Python 3.14 (mínimo 3.12), pytest 8, Tkinter, sqlite3.

**Spec:** `docs/superpowers/specs/2026-08-28-fase-33-presence-avatar-skills-design.md`

## Estado da branch ao começar

`fase-33` já tem três commits, e eles mudam o que as tarefas abaixo
encontram:

- `2a4ae8f` — a spec desta fase.
- `5e37b7c` — **`_poll_events`, `_animate` e `_idle_watch` já receberam
  `try/except` e reagendamento em `finally`**, e já existe
  `tests/test_unified_app_loops.py`. A Task 6 constrói em cima disso; não
  reintroduza a proteção, e não crie um segundo arquivo de teste para esses
  laços.
- `39c0914` — `Testar_Sistema.py` ganhou a seção 6b, e `AIRouter.test()`
  passou a pedir 200 tokens.

A spec previa um arquivo `tests/test_unified_app_eventos.py`. Ele **não** vai
existir: `tests/test_unified_app_loops.py` já ocupa esse lugar, e a Task 6
acrescenta casos a ele.

## Restrições globais

- Python mínimo: **3.12**. Máquina de referência: 3.14.7.
- Imports absolutos com `src/` no `sys.path` (`from core.config import ...`),
  nunca relativos (`from ..core import`). Import relativo quebra neste
  projeto.
- Testes em `tests/`, rodados de `C:\JARVIS` com `python -m pytest`.
  `tests/conftest.py` já põe `src/` no path.
- Tudo escrito para humanos — comentários, docstrings, mensagens, commits —
  em português.
- Configuração de máquina vai para `config/local/`, resolvida por
  `core.config.config_path`.
- Nenhum teste pode depender de microfone, de janela Tk, de rede, de git
  real ou do navegador.
- **O cérebro de IA é o 9Router local na porta 20128.** Se algum passo de
  verificação manual precisar da MILK respondendo, o 9Router tem que estar
  no ar: `9router -t -n`.

---

### Task 1: O módulo dono do estado

**Arquivos:**
- Criar: `src/core/activity_state.py`
- Criar: `tests/test_activity_state.py`

**Interfaces:**
- Consome: nada.
- Produz:
  - `definir_atividade(nome: str) -> None` — aceita só `"idle"`,
    `"listening"`, `"thinking"`, `"speaking"`; levanta `ValueError` em
    qualquer outro valor.
  - `atividade() -> str` — o valor em memória.
  - `pulsar() -> None` — regrava o carimbo sem mudar a atividade.
  - `ler_do_arquivo(agora: float | None = None) -> tuple[str, bool]` —
    devolve `(atividade, fresco)`.
  - Constantes `ARQUIVO: Path`, `ATIVIDADES: tuple[str, ...]`,
    `PADRAO: str`, `LIMITE_DE_FRESCOR: float`.

- [ ] **Passo 1: Escrever o teste que falha**

Criar `tests/test_activity_state.py`:

```python
"""
Testes de src/core/activity_state.py.

O modulo e o dono unico da atividade da MILK: guarda em memoria para quem
esta no mesmo processo e publica em data/milk_runtime_state.json para o
mini overlay, que roda em outro processo.

O carimbo de tempo existe porque o arquivo sobrevive ao processo. Sem ele,
com a MILK fechada o mini mostraria "pensando" para sempre.
"""
import json

import pytest

import core.activity_state as estado_mod
from core.activity_state import (
    atividade,
    definir_atividade,
    ler_do_arquivo,
    pulsar,
)


@pytest.fixture(autouse=True)
def arquivo_isolado(tmp_path, monkeypatch):
    """Cada teste escreve no seu proprio arquivo e comeca em 'idle'."""
    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    monkeypatch.setattr(estado_mod, "_atividade", "idle")
    return tmp_path / "runtime.json"


# ------------------------------------------------------- memoria

def test_comeca_ocioso():
    assert atividade() == "idle"


def test_definir_muda_o_valor_em_memoria():
    definir_atividade("thinking")

    assert atividade() == "thinking"


def test_atividade_desconhecida_e_recusada():
    """Um erro de digitacao viraria um estado que nenhum overlay sabe pintar."""
    with pytest.raises(ValueError):
        definir_atividade("pensando")


# -------------------------------------------------------- arquivo

def test_definir_publica_no_arquivo(arquivo_isolado):
    definir_atividade("speaking")

    dados = json.loads(arquivo_isolado.read_text(encoding="utf-8"))
    assert dados["activity"] == "speaking"
    assert isinstance(dados["at"], (int, float))


def test_le_de_volta_o_que_escreveu():
    definir_atividade("listening")

    assert ler_do_arquivo() == ("listening", True)


def test_sem_arquivo_devolve_ocioso_e_nao_fresco():
    assert ler_do_arquivo() == ("idle", False)


def test_arquivo_corrompido_devolve_ocioso_e_nao_fresco(arquivo_isolado):
    arquivo_isolado.write_text("{isso nao e json", encoding="utf-8")

    assert ler_do_arquivo() == ("idle", False)


def test_atividade_desconhecida_no_arquivo_nao_e_aceita(arquivo_isolado):
    """Arquivo de uma versao antiga, ou editado a mao."""
    arquivo_isolado.write_text(
        json.dumps({"activity": "dancando", "at": 1.0}), encoding="utf-8"
    )

    assert ler_do_arquivo(agora=1.0) == ("idle", False)


# -------------------------------------------------------- frescor

def test_carimbo_velho_nao_e_fresco(arquivo_isolado):
    """O sintoma que isso evita: MILK fechada e o mini dizendo 'pensando'."""
    arquivo_isolado.write_text(
        json.dumps({"activity": "thinking", "at": 1000.0}), encoding="utf-8"
    )

    nome, fresco = ler_do_arquivo(agora=1000.0 + estado_mod.LIMITE_DE_FRESCOR + 1)

    assert nome == "thinking"
    assert fresco is False


def test_carimbo_dentro_do_limite_e_fresco(arquivo_isolado):
    arquivo_isolado.write_text(
        json.dumps({"activity": "thinking", "at": 1000.0}), encoding="utf-8"
    )

    assert ler_do_arquivo(agora=1000.5) == ("thinking", True)


def test_pulsar_renova_o_carimbo_sem_mudar_a_atividade(arquivo_isolado):
    definir_atividade("listening")
    arquivo_isolado.write_text(
        json.dumps({"activity": "listening", "at": 1.0}), encoding="utf-8"
    )
    assert ler_do_arquivo()[1] is False

    pulsar()

    assert ler_do_arquivo() == ("listening", True)


# ---------------------------------------------------------- falha

def test_falha_ao_gravar_nao_derruba_a_voz(monkeypatch, capsys):
    """
    O estado e conveniencia de interface. Disco cheio ou arquivo travado
    por antivirus nao pode impedir a MILK de continuar funcionando.
    """
    def explode(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(estado_mod.Path, "write_text", explode)

    definir_atividade("speaking")

    assert atividade() == "speaking"
    assert "milk" in capsys.readouterr().out.lower()
```

- [ ] **Passo 2: Rodar o teste e confirmar que falha**

Rodar: `python -m pytest tests/test_activity_state.py -v`
Esperado: FAIL com `ModuleNotFoundError: No module named 'core.activity_state'`

- [ ] **Passo 3: Implementar o mínimo**

Criar `src/core/activity_state.py`:

```python
"""
Dono unico do estado de atividade da MILK.

Ate a fase 33 havia duas verdades sobre o que a MILK estava fazendo:
MilkCore.activity, em memoria, que movia o overlay grande; e
data/milk_runtime_state.json, lido pelo mini overlay -- que ninguem nunca
escrevia. O mini mostrava o estado padrao para sempre.

Agora ha um dono so. Ele guarda em memoria para quem esta no mesmo
processo (o overlay grande le a 120 ms e nao pode tocar disco nessa
frequencia) e publica no arquivo para o mini overlay, que roda em outro
processo.

O carimbo de tempo existe porque o arquivo sobrevive ao processo. Sem ele,
com a MILK fechada o mini mostraria "pensando" para sempre. Quem le decide
o que fazer com estado velho; este modulo so diz se e fresco.

Este modulo fica em core/ e nao em avatar/ porque quem escreve e o
MilkCore, e o cerebro nao deve importar de um pacote de interface.
"""

import json
import threading
import time
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[2] / "data" / "milk_runtime_state.json"

ATIVIDADES = ("idle", "listening", "thinking", "speaking")
PADRAO = "idle"

# Cinco segundos: o UnifiedApp chama pulsar() de segundo em segundo, entao
# cinco pulsos podem se perder antes de o mini declarar a MILK morta.
LIMITE_DE_FRESCOR = 5.0

_LOCK = threading.Lock()
_atividade = PADRAO


def definir_atividade(nome):
    """Muda a atividade e publica. Recusa nome fora de ATIVIDADES."""
    global _atividade
    if nome not in ATIVIDADES:
        raise ValueError(f"atividade desconhecida: {nome!r}")
    with _LOCK:
        _atividade = nome
    _gravar(nome)


def atividade():
    """O valor em memoria. Para quem esta no mesmo processo."""
    with _LOCK:
        return _atividade


def pulsar():
    """Regrava o carimbo sem mudar a atividade.

    A atividade so e escrita quando muda. Com a MILK parada ouvindo, o
    carimbo envelheceria e o mini a declararia desligada enquanto ela esta
    viva.
    """
    _gravar(atividade())


def ler_do_arquivo(agora=None):
    """
    Devolve (atividade, fresco). Para quem esta em OUTRO processo.

    Devolve (PADRAO, False) quando o arquivo nao existe, esta corrompido,
    tem formato inesperado ou traz atividade que este modulo nao conhece.
    """
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        nome = dados["activity"]
        carimbo = float(dados["at"])
    except Exception:
        return (PADRAO, False)

    if nome not in ATIVIDADES:
        return (PADRAO, False)

    agora = time.time() if agora is None else agora
    return (nome, (agora - carimbo) <= LIMITE_DE_FRESCOR)


def _gravar(nome):
    """Publica no arquivo. Falhar aqui nunca pode derrubar a MILK."""
    try:
        ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO.write_text(
            json.dumps({"activity": nome, "at": time.time()}),
            encoding="utf-8",
        )
    except Exception as e:
        print(
            f"⚠️ MILK: não consegui publicar o estado em {ARQUIVO} "
            f"({type(e).__name__}: {e}); o mini overlay pode ficar parado."
        )
```

- [ ] **Passo 4: Rodar os testes e confirmar que passam**

Rodar: `python -m pytest tests/test_activity_state.py -v`
Esperado: PASS nos 12 testes.

- [ ] **Passo 5: Commitar**

```bash
git add src/core/activity_state.py tests/test_activity_state.py
git commit -m "feat: um dono único para o estado de atividade da MILK"
```

---

### Task 2: MilkCore e UnifiedApp passam a usar o módulo

**Arquivos:**
- Modificar: `src/core/orchestrator.py:58` (o `self.activity="idle"` do
  `__init__`) e `src/core/orchestrator.py:60-65` (o `say()`)
- Modificar: `src/presence/unified_app.py` — `_animate`, `_listen_loop`,
  `_idle_watch`
- Criar: `tests/test_orchestrator_atividade.py`

**Interfaces:**
- Consome da Task 1: `definir_atividade`, `atividade`, `pulsar`.
- Produz: `MilkCore` deixa de expor o atributo `activity`. Quem quiser
  saber a atividade chama `core.activity_state.atividade()`.

- [ ] **Passo 1: Escrever o teste que falha**

Criar `tests/test_orchestrator_atividade.py`:

```python
"""
Testes da ligacao entre MilkCore e core.activity_state.

Instanciar MilkCore de verdade exigiria microfone, Whisper e provedor de
IA no ar. Estes testes exercitam so o metodo say(), com o objeto montado
por __new__ e os colaboradores que say() usa trocados por falsos.
"""
import pytest

import core.activity_state as estado_mod
from core.activity_state import atividade
from core.orchestrator import MilkCore


class FalanteFalso:
    def __init__(self, ao_falar=None):
        self.ditos = []
        self.ao_falar = ao_falar

    def say(self, texto):
        self.ditos.append(texto)
        if self.ao_falar:
            self.ao_falar()


class MemoriaFalsa:
    def __init__(self):
        self.mensagens = []

    def assistant_message(self, texto):
        self.mensagens.append(texto)


@pytest.fixture(autouse=True)
def estado_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    monkeypatch.setattr(estado_mod, "_atividade", "idle")


@pytest.fixture
def core():
    c = MilkCore.__new__(MilkCore)
    c.state = "ready"
    c.speaker = FalanteFalso()
    c.memory = MemoriaFalsa()
    return c


def test_say_marca_falando_enquanto_fala(core):
    visto = []
    core.speaker = FalanteFalso(ao_falar=lambda: visto.append(atividade()))

    core.say("olá")

    assert visto == ["speaking"]


def test_depois_de_falar_volta_a_ouvir(core):
    core.say("olá")

    assert atividade() == "listening"


def test_dormindo_volta_para_ocioso(core):
    core.state = "sleep"

    core.say("vou ficar em espera")

    assert atividade() == "idle"


def test_falha_do_falante_nao_deixa_o_estado_presa_em_falando(core):
    """O finally do say() existe para isso; o teste garante que continua lá."""
    def explode():
        raise RuntimeError("TTS fora do ar")

    core.speaker = FalanteFalso(ao_falar=explode)

    with pytest.raises(RuntimeError):
        core.say("olá")

    assert atividade() == "listening"


def test_milkcore_nao_tem_mais_o_atributo_activity(core):
    """
    O ponto da fase: uma verdade so. Um atributo sobrevivente viraria a
    segunda, e o overlay leria o valor errado sem ninguem perceber.
    """
    assert not hasattr(core, "activity")
```

- [ ] **Passo 2: Rodar o teste e confirmar que falha**

Rodar: `python -m pytest tests/test_orchestrator_atividade.py -v`
Esperado: FAIL — `say()` ainda escreve `self.activity`, então
`test_say_marca_falando_enquanto_fala` vê `"idle"` e
`test_milkcore_nao_tem_mais_o_atributo_activity` encontra o atributo.

- [ ] **Passo 3: Trocar no orchestrator**

Em `src/core/orchestrator.py`, acrescentar ao bloco de imports do topo:

```python
from core.activity_state import definir_atividade
```

Apagar as cinco linhas de comentário e a atribuição `self.activity="idle"`
no fim do `__init__` (`src/core/orchestrator.py:53-58`), e pôr no lugar:

```python
        # Estado fino de atividade (ouvindo/pensando/falando). Desde a fase
        # 33 o dono é core/activity_state.py, que guarda em memória e publica
        # em data/milk_runtime_state.json para o mini overlay, que roda em
        # outro processo. Antes isso era um atributo daqui, e o arquivo era
        # uma segunda verdade que ninguém escrevia.
        definir_atividade("idle")
```

Trocar o `say()`:

```python
    def say(self,text):
        definir_atividade("speaking")
        try:
            self.speaker.say(text)
        finally:
            definir_atividade("idle" if self.state=="sleep" else "listening")
        try:
            self.memory.assistant_message(text)
        except Exception:
            pass
```

- [ ] **Passo 4: Rodar os testes e confirmar que passam**

Rodar: `python -m pytest tests/test_orchestrator_atividade.py -v`
Esperado: PASS nos 5 testes.

- [ ] **Passo 5: Trocar no UnifiedApp**

Em `src/presence/unified_app.py`, acrescentar aos imports:

```python
from core.activity_state import atividade, definir_atividade, pulsar
```

Em `_animate`, trocar a leitura do atributo:

```python
                activity = atividade()
```

Em `_listen_loop`, trocar as duas atribuições:

```python
            definir_atividade("listening")
```

e

```python
                definir_atividade("thinking")
```

Em `_idle_watch`, trocar `self.core.activity = "idle"` por:

```python
                    definir_atividade("idle")
```

e acrescentar o pulso, dentro do `try`, depois do `if`:

```python
            # O estado só é escrito quando muda. Sem este pulso, a MILK
            # parada ouvindo teria o carimbo envelhecendo e o mini overlay
            # a declararia desligada enquanto ela está viva.
            pulsar()
```

Atualizar os comentários que citam `MilkCore.activity`
(`src/presence/unified_app.py:46`, `:169` e `:211`) para citar
`core.activity_state`.

- [ ] **Passo 6: Rodar a suíte inteira**

Rodar: `python -m pytest -q`
Esperado: PASS em tudo. `tests/test_unified_app_loops.py` continua passando
— ele monta `app.core` com um objeto falso que tem `activity`, e esse
atributo simplesmente deixa de ser lido.

- [ ] **Passo 7: Commitar**

```bash
git add src/core/orchestrator.py src/presence/unified_app.py tests/test_orchestrator_atividade.py
git commit -m "feat: MilkCore e overlay passam a usar o dono do estado"
```

---

### Task 3: O mini overlay lê o estado de verdade

**Arquivos:**
- Modificar: `src/overlay/mini_overlay.py:4` (o import) e o `_tick`
- Modificar: `src/avatar/runtime_state.py`, `src/avatar/avatar_window.py`,
  `src/avatar/speaker_state_patch.py`, `Testar_Avatar_Animado.py` — só o
  cabeçalho
- Criar: `tests/test_mini_overlay_rotulo.py`

**Interfaces:**
- Consome da Task 1: `ler_do_arquivo`.
- Produz: `rotulo_de(atividade: str, fresco: bool) -> str`, em
  `src/overlay/mini_overlay.py`, testável sem Tk.

- [ ] **Passo 1: Escrever o teste que falha**

Criar `tests/test_mini_overlay_rotulo.py`:

```python
"""
Testes do rotulo do mini overlay.

O rotulo e a unica logica do mini que da para testar sem abrir janela,
entao ela sai do _tick para uma funcao propria. O caso que importa e o
estado velho: com a MILK fechada, o arquivo continua no disco dizendo
"thinking", e o mini nao pode repetir isso.
"""
from overlay.mini_overlay import rotulo_de


def test_ouvindo():
    assert rotulo_de("listening", True) == "MILK · OUVINDO"


def test_pensando():
    assert rotulo_de("thinking", True) == "MILK · PENSANDO"


def test_falando():
    assert rotulo_de("speaking", True) == "MILK · FALANDO"


def test_ociosa_e_fresca_esta_pronta():
    assert rotulo_de("idle", True) == "MILK · PRONTA"


def test_estado_velho_vira_desligada():
    """MILK fechada: o arquivo ficou para tras dizendo 'pensando'."""
    assert rotulo_de("thinking", False) == "MILK · DESLIGADA"


def test_ociosa_e_velha_tambem_e_desligada():
    assert rotulo_de("idle", False) == "MILK · DESLIGADA"
```

- [ ] **Passo 2: Rodar o teste e confirmar que falha**

Rodar: `python -m pytest tests/test_mini_overlay_rotulo.py -v`
Esperado: FAIL com `ImportError: cannot import name 'rotulo_de'`

- [ ] **Passo 3: Implementar**

Em `src/overlay/mini_overlay.py`, trocar o import da linha 4:

```python
from core.activity_state import ler_do_arquivo
```

Acrescentar, logo depois de `ASSET=Path("assets/milk_avatar.png")`:

```python
ROTULOS = {
    "listening": "OUVINDO",
    "thinking": "PENSANDO",
    "speaking": "FALANDO",
    "idle": "PRONTA",
}


def rotulo_de(atividade, fresco):
    """
    O texto do mini overlay.

    Estado nao fresco vira DESLIGADA: o arquivo sobrevive ao processo, e
    sem isso a MILK fechada ficaria "pensando" para sempre na tela.
    """
    if not fresco:
        return "MILK · DESLIGADA"
    return "MILK · " + ROTULOS.get(atividade, "PRONTA")
```

Trocar as duas linhas do `_tick` que montavam o rótulo:

```python
        nome, fresco = ler_do_arquivo()
        self.canvas.create_text(110,18,text=rotulo_de(nome, fresco),fill="#67e8ff",font=("Segoe UI",10,"bold"))
```

- [ ] **Passo 4: Rodar os testes e confirmar que passam**

Rodar: `python -m pytest tests/test_mini_overlay_rotulo.py -v`
Esperado: PASS nos 6 testes.

- [ ] **Passo 5: Marcar os arquivos substituídos**

Pôr no topo de `src/avatar/runtime_state.py`,
`src/avatar/avatar_window.py`, `src/avatar/speaker_state_patch.py` e
`Testar_Avatar_Animado.py` o bloco abaixo, ajustando a última linha ao
arquivo. Nenhum deles é apagado: `Testar_Avatar_Animado.py` importa
`runtime_state`, e apagar um sem o outro deixaria código quebrado no
repositório.

```python
# =============================================================================
# SUBSTITUÍDO (Fase 33 - integração Presence + Avatar + Skills, 2026-08-28).
# O estado de atividade da MILK passou a ter um dono único em
# src/core/activity_state.py, que guarda em memória e publica em
# data/milk_runtime_state.json com carimbo de tempo. Este arquivo pertence
# ao mecanismo anterior, cujos campos (speaking/listening/thinking/emotion/
# last_text) nunca chegaram a ser escritos por ninguém.
# Mantido apenas como referência histórica. Não editar/usar.
# =============================================================================
```

- [ ] **Passo 6: Conferir que nada mais importa o módulo antigo**

Rodar: `grep -rn "runtime_state" --include=*.py . | grep -v __pycache__ | grep -v third_party`
Esperado: só `src/avatar/runtime_state.py` (ele mesmo),
`src/avatar/avatar_window.py`, `src/avatar/speaker_state_patch.py` e
`Testar_Avatar_Animado.py` — todos já marcados como substituídos. Se
`mini_overlay.py` aparecer, o passo 3 não foi aplicado.

- [ ] **Passo 7: Rodar a suíte e a verificação de fumaça**

Rodar: `python -m pytest -q`
Esperado: PASS em tudo.

Rodar: `python Testar_Sistema.py`
Esperado: `RESULTADO: tudo passou`. A seção 3 importa `overlay.mini_overlay`
e `avatar.runtime_state`; ambos precisam continuar importáveis.

- [ ] **Passo 8: Commitar**

```bash
git add src/overlay/mini_overlay.py src/avatar/ Testar_Avatar_Animado.py tests/test_mini_overlay_rotulo.py
git commit -m "feat: o mini overlay mostra o estado real e sabe quando é velho"
```

---

### Task 4: As skills devolvem frase e passam pelo gate certo

**Arquivos:**
- Modificar: `src/skills/skill_registry.py`
- Modificar: `src/skills/advanced_router.py`
- Modificar: `config/skills.json`
- Criar: `tests/test_skill_router.py`

**Interfaces:**
- Consome: `security.permission_manager.PermissionManager.check(action) ->
  {"allowed": bool, "confirm": bool, "reason": str}`.
- Produz:
  - `AdvancedSkillRouter(ai=None, mcp_manager=None, permissions=None)`.
  - `route_local(text) -> dict | None` — `{"type": "builtin", "skill":
    str, "args": dict}`.
  - `execute(plan, confirmed=False) -> dict` — `{"ok": bool, "fala": str,
    "dados": dict}`, ou `{"requires_confirmation": True, "skill": str,
    "fala": str}`.
  - Cada método de `BuiltinSkills` devolve `{"ok", "fala", "dados"}`.

- [ ] **Passo 1: Escrever o teste que falha**

Criar `tests/test_skill_router.py`:

```python
"""
Testes de src/skills/advanced_router.py.

Ate a fase 33 este router era orfao: nenhum ponto do aplicativo o
importava, so Testar_Fase31.py. As skills nunca rodaram por voz.

Duas coisas mudam e sao o que estes testes protegem: o gate passou a ser o
PermissionManager da fase 2 (o conjunto RISKY proprio do router era uma
copia pior, sem distinguir negar de confirmar), e as skills devolvem uma
frase falavel alem dos dados.

Nenhum teste toca git, disco ou navegador de verdade.
"""
import pytest

from skills.advanced_router import AdvancedSkillRouter


class PermissoesFalsas:
    """PermissionManager de mentira, com a resposta ditada pelo teste."""

    def __init__(self, negar=(), confirmar=()):
        self.negar = set(negar)
        self.confirmar = set(confirmar)
        self.consultadas = []

    def check(self, action):
        self.consultadas.append(action)
        if action in self.negar:
            return {"allowed": False, "confirm": False, "reason": "Bloqueado pelo perfil."}
        if action in self.confirmar:
            return {"allowed": True, "confirm": True, "reason": "Confirmação obrigatória."}
        return {"allowed": True, "confirm": False, "reason": "Permitido."}


@pytest.fixture
def router():
    return AdvancedSkillRouter(permissions=PermissoesFalsas())


# ------------------------------------------------------ route_local

def test_reconhece_status_do_git(router):
    plano = router.route_local("milk, qual o status do git")

    assert plano == {"type": "builtin", "skill": "git_status", "args": {}}


def test_reconhece_abrir_projetos(router):
    plano = router.route_local("abrir projetos")

    assert plano["skill"] == "open_projects"


def test_frase_qualquer_nao_casa(router):
    """Sem plano, o handle segue para o NLU como sempre fez."""
    assert router.route_local("que horas são") is None


def test_texto_vazio_nao_casa(router):
    assert router.route_local("") is None
    assert router.route_local(None) is None


def test_status_do_sistema_nao_e_mais_skill(router):
    """
    WindowsAgent.system_status já responde isso, com frase falável, e está
    ligado ao intent. Se o router capturasse, a resposta pioraria.
    """
    assert router.route_local("status do sistema") is None


def test_pesquisa_no_google_nao_e_mais_skill(router):
    """
    BrowserAgent.search dirige a página e sustenta os browser_click_text e
    browser_fill que vêm depois; o webbrowser do sistema não.
    """
    assert router.route_local("pesquisa no google gatos") is None


# ---------------------------------------------------------- execute

def test_executa_e_devolve_frase(router, monkeypatch):
    monkeypatch.setattr(
        "skills.advanced_router.BuiltinSkills.git_status",
        staticmethod(lambda args=None: {"ok": True, "fala": "Estou na branch master.", "dados": {"branch": "master"}}),
    )

    saida = router.execute({"type": "builtin", "skill": "git_status", "args": {}})

    assert saida["ok"] is True
    assert saida["fala"] == "Estou na branch master."
    assert saida["dados"] == {"branch": "master"}


def test_o_gate_e_consultado_com_o_nome_da_skill():
    permissoes = PermissoesFalsas()
    router = AdvancedSkillRouter(permissions=permissoes)

    router.execute({"type": "builtin", "skill": "open_projects", "args": {}}, confirmed=True)

    assert "open_projects" in permissoes.consultadas


def test_skill_negada_nao_executa():
    permissoes = PermissoesFalsas(negar=["git_status"])
    router = AdvancedSkillRouter(permissions=permissoes)

    saida = router.execute({"type": "builtin", "skill": "git_status", "args": {}})

    assert saida["ok"] is False
    assert "perfil" in saida["fala"].lower()


def test_skill_que_pede_confirmacao_nao_executa_ainda():
    permissoes = PermissoesFalsas(confirmar=["open_projects"])
    router = AdvancedSkillRouter(permissions=permissoes)

    saida = router.execute({"type": "builtin", "skill": "open_projects", "args": {}})

    assert saida.get("requires_confirmation") is True
    assert saida["skill"] == "open_projects"


def test_confirmada_a_skill_executa(monkeypatch):
    permissoes = PermissoesFalsas(confirmar=["open_projects"])
    router = AdvancedSkillRouter(permissions=permissoes)
    monkeypatch.setattr(
        "skills.advanced_router.BuiltinSkills.open_projects",
        staticmethod(lambda args=None: {"ok": True, "fala": "Abri a pasta.", "dados": {}}),
    )

    saida = router.execute(
        {"type": "builtin", "skill": "open_projects", "args": {}}, confirmed=True
    )

    assert saida["ok"] is True
    assert saida["fala"] == "Abri a pasta."


def test_sem_gate_configurado_a_skill_nao_roda():
    """
    Router sem PermissionManager é erro de montagem, não permissão livre.
    Deixar passar seria abrir um caminho sem gate nenhum.
    """
    router = AdvancedSkillRouter()

    saida = router.execute({"type": "builtin", "skill": "git_status", "args": {}})

    assert saida["ok"] is False


def test_skill_que_levanta_excecao_vira_frase(router, monkeypatch):
    def explode(args=None):
        raise RuntimeError("git não está no PATH")

    monkeypatch.setattr(
        "skills.advanced_router.BuiltinSkills.git_status", staticmethod(explode)
    )

    saida = router.execute({"type": "builtin", "skill": "git_status", "args": {}})

    assert saida["ok"] is False
    assert "git_status" in saida["dados"].get("erro", "") or saida["fala"]


def test_plano_vazio(router):
    saida = router.execute(None)

    assert saida["ok"] is False


def test_skill_inexistente(router):
    saida = router.execute({"type": "builtin", "skill": "voar", "args": {}})

    assert saida["ok"] is False


# ------------------------------------------------------- o registro

def test_o_registro_so_lista_o_que_existe():
    """
    config/skills.json declarava git_push, deploy, send_email e
    system_change sem nenhuma implementação: nomes sem nada atrás.
    """
    from skills.skill_registry import BuiltinSkills, SkillRegistry

    for skill in SkillRegistry().list_skills():
        assert hasattr(BuiltinSkills, skill["name"]), skill["name"]
```

- [ ] **Passo 2: Rodar o teste e confirmar que falha**

Rodar: `python -m pytest tests/test_skill_router.py -v`
Esperado: FAIL — `AdvancedSkillRouter.__init__` ainda não aceita
`permissions`.

- [ ] **Passo 3: Reescrever o registro de skills**

Substituir `src/skills/skill_registry.py` inteiro por:

```python
"""
As skills embutidas da MILK.

Cada skill devolve {"ok", "fala", "dados"}: a MILK fala o campo "fala", e
"dados" fica para log, teste e para o Command Center mostrar o número
exato sem re-executar a skill.

Duas skills sairam na fase 33 por duplicarem, pior, o que ja existia:
system_status (WindowsAgent.system_status ja devolve frase falavel e esta
ligado ao intent) e web_search (BrowserAgent.search dirige a pagina e
sustenta os browser_click_text e browser_fill que vem depois).
"""
import json
import os
from pathlib import Path

from core.proc import run_hidden

RAIZ = Path(__file__).resolve().parents[2]
REGISTRY = RAIZ / "config" / "skills.json"


class SkillRegistry:
    def __init__(self):
        self.data = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))

    def list_skills(self):
        return self.data.get("skills", [])

    def get(self, name):
        return next((s for s in self.list_skills() if s.get("name") == name), None)


class BuiltinSkills:
    @staticmethod
    def git_status(args=None):
        p = run_hidden(["git", "status", "--short", "--branch"], cwd=str(RAIZ))
        if p.returncode != 0:
            return {
                "ok": False,
                "fala": "Não consegui ler o status do git.",
                "dados": {"stderr": (p.stderr or "").strip()},
            }

        linhas = [l for l in (p.stdout or "").splitlines() if l.strip()]
        cabecalho = linhas[0] if linhas else ""
        # "## fase-33...origem/fase-33" -> "fase-33"
        branch = cabecalho.lstrip("#").strip().split("...")[0].strip() or "desconhecida"
        pendentes = max(0, len(linhas) - 1)

        if pendentes == 0:
            fala = f"Estou na branch {branch}, sem alterações pendentes."
        elif pendentes == 1:
            fala = f"Estou na branch {branch}, com um arquivo pendente."
        else:
            fala = f"Estou na branch {branch}, com {pendentes} arquivos pendentes."

        return {"ok": True, "fala": fala, "dados": {"branch": branch, "pendentes": pendentes}}

    @staticmethod
    def open_projects(args=None):
        caminho = RAIZ / "projects"
        caminho.mkdir(parents=True, exist_ok=True)
        os.startfile(caminho)
        return {
            "ok": True,
            "fala": "Abri a pasta de projetos.",
            "dados": {"path": str(caminho)},
        }
```

- [ ] **Passo 4: Reescrever o router**

Substituir `src/skills/advanced_router.py` inteiro por:

```python
"""
Roteia fala para skill embutida, por palavra-chave local.

Sem IA de proposito: e rapido, nao gasta token e continua funcionando com
o provedor fora do ar. O custo aceito e casar so as frases previstas.

O gate e o PermissionManager da fase 2. Ate a fase 33 este modulo tinha um
conjunto RISKY proprio -- as mesmas acoes de config/permission_profiles.json,
so que sem distinguir negar de confirmar, e com "admin_shell" onde o perfil
diz "open_admin". Dois gates, um pior. Sobrou o do perfil.
"""
from skills.skill_registry import BuiltinSkills, SkillRegistry


class AdvancedSkillRouter:
    def __init__(self, ai=None, mcp_manager=None, permissions=None):
        self.ai = ai
        self.mcp = mcp_manager
        self.registry = SkillRegistry()
        self.permissions = permissions

    def route_local(self, text):
        """Devolve um plano, ou None para o fluxo seguir para o NLU."""
        t = (text or "").lower()

        if "status do git" in t or "status do repositorio" in t or "status do repositório" in t:
            return {"type": "builtin", "skill": "git_status", "args": {}}

        if "abrir projetos" in t or "abre meus projetos" in t or "abrir meus projetos" in t:
            return {"type": "builtin", "skill": "open_projects", "args": {}}

        return None

    def execute(self, plan, confirmed=False):
        if not plan:
            return {"ok": False, "fala": "Não entendi qual ação executar.", "dados": {}}

        skill = plan.get("skill")

        if not self.permissions:
            # Router montado sem gate é erro de montagem, não permissão
            # livre: deixar passar abriria um caminho sem gate nenhum.
            return {
                "ok": False,
                "fala": "Não posso executar isso: o controle de permissões não está configurado.",
                "dados": {"skill": skill},
            }

        veredito = self.permissions.check(skill)
        if not veredito["allowed"]:
            return {
                "ok": False,
                "fala": f"Não posso fazer isso. {veredito['reason']}",
                "dados": {"skill": skill},
            }
        if veredito["confirm"] and not confirmed:
            return {
                "requires_confirmation": True,
                "skill": skill,
                "fala": "Isso requer confirmação. Diga confirmar para continuar.",
            }

        if plan.get("type") == "builtin":
            fn = getattr(BuiltinSkills, skill, None)
            if not fn:
                return {"ok": False, "fala": "Não conheço essa habilidade.", "dados": {"skill": skill}}
            try:
                return fn(plan.get("args") or {})
            except Exception as e:
                return {
                    "ok": False,
                    "fala": "Não consegui executar isso agora.",
                    "dados": {"skill": skill, "erro": f"{type(e).__name__}: {e}"},
                }

        if plan.get("type") == "mcp":
            if not self.mcp:
                return {"ok": False, "fala": "O MCP não está disponível.", "dados": {}}
            return self.mcp.call_tool(
                plan["server"], plan["tool"], plan.get("args") or {}, confirmed=confirmed
            )

        return {"ok": False, "fala": "Não conheço esse tipo de habilidade.", "dados": {"plano": plan}}
```

- [ ] **Passo 5: Limpar o config/skills.json**

Substituir `config/skills.json` inteiro por:

```json
{
  "skills": [
    {
      "name": "git_status",
      "type": "builtin",
      "safe": true
    },
    {
      "name": "open_projects",
      "type": "builtin",
      "safe": true
    }
  ]
}
```

- [ ] **Passo 6: Rodar os testes e confirmar que passam**

Rodar: `python -m pytest tests/test_skill_router.py -v`
Esperado: PASS nos 16 testes.

- [ ] **Passo 7: Conferir que o script antigo não quebrou o import**

Rodar: `python -c "import sys; sys.path.insert(0,'src'); from skills.advanced_router import AdvancedSkillRouter; print('importa')"`
Esperado: `importa`.

`Testar_Fase31.py` monta o router sem `permissions` e espera dicionários no
formato antigo. Não corrija o script: pôr no topo dele o mesmo cabeçalho
`SUBSTITUÍDO (Fase 33)` do passo 5 da Task 3, explicando que o formato de
retorno das skills mudou e que a cobertura real está em
`tests/test_skill_router.py`.

- [ ] **Passo 8: Commitar**

```bash
git add src/skills/ config/skills.json Testar_Fase31.py tests/test_skill_router.py
git commit -m "feat: skills devolvem frase e passam pelo gate de permissão do perfil"
```

---

### Task 5: Ligar o router ao cérebro

**Arquivos:**
- Modificar: `src/core/orchestrator.py` — o `__init__` e o `handle`
- Criar: `tests/test_orchestrator_skills.py`

**Interfaces:**
- Consome da Task 4: `AdvancedSkillRouter(permissions=...)`,
  `route_local`, `execute`.
- Produz: `MilkCore.skills` — a instância do router.

- [ ] **Passo 1: Escrever o teste que falha**

Criar `tests/test_orchestrator_skills.py`:

```python
"""
Testes da ligacao entre MilkCore.handle e o roteador de skills.

O router e consultado antes do NLU: quando casa, executa e fala; quando
nao casa, o fluxo segue exatamente como sempre foi.

MilkCore e montado por __new__ -- instanciar de verdade exigiria
microfone, Whisper e provedor de IA no ar.
"""
import pytest

import core.activity_state as estado_mod
from core.orchestrator import MilkCore


class RouterFalso:
    def __init__(self, plano=None, saida=None):
        self.plano = plano
        self.saida = saida or {"ok": True, "fala": "feito", "dados": {}}
        self.executados = []

    def route_local(self, texto):
        return self.plano

    def execute(self, plano, confirmed=False):
        self.executados.append((plano, confirmed))
        return self.saida


class NluFalso:
    def __init__(self):
        self.chamado = False

    def interpret(self, texto):
        self.chamado = True
        return {"intent": "chat", "reply": "oi"}


class MemoriaFalsa:
    def user_message(self, texto):
        pass

    def assistant_message(self, texto):
        pass


@pytest.fixture(autouse=True)
def estado_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    monkeypatch.setattr(estado_mod, "_atividade", "idle")


@pytest.fixture
def core():
    c = MilkCore.__new__(MilkCore)
    c.state = "ready"
    c.running = True
    c.memory = MemoriaFalsa()
    c.nlu = NluFalso()
    c._pending_confirmation = None
    c.ditos = []
    c.say = c.ditos.append
    return c


def test_skill_que_casa_e_falada(core):
    core.skills = RouterFalso(
        plano={"type": "builtin", "skill": "git_status", "args": {}},
        saida={"ok": True, "fala": "Estou na branch master.", "dados": {}},
    )

    core.handle("qual o status do git")

    assert core.ditos == ["Estou na branch master."]


def test_skill_que_casa_nao_gasta_o_nlu(core):
    """O ponto de rotear local: não pagar token no que já foi resolvido."""
    core.skills = RouterFalso(plano={"type": "builtin", "skill": "git_status", "args": {}})

    core.handle("qual o status do git")

    assert core.nlu.chamado is False


def test_frase_que_nao_casa_segue_para_o_nlu(core):
    core.skills = RouterFalso(plano=None)

    core.handle("me conte uma piada")

    assert core.nlu.chamado is True


def test_skill_que_falha_fala_o_motivo(core):
    core.skills = RouterFalso(
        plano={"type": "builtin", "skill": "git_status", "args": {}},
        saida={"ok": False, "fala": "Não consegui ler o status do git.", "dados": {}},
    )

    core.handle("qual o status do git")

    assert core.ditos == ["Não consegui ler o status do git."]


def test_skill_que_pede_confirmacao_adia(core):
    core.skills = RouterFalso(
        plano={"type": "builtin", "skill": "open_projects", "args": {}},
        saida={"requires_confirmation": True, "skill": "open_projects",
               "fala": "Isso requer confirmação. Diga confirmar para continuar."},
    )

    core.handle("abrir projetos")

    assert core._pending_confirmation is not None
    assert "confirmar" in core.ditos[0].lower()


def test_confirmar_executa_a_skill_adiada(core):
    router = RouterFalso(
        plano={"type": "builtin", "skill": "open_projects", "args": {}},
        saida={"requires_confirmation": True, "skill": "open_projects",
               "fala": "Isso requer confirmação. Diga confirmar para continuar."},
    )
    core.skills = router
    core.handle("abrir projetos")

    router.saida = {"ok": True, "fala": "Abri a pasta de projetos.", "dados": {}}
    core.handle("confirmar")

    assert router.executados[-1][1] is True
    assert core.ditos[-1] == "Abri a pasta de projetos."


def test_dormindo_a_skill_nao_dispara_sem_a_wake_word(core):
    """A palavra 'milk' continua sendo o portão; a skill não fura isso."""
    core.state = "sleep"
    core.skills = RouterFalso(plano={"type": "builtin", "skill": "git_status", "args": {}})

    core.handle("qual o status do git")

    assert core.ditos == []
```

- [ ] **Passo 2: Rodar o teste e confirmar que falha**

Rodar: `python -m pytest tests/test_orchestrator_skills.py -v`
Esperado: FAIL — `handle` ainda não consulta `self.skills`.

- [ ] **Passo 3: Montar o router no `__init__`**

Em `src/core/orchestrator.py`, acrescentar ao bloco de imports:

```python
from skills.advanced_router import AdvancedSkillRouter
```

Logo depois da linha que cria `self.permissions`, acrescentar:

```python
        # Roteador de skills por palavra-chave local (fase 33). Antes disso
        # ele existia e não era importado por ninguém: as skills eram
        # inalcançáveis por voz. Recebe o mesmo PermissionManager do resto
        # do MilkCore -- não existe um segundo gate.
        self.skills=AdvancedSkillRouter(ai=self.ai,permissions=self.permissions)
```

- [ ] **Passo 4: Consultar o router no `handle`**

Em `src/core/orchestrator.py`, inserir o bloco abaixo imediatamente **antes**
da linha `result=self.nlu.interpret(text)`:

```python
        # Skills por palavra-chave, antes do NLU: o que casa aqui não gasta
        # token nem depende do provedor de IA estar no ar.
        plano=self.skills.route_local(text)
        if plano:
            resultado=self.skills.execute(plano)
            if resultado.get("requires_confirmation"):
                def _executar_skill(p=plano):
                    confirmado=self.skills.execute(p,confirmed=True)
                    self.say(confirmado.get("fala") or "Feito.")
                self._pending_confirmation={"run":_executar_skill}
                self.say(resultado.get("fala") or "Isso requer confirmação. Diga confirmar para continuar.")
                return
            self.say(resultado.get("fala") or "Não consegui executar isso.")
            return
```

- [ ] **Passo 5: Rodar os testes e confirmar que passam**

Rodar: `python -m pytest tests/test_orchestrator_skills.py -v`
Esperado: PASS nos 7 testes.

- [ ] **Passo 6: Rodar a suíte inteira**

Rodar: `python -m pytest -q`
Esperado: PASS em tudo.

- [ ] **Passo 7: Verificar com o cérebro no ar**

Confirmar que o 9Router está de pé (`9router -t -n` se não estiver) e rodar:

```bash
python -c "import sys; sys.path.insert(0,'src'); from core.orchestrator import MilkCore; MilkCore().handle('milk, qual o status do git')"
```

Esperado: a MILK diz a branch atual e o número de arquivos pendentes — não
"Não consegui responder agora", que seria o NLU tendo capturado a frase.

- [ ] **Passo 8: Commitar**

```bash
git add src/core/orchestrator.py tests/test_orchestrator_skills.py
git commit -m "feat: as skills passam a ser alcançáveis por voz"
```

---

### Task 6: handle() sai da thread do Tk

**Arquivos:**
- Modificar: `src/presence/unified_app.py` — `__init__`, `_poll_events`,
  `_on_heard`, `_idle_watch`
- Modificar: `tests/test_unified_app_loops.py`

**Interfaces:**
- Consome da Task 2: `atividade`, `definir_atividade`, `pulsar`.
- Produz: `UnifiedApp._trabalho_loop` — a thread que consome a fila e chama
  `core.handle`. `_poll_events` deixa de chamar `_on_heard`.

**Antes de escrever código, faça a varredura que a spec exige:** `handle()`
nunca rodou fora da thread principal. Rodar:

```bash
grep -rn "tkinter\|Tk()\|messagebox\|Toplevel" --include=*.py src/agents src/browser src/coding src/vision src/devops src/documents | grep -v __pycache__
```

Se algum agente alcançado por `handle` abrir janela Tk, **pare e relate** —
vira tarefa própria, não conserto improvisado dentro desta.

- [ ] **Passo 1: Escrever o teste que falha**

Acrescentar ao fim de `tests/test_unified_app_loops.py`:

Acrescentar também, ao topo do arquivo, o isolamento do estado — sem ele o
novo `_idle_watch` chama `pulsar()` e escreve no
`data/milk_runtime_state.json` de verdade durante os testes:

```python
import core.activity_state as estado_mod


@pytest.fixture(autouse=True)
def estado_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    monkeypatch.setattr(estado_mod, "_atividade", "idle")
```

E os casos novos:

```python
# ------------------------------------------------- fila fora do Tk

def test_nao_existe_mais_poll_events(app):
    """
    A fila passou a ser consumida pela thread de trabalho. Um _poll_events
    sobrevivente voltaria a chamar handle() na thread do Tk, e o avatar
    voltaria a congelar -- o defeito que esta fase existe para tirar.
    """
    assert not hasattr(app, "_poll_events")
    assert not hasattr(app, "_on_heard")


def test_trabalho_loop_entrega_a_fala_ao_cerebro(app):
    tratados = []
    app.core = type("CoreFalso", (), {"handle": lambda self, t: tratados.append(t)})()
    app.running = True

    app.events.put("milk que horas são")
    app._trabalho_passo(timeout=0.01)

    assert tratados == ["milk que horas são"]


def test_fila_vazia_no_trabalho_loop_nao_e_erro(app):
    app.core = type("CoreFalso", (), {"handle": lambda self, t: None})()
    app.running = True

    app._trabalho_passo(timeout=0.01)  # não levanta


def test_falha_do_cerebro_nao_mata_a_thread_de_trabalho(app, registros):
    def explode(self, texto):
        raise RuntimeError("provedor de IA fora do ar")

    app.core = type("CoreFalso", (), {"handle": explode})()
    app.running = True
    app.events.put("milk")

    app._trabalho_passo(timeout=0.01)  # não levanta

    registro = "\n".join(registros)
    assert "provedor de IA fora do ar" in registro


def test_o_fade_segue_o_estado_e_nao_o_comando(app, monkeypatch):
    """
    A thread de trabalho não pode tocar em Tk. Quem faz o fade é o
    _idle_watch, olhando core.state.
    """
    escondeu = []
    monkeypatch.setattr(app, "_fade_out", lambda: escondeu.append(True))
    app.visible = True
    app.core = type("CoreFalso", (), {"state": "sleep"})()

    app._idle_watch()

    assert escondeu == [True]
```

- [ ] **Passo 2: Rodar o teste e confirmar que falha**

Rodar: `python -m pytest tests/test_unified_app_loops.py -v`
Esperado: FAIL — `_trabalho_passo` não existe, e `_poll_events` ainda chama
`_on_heard`.

- [ ] **Passo 3: Criar a thread de trabalho**

Em `src/presence/unified_app.py`, no `__init__`, acrescentar a thread junto
das outras duas:

```python
        threading.Thread(target=self._trabalho_loop, daemon=True).start()
```

Acrescentar os dois métodos, logo depois de `_scheduler_loop`:

```python
    def _trabalho_loop(self):
        """
        Consome a fila e chama o cérebro, FORA da thread do Tk.

        Antes, handle() rodava na thread do Tk: a chamada de IA inteira, a
        memória e o TTS aconteciam dentro da thread que deveria estar
        animando. O after() ficava parado e o avatar congelava em
        "pensando" -- exatamente quando devia se mexer.

        Esta thread nunca toca em Tkinter, que não aceita chamada de outra
        thread. Ela só muda estado; quem aparece e some é o _idle_watch, na
        thread do Tk, olhando core.state.
        """
        while self.running:
            self._trabalho_passo()

    def _trabalho_passo(self, timeout=0.2):
        """Um giro do laço. Separado para poder ser testado sem thread."""
        try:
            text = self.events.get(timeout=timeout)
        except queue.Empty:
            return

        self.last_activity = time.time()
        try:
            self.core.handle(text)
        except Exception:
            _log(f"Erro ao tratar {text!r}:\n{traceback.format_exc()}")
```

- [ ] **Passo 4: Tirar o cérebro do `_poll_events`**

`_poll_events` não tem mais o que fazer: a fila passou a ser consumida pela
thread de trabalho.

Apagar de `src/presence/unified_app.py`:

- o método `_poll_events` inteiro;
- a linha `self.root.after(100, self._poll_events)` do `__init__`;
- o método `_on_heard` inteiro — `last_activity` foi para `_trabalho_passo`,
  e o fade vai para o `_idle_watch` no passo 5.

Apagar de `tests/test_unified_app_loops.py` os cinco testes que ficaram sem
objeto, todos da seção `_poll_events`:

- `test_fila_vazia_reagenda`
- `test_consome_tudo_que_esta_na_fila`
- `test_excecao_ao_tratar_nao_mata_o_laco`
- `test_a_falha_vai_para_o_log`
- `test_uma_frase_ruim_nao_impede_a_proxima`

Os três primeiros protegiam a fila; quem protege isso agora é
`test_falha_do_cerebro_nao_mata_a_thread_de_trabalho`, do passo 1. Os testes
de `_animate` e `_idle_watch` ficam onde estão.

- [ ] **Passo 5: O fade passa a seguir o estado**

Trocar o `_idle_watch` inteiro por:

```python
    def _idle_watch(self):
        # Aparecer e sumir virou consequência do estado, não do comando: a
        # thread de trabalho não pode tocar em Tkinter, então quem decide
        # é este laço, que já roda na thread do Tk de segundo em segundo.
        try:
            if self.core.state == "sleep" and self.visible:
                self._fade_out()
            elif self.core.state != "sleep" and not self.visible:
                self._fade_in()

            if self.visible and self.core.state != "sleep" and self.last_activity:
                if time.time() - self.last_activity > self.idle_timeout:
                    self.core.state = "sleep"
                    definir_atividade("idle")
                    self._fade_out()

            pulsar()
        except Exception:
            _log(f"Erro no controle de ociosidade:\n{traceback.format_exc()}")
        finally:
            self.root.after(1000, self._idle_watch)
```

- [ ] **Passo 6: Rodar os testes e confirmar que passam**

Rodar: `python -m pytest tests/test_unified_app_loops.py -v`
Esperado: PASS.

- [ ] **Passo 7: Rodar a suíte inteira**

Rodar: `python -m pytest -q`
Esperado: PASS em tudo.

- [ ] **Passo 8: Verificação manual — a que nenhum teste cobre**

Com o 9Router no ar, rodar `python src/main.py`, dizer "milk" para o avatar
aparecer e fazer uma pergunta que puxe a IA (não uma skill nem um comando
local). Conferir, olhando a tela: **o pulso do avatar continua enquanto a
resposta não chega.** Antes ele parava.

Depois fechar a MILK, abrir o mini overlay com
`INICIAR_MILK_MINI_OVERLAY.bat` e conferir que ele mostra `MILK · DESLIGADA`
em até cinco segundos.

Registrar as duas no relatório como **verificação manual**, com o que você
observou. Não conte nenhuma delas como aprovada por teste automático.

- [ ] **Passo 9: Commitar**

```bash
git add src/presence/unified_app.py tests/test_unified_app_loops.py
git commit -m "feat: o cérebro sai da thread do Tk e o avatar não congela mais"
```

---

## Verificação final da fase

- [ ] `python -m pytest -q` — todos passam
- [ ] `python Testar_Sistema.py` — `RESULTADO: tudo passou`
- [ ] `git status --porcelain` vazio
- [ ] `grep -rn "self.activity\|core.activity" --include=*.py src/ | grep -v __pycache__` não retorna nada — a segunda verdade sumiu
- [ ] `grep -rn "RISKY" --include=*.py src/ | grep -v __pycache__` não retorna nada — o gate duplicado sumiu
- [ ] `python -c "import sys; sys.path.insert(0,'src'); from core.orchestrator import MilkCore; MilkCore().handle('milk, qual o status do git')"` fala a branch
- [ ] As duas verificações manuais da Task 6, passo 8, registradas com o que
      foi observado
