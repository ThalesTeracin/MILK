# Fase 32 — Instalador e Atualização Segura — Plano de Implementação

> **Para executores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> superpowers:subagent-driven-development (recomendado) ou
> superpowers:executing-plans para implementar tarefa a tarefa. Os passos
> usam caixas (`- [ ]`) para acompanhamento.

**Objetivo:** Permitir instalar e atualizar o MILK sem perder configuração
de máquina e sem deixar uma atualização defeituosa ativa.

**Arquitetura:** Um resolvedor de config faz `config/local/` (fora do git)
sobrepor `config/`, tirando o dado de máquina do caminho da atualização. Um
script de atualização exige árvore limpa, para o processo, atualiza, migra,
roda os testes e reverte ao commit anterior se qualquer passo falhar. Um
arquivo `VERSION` somado ao commit identifica o que está rodando.

**Stack:** Python 3.14 (mínimo 3.12), pytest 8, PowerShell 5.1+ (cmdlets de
Tarefa Agendada), git.

**Spec:** `docs/superpowers/specs/2026-08-28-fase-32-instalador-atualizacao-design.md`

## Restrições globais

- Python mínimo: **3.12**. Máquina de referência: 3.14.7.
- Migrações de schema são **somente aditivas** (`ADD COLUMN`). É o que torna
  a reversão do updater segura: se a migração rodou e os testes falharam, o
  código volta e o banco fica adiante sem quebrar.
- Tudo que é escrito para humanos — comentários, docstrings, mensagens de
  script, commits — em português.
- Imports são absolutos com `src/` no `sys.path` (`from core.proc import
  ...`), nunca relativos (`from ..core import`). Import relativo quebra
  neste projeto.
- Testes ficam em `tests/`, rodados de `C:\JARVIS` com `python -m pytest`.
  `tests/conftest.py` já põe `src/` no path.
- Nome da tarefa agendada: `MILK_Assistant`. Ponto de entrada:
  `src/main.py`.
- **Sobre PowerShell e TDD:** os `.ps1` não são testáveis por pytest. Toda
  lógica pura (resolução de caminho, formatação de linha de log, leitura de
  versão) vive em Python e recebe TDD de verdade. Os `.ps1` ficam como
  orquestração fina e seus passos de verificação são manuais e explícitos.
  Não invente testes de PowerShell.

---

### Task 1: Resolvedor de config

**Arquivos:**
- Criar: `src/core/config.py`
- Criar: `tests/test_config_path.py`

**Interfaces:**
- Consome: nada.
- Produz: `config_path(nome: str) -> Path` — devolve
  `config/local/<nome>` se existir, senão `config/<nome>`. Também expõe
  `CONFIG_DIR: Path` e `LOCAL_DIR: Path`, ambos absolutos, derivados da
  raiz do repositório.

- [ ] **Passo 1: Escrever o teste que falha**

```python
"""
Testes de src/core/config.py -- o resolvedor que faz config/local/
sobrepor config/, para que a atualização não sobrescreva configuração
específica desta máquina.
"""
import core.config as config_mod
from core.config import config_path


def test_devolve_o_versionado_quando_nao_ha_local(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    versionado = tmp_path / "config" / "x.json"
    versionado.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config_mod, "LOCAL_DIR", tmp_path / "config" / "local")

    assert config_path("x.json") == versionado


def test_local_tem_precedencia(tmp_path, monkeypatch):
    (tmp_path / "config" / "local").mkdir(parents=True)
    (tmp_path / "config" / "x.json").write_text("{}", encoding="utf-8")
    local = tmp_path / "config" / "local" / "x.json"
    local.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config_mod, "LOCAL_DIR", tmp_path / "config" / "local")

    assert config_path("x.json") == local


def test_devolve_o_versionado_quando_nenhum_existe(tmp_path, monkeypatch):
    """Quem chama decide o que fazer com caminho inexistente."""
    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config_mod, "LOCAL_DIR", tmp_path / "config" / "local")

    assert config_path("nao_existe.json") == tmp_path / "config" / "nao_existe.json"


def test_diretorios_padrao_apontam_para_a_raiz_do_repositorio():
    assert config_mod.CONFIG_DIR.name == "config"
    assert config_mod.LOCAL_DIR.parent == config_mod.CONFIG_DIR
    assert (config_mod.CONFIG_DIR / "persona.txt").exists()
```

- [ ] **Passo 2: Rodar o teste e confirmar que falha**

Rodar: `python -m pytest tests/test_config_path.py -v`
Esperado: FAIL com `ModuleNotFoundError: No module named 'core.config'`

- [ ] **Passo 3: Implementar o mínimo**

```python
"""
Resolve qual arquivo de configuração usar.

config/ é versionado e vem com a atualização. config/local/ é ignorado
pelo git e guarda o que pertence a ESTA máquina: índice do microfone,
caminhos absolutos do whisper. Sem essa separação, um git pull
sobrescreve a escolha de dispositivo do usuário.

Quem escreve configuração de máquina deve escrever sempre em
config/local/, nunca em config/.
"""

from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
LOCAL_DIR = CONFIG_DIR / "local"


def config_path(nome):
    """
    Devolve config/local/<nome> se existir, senão config/<nome>.

    O caminho devolvido pode não existir; cabe a quem chama tratar isso.
    """
    local = LOCAL_DIR / nome
    if local.exists():
        return local
    return CONFIG_DIR / nome
```

- [ ] **Passo 4: Rodar o teste e confirmar que passa**

Rodar: `python -m pytest tests/test_config_path.py -v`
Esperado: 4 passed

- [ ] **Passo 5: Rodar a suíte inteira**

Rodar: `python -m pytest -q`
Esperado: todos passam (35 antes desta tarefa, 39 depois)

- [ ] **Passo 6: Commitar**

```bash
git add src/core/config.py tests/test_config_path.py
git commit -m "feat: resolve config de máquina em config/local/"
```

---

### Task 2: Migrar os leitores e tirar config de máquina do git

**Arquivos:**
- Modificar: `src/voice/listener.py:12`
- Modificar: `Selecionar_Microfone.py:5,24`
- Modificar: `MILK_Command_Center.py:370`
- Modificar: `.gitignore`
- Criar: `config/audio_device.example.json`
- Criar: `config/whisper_local.example.json`
- Criar: `tests/test_config_local_integracao.py`

**Interfaces:**
- Consome: `config_path(nome)` da Task 1.
- Produz: `config/local/` populado com os arquivos reais desta máquina.

- [ ] **Passo 1: Mover os arquivos reais para config/local/ ANTES de mexer no git**

Ordem importa: o conteúdo tem que estar salvo antes de sair do índice.

```bash
mkdir -p config/local
cp config/audio_device.json config/local/audio_device.json
cp config/whisper_local.json config/local/whisper_local.json
```

Verificar: `ls config/local/` mostra os dois arquivos.

- [ ] **Passo 2: Escrever o teste que falha**

```python
"""
Verifica que a configuração de máquina foi separada da versionada.

O risco que estes testes cobrem: um git pull sobrescrever o índice do
microfone escolhido pelo usuário.
"""
import json
import subprocess

from core.config import CONFIG_DIR, LOCAL_DIR, config_path


def test_config_local_existe_com_os_arquivos_de_maquina():
    assert (LOCAL_DIR / "audio_device.json").exists()
    assert (LOCAL_DIR / "whisper_local.json").exists()


def test_arquivos_de_maquina_nao_estao_versionados():
    """git ls-files vazio == o arquivo não vem na atualização."""
    for nome in ["audio_device.json", "whisper_local.json"]:
        saida = subprocess.run(
            ["git", "ls-files", "config/%s" % nome],
            capture_output=True, text=True, cwd=CONFIG_DIR.parent,
        ).stdout.strip()
        assert saida == "", "config/%s ainda está no git" % nome


def test_os_exemplos_estao_versionados_e_sao_json_valido():
    for nome in ["audio_device.example.json", "whisper_local.example.json"]:
        caminho = CONFIG_DIR / nome
        assert caminho.exists()
        json.loads(caminho.read_text(encoding="utf-8-sig"))


def test_config_path_prefere_o_local_para_arquivos_de_maquina():
    assert config_path("whisper_local.json").parent == LOCAL_DIR
    assert config_path("audio_device.json").parent == LOCAL_DIR


def test_selecionar_microfone_grava_em_config_local():
    """
    O seletor é interativo e não dá para executar aqui, mas o destino da
    escrita é uma constante de módulo. Se ela apontar para config/, a
    escolha do usuário volta a ser sobrescrita pela atualização.
    """
    import ast

    fonte = (CONFIG_DIR.parent / "Selecionar_Microfone.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    destinos = [
        no for no in ast.walk(arvore)
        if isinstance(no, ast.Assign)
        and any(getattr(a, "id", None) == "CONFIG" for a in no.targets)
    ]
    assert len(destinos) == 1, "esperava uma única atribuição de CONFIG"
    assert "LOCAL_DIR" in ast.dump(destinos[0]), "CONFIG não aponta para LOCAL_DIR"
```

- [ ] **Passo 3: Rodar e confirmar que falha**

Rodar: `python -m pytest tests/test_config_local_integracao.py -v`
Esperado: FAIL em `test_arquivos_de_maquina_nao_estao_versionados` (ainda no git)

- [ ] **Passo 4: Criar os arquivos de exemplo**

`config/audio_device.example.json`:

```json
{
  "input_device": 0
}
```

`config/whisper_local.example.json`:

```json
{
  "language": "pt",
  "whisper_exe": "C:\\JARVIS\\third_party\\whisper-prebuilt\\Release\\whisper-cli.exe",
  "model": "C:\\JARVIS\\models\\ggml-base.bin",
  "seconds": 6
}
```

- [ ] **Passo 5: Tirar os reais do índice do git**

O conteúdo permanece em disco; sai apenas do controle de versão.

```bash
git rm --cached config/audio_device.json config/whisper_local.json
```

- [ ] **Passo 6: Acrescentar ao .gitignore**

Adicionar ao final de `.gitignore`:

```
# Configuração desta máquina (índice do microfone, caminhos do whisper).
# Fica fora do git para que a atualização não sobrescreva a escolha do
# usuário. Formato documentado em config/*.example.json.
config/local/
config/audio_device.json
config/whisper_local.json
```

- [ ] **Passo 7: Trocar os três pontos de leitura**

Em `src/voice/listener.py`, trocar a linha 12 e ajustar o import:

```python
from core.config import config_path
from core.proc import popen_hidden

CONFIG = config_path("whisper_local.json")
```

Em `MILK_Command_Center.py:370`, dentro de `refresh_whisper`:

```python
        cfg = config_path("whisper_local.json")
```

acrescentando no topo do arquivo `from core.config import config_path`.

Em `Selecionar_Microfone.py`, trocar a linha 5 e a escrita da linha 24.
O arquivo passa a escrever **sempre** em `config/local/`:

```python
import json
import sounddevice as sd

from core.config import LOCAL_DIR

# Escreve sempre em config/local/: é configuração desta máquina, e no
# diretório versionado seria sobrescrita na próxima atualização.
CONFIG = LOCAL_DIR / "audio_device.json"
CONFIG.parent.mkdir(parents=True, exist_ok=True)
```

`Selecionar_Microfone.py` roda da raiz e não tem `src/` no path. Acrescentar
no topo, antes dos imports do projeto:

```python
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

- [ ] **Passo 8: Rodar os testes e confirmar que passam**

Rodar: `python -m pytest tests/test_config_local_integracao.py -v`
Esperado: 5 passed

- [ ] **Passo 9: Verificar que o MILK ainda carrega**

Rodar:

```bash
python -c "import sys; sys.path.insert(0,'src'); import voice.listener; print('OK')"
python -m pytest -q
```

Esperado: `OK` e todos os testes passam (44 no total)

- [ ] **Passo 10: Commitar**

```bash
git add .gitignore config/audio_device.example.json config/whisper_local.example.json src/voice/listener.py MILK_Command_Center.py Selecionar_Microfone.py tests/test_config_local_integracao.py
git commit -m "feat: tira config de máquina do controle de versão"
```

---

### Task 3: Versionamento

**Arquivos:**
- Criar: `VERSION`
- Criar: `src/core/version.py`
- Criar: `tests/test_version.py`
- Modificar: `src/main.py`

**Interfaces:**
- Consome: nada.
- Produz: `version_info() -> tuple[str, str | None]` — devolve
  `(versao, commit)`. `versao` vem do arquivo `VERSION`; `commit` é o hash
  curto de `git rev-parse --short HEAD`, ou `None` fora de um repositório.
  Também `formatar_versao() -> str`, que devolve `"32.0 (c53d469)"` ou
  `"32.0"` quando não há commit.

- [ ] **Passo 1: Escrever o teste que falha**

```python
"""
Testes de src/core/version.py -- identificação do que está rodando.

A versão vem de um arquivo para funcionar em máquinas sem git; o commit
vem do git quando disponível e identifica o código exato.
"""
import core.version as version_mod
from core.version import formatar_versao, version_info


def test_le_a_versao_do_arquivo():
    versao, _ = version_info()
    assert versao
    assert versao[0].isdigit()


def test_devolve_o_commit_dentro_de_um_repositorio():
    _, commit = version_info()
    assert commit is not None
    assert 6 <= len(commit) <= 12


def test_versao_cai_no_padrao_quando_o_arquivo_some(tmp_path, monkeypatch):
    monkeypatch.setattr(version_mod, "VERSION_FILE", tmp_path / "nao_existe")
    versao, _ = version_info()
    assert versao == version_mod.VERSAO_DESCONHECIDA


def test_commit_e_none_fora_de_repositorio(tmp_path, monkeypatch):
    monkeypatch.setattr(version_mod, "ROOT", tmp_path)
    _, commit = version_info()
    assert commit is None


def test_formatar_inclui_o_commit_entre_parenteses():
    saida = formatar_versao()
    versao, commit = version_info()
    assert saida == "%s (%s)" % (versao, commit)


def test_formatar_omite_os_parenteses_sem_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(version_mod, "ROOT", tmp_path)
    versao, _ = version_info()
    assert formatar_versao() == versao
```

- [ ] **Passo 2: Rodar e confirmar que falha**

Rodar: `python -m pytest tests/test_version.py -v`
Esperado: FAIL com `ModuleNotFoundError: No module named 'core.version'`

- [ ] **Passo 3: Criar o arquivo VERSION**

Conteúdo de `VERSION`, uma linha:

```
32.0
```

- [ ] **Passo 4: Implementar src/core/version.py**

```python
"""
Identifica a versão do MILK em execução.

Duas fontes, de propósito: o arquivo VERSION acompanha instalações sem
git (o caso das outras máquinas), enquanto o commit identifica o código
exato e só existe onde há repositório.
"""

from pathlib import Path

from core.proc import run_hidden

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "VERSION"
VERSAO_DESCONHECIDA = "desconhecida"


def version_info():
    """Devolve (versao, commit). O commit é None fora de um repositório."""
    try:
        versao = VERSION_FILE.read_text(encoding="utf-8").strip() or VERSAO_DESCONHECIDA
    except Exception:
        versao = VERSAO_DESCONHECIDA

    commit = None
    try:
        resultado = run_hidden(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, timeout=10
        )
        if resultado.returncode == 0:
            commit = resultado.stdout.strip() or None
    except Exception:
        commit = None

    return versao, commit


def formatar_versao():
    """Devolve "32.0 (c53d469)", ou só "32.0" quando não há commit."""
    versao, commit = version_info()
    if commit:
        return "%s (%s)" % (versao, commit)
    return versao
```

- [ ] **Passo 5: Rodar e confirmar que passa**

Rodar: `python -m pytest tests/test_version.py -v`
Esperado: 6 passed

- [ ] **Passo 6: Acrescentar --version ao ponto de entrada**

Em `src/main.py`, dentro de `main()`, **antes** do trecho de `--headless`:

```python
    if "--version" in sys.argv:
        from core.version import formatar_versao
        print(formatar_versao())
        return
```

- [ ] **Passo 7: Verificar na mão**

Rodar: `python src/main.py --version`
Esperado: uma linha no formato `32.0 (<hash>)`

- [ ] **Passo 8: Rodar a suíte inteira**

Rodar: `python -m pytest -q`
Esperado: todos passam (50 no total)

- [ ] **Passo 9: Commitar**

```bash
git add VERSION src/core/version.py src/main.py tests/test_version.py
git commit -m "feat: identifica a versão em execução por arquivo e commit"
```

---

### Task 4: Linha do registro de atualização

**Arquivos:**
- Criar: `src/core/update_log.py`
- Criar: `tests/test_update_log.py`

Esta tarefa existe separada da Task 5 porque é a única parte do updater que
é lógica pura, e portanto a única testável de verdade.

**Interfaces:**
- Consome: nada.
- Produz: `linha_de_log(quando, antes, depois, resultado, detalhe=None) ->
  str` e `registrar(caminho, linha) -> None`, que acrescenta a linha ao
  arquivo criando o diretório se preciso.

- [ ] **Passo 1: Escrever o teste que falha**

```python
"""
Testes do registro de atualizações.

Quando o MILK começar a se comportar mal, a primeira pergunta é "o que
mudou e quando". Este log é a resposta.
"""
import datetime

from core.update_log import linha_de_log, registrar

QUANDO = datetime.datetime(2026, 8, 28, 14, 2)


def test_linha_de_sucesso():
    linha = linha_de_log(QUANDO, "32.0 (c53d469)", "32.1 (a1b2c3d)", "OK")
    assert linha == "2026-08-28 14:02  32.0 (c53d469) -> 32.1 (a1b2c3d)  OK"


def test_linha_de_falha_traz_o_detalhe():
    linha = linha_de_log(
        QUANDO, "32.1 (a1b2c3d)", "32.2 (e4f5g6h)", "FALHOU", "2 testes  revertido"
    )
    assert linha.endswith("FALHOU: 2 testes  revertido")


def test_linha_nunca_tem_quebra_interna():
    """Uma linha por atualização: o log é lido com grep e tail."""
    linha = linha_de_log(QUANDO, "32.0", "32.1", "FALHOU", "erro\ncom quebra")
    assert "\n" not in linha


def test_registrar_cria_o_diretorio_e_acrescenta(tmp_path):
    destino = tmp_path / "logs" / "update.log"
    registrar(destino, "primeira")
    registrar(destino, "segunda")
    assert destino.read_text(encoding="utf-8").splitlines() == ["primeira", "segunda"]
```

- [ ] **Passo 2: Rodar e confirmar que falha**

Rodar: `python -m pytest tests/test_update_log.py -v`
Esperado: FAIL com `ModuleNotFoundError: No module named 'core.update_log'`

- [ ] **Passo 3: Implementar**

```python
"""
Formata e grava o registro de atualizações do MILK.

Uma linha por atualização, para ser lida com tail e grep:

    2026-08-28 14:02  32.0 (c53d469) -> 32.1 (a1b2c3d)  OK
    2026-08-28 15:40  32.1 (a1b2c3d) -> 32.2 (e4f5g6h)  FALHOU: 2 testes  revertido
"""


def linha_de_log(quando, antes, depois, resultado, detalhe=None):
    """
    Monta a linha de uma atualização.

    quando: datetime. antes/depois: texto de versão já formatado.
    resultado: "OK" ou "FALHOU". detalhe: motivo, só quando falhou.
    """
    linha = "%s  %s -> %s  %s" % (
        quando.strftime("%Y-%m-%d %H:%M"),
        antes,
        depois,
        resultado,
    )
    if detalhe:
        # Quebras de linha destruiriam o formato de uma linha por registro.
        linha += ": " + " ".join(str(detalhe).split("\n"))
    return linha


def registrar(caminho, linha):
    """Acrescenta a linha ao arquivo, criando o diretório se preciso."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(linha + "\n")
```

- [ ] **Passo 4: Rodar e confirmar que passa**

Rodar: `python -m pytest tests/test_update_log.py -v`
Esperado: 4 passed

- [ ] **Passo 5: Commitar**

```bash
git add src/core/update_log.py tests/test_update_log.py
git commit -m "feat: formata o registro de atualizações"
```

---

### Task 5: Script de atualização segura

**Arquivos:**
- Criar: `installer/Atualizar_MILK.ps1`

**Interfaces:**
- Consome: `formatar_versao()` da Task 3, `linha_de_log()` e `registrar()`
  da Task 4, `LongMemory` de `src/memory/long_memory.py`.
- Produz: nada consumido por tarefas posteriores.

Não há teste unitário aqui — é orquestração de git, tarefa agendada e
processo. A verificação é manual, no Passo 3, e cobre os dois caminhos.

- [ ] **Passo 1: Escrever o script**

```powershell
<#
    Atualiza o MILK com reversão automática.

    A ordem dos passos não é arbitrária:

    - Exigir árvore limpa é o que torna a reversão segura. git reset
      --hard descarta alterações não commitadas; recusar entrar com a
      árvore suja garante que não há trabalho a destruir na saída.

    - Parar a tarefa antes de migrar, porque o processo mantém o SQLite
      aberto em modo WAL. Stop-ScheduledTask retorna antes do processo
      morrer, então esperamos o pythonw sumir.

    - A reversão só é segura porque as migrações são somente aditivas
      (ADD COLUMN). Se a migração rodou e os testes falharam, o código
      volta e o banco fica adiante sem quebrar.

    Uso:
        powershell -ExecutionPolicy Bypass -File installer\Atualizar_MILK.ps1
#>

$ErrorActionPreference = "Stop"

$Raiz     = "C:\JARVIS"
$Tarefa   = "MILK_Assistant"
$LogFile  = Join-Path $Raiz "logs\update.log"

Set-Location $Raiz

function Versao {
    (& python "src\main.py" "--version" 2>$null | Select-Object -First 1)
}

function Registrar($antes, $depois, $resultado, $detalhe) {
    $py = @"
import sys, datetime
sys.path.insert(0, 'src')
from core.update_log import linha_de_log, registrar
from pathlib import Path
registrar(Path(r'$LogFile'), linha_de_log(
    datetime.datetime.now(), r'''$antes''', r'''$depois''',
    r'''$resultado''', r'''$detalhe''' or None))
"@
    $py | & python -
}

# --- 1. Árvore limpa ---
$sujo = & git status --porcelain
if ($sujo) {
    Write-Host "Há alterações não commitadas. A atualização foi cancelada." -ForegroundColor Yellow
    Write-Host "Commite ou descarte antes de atualizar:" -ForegroundColor Yellow
    Write-Host $sujo
    exit 1
}

# --- 2. Guardar o ponto de retorno ---
$antesCommit = (& git rev-parse HEAD).Trim()
$antesVersao = Versao
Write-Host "Versão atual: $antesVersao"

# --- 3. Parar a tarefa e esperar o processo morrer ---
Write-Host "Parando $Tarefa..."
Stop-ScheduledTask -TaskName $Tarefa -ErrorAction SilentlyContinue

$limite = (Get-Date).AddSeconds(30)
while (Get-Process pythonw -ErrorAction SilentlyContinue) {
    if ((Get-Date) -gt $limite) {
        Write-Host "O processo do MILK não encerrou em 30s. Atualização cancelada." -ForegroundColor Red
        Start-ScheduledTask -TaskName $Tarefa -ErrorAction SilentlyContinue
        exit 1
    }
    Start-Sleep -Milliseconds 500
}

# --- 4 a 6. Atualizar, migrar, testar ---
$falha = $null

try {
    Write-Host "Atualizando..."
    & git pull
    if ($LASTEXITCODE -ne 0) { throw "git pull falhou" }

    Write-Host "Migrando o banco..."
    & python -c "import sys; sys.path.insert(0,'src'); from memory.long_memory import LongMemory; LongMemory().close()"
    if ($LASTEXITCODE -ne 0) { throw "migração falhou" }

    Write-Host "Rodando os testes..."
    & python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "testes falharam" }
}
catch {
    $falha = $_.Exception.Message
}

# --- 7. Concluir ou reverter ---
if ($falha) {
    Write-Host "Falhou: $falha. Revertendo para $antesCommit." -ForegroundColor Red
    & git reset --hard $antesCommit | Out-Null
    Start-ScheduledTask -TaskName $Tarefa
    Registrar $antesVersao (Versao) "FALHOU" "$falha  revertido"
    exit 1
}

$depoisVersao = Versao
Start-ScheduledTask -TaskName $Tarefa
Registrar $antesVersao $depoisVersao "OK" ""

Write-Host ""
Write-Host "Atualizado: $antesVersao -> $depoisVersao" -ForegroundColor Green
Write-Host "Registro em logs\update.log"
```

- [ ] **Passo 2: Verificar a recusa com árvore suja**

```bash
echo "sujeira" > sujeira_temporaria.txt
powershell -ExecutionPolicy Bypass -File installer\Atualizar_MILK.ps1
```

Esperado: sai com "Há alterações não commitadas", código 1, e **sem** ter
parado a tarefa. Depois: `rm sujeira_temporaria.txt`

- [ ] **Passo 3: Verificar o caminho de sucesso**

Com a árvore limpa, rodar:

```bash
powershell -ExecutionPolicy Bypass -File installer\Atualizar_MILK.ps1
```

Esperado: roda até o fim (o `git pull` não traz nada, o que é sucesso),
reinicia a tarefa, e acrescenta uma linha `OK` a `logs\update.log`.
Conferir com `cat logs/update.log`.

- [ ] **Passo 4: Verificar o caminho de reversão**

O caminho de falha é a razão de o script existir; não pode ficar sem
prova. Forçar a falha do passo de testes, temporariamente:

Em `installer/Atualizar_MILK.ps1`, trocar por um instante a linha

```powershell
    & python -m pytest -q
```

por

```powershell
    & python -m pytest -q --flag-inexistente-para-forcar-falha
```

Commitar essa alteração (a árvore precisa estar limpa), anotar o commit
com `git rev-parse HEAD`, e rodar o script.

Esperado: o script relata "Falhou: testes falharam. Revertendo para
&lt;commit&gt;", reinicia a tarefa, e acrescenta a `logs\update.log` uma linha
terminada em `FALHOU: testes falharam  revertido`.

Conferir: `git rev-parse HEAD` devolve o mesmo commit anotado (o
`git reset --hard` voltou ao ponto de partida) e
`Get-ScheduledTask MILK_Assistant` mostra a tarefa em execução.

Depois, desfazer a alteração no script e commitar a versão correta.

- [ ] **Passo 5: Commitar**

```bash
git add installer/Atualizar_MILK.ps1
git commit -m "feat: atualiza o MILK com reversão automática"
```

---

### Task 6: Instalação limpa

**Arquivos:**
- Criar: `installer/INSTALAR.ps1`

**Interfaces:**
- Consome: `config/*.example.json` da Task 2, `REGISTRAR_TAREFA_AGENDADA.ps1`
  já existente.
- Produz: nada consumido por tarefas posteriores.

- [ ] **Passo 1: Escrever o script**

```powershell
<#
    Instalação limpa do MILK.

    Seguro de rodar numa máquina já instalada: cada passo verifica antes
    se o destino existe, e não refaz o que já está pronto. Os passos 4 e
    5 são os únicos que dependem de rede e concentram os 250 MB que o
    repositório não carrega.

    Uso:
        powershell -ExecutionPolicy Bypass -File installer\INSTALAR.ps1
#>

$ErrorActionPreference = "Stop"

$Raiz         = "C:\JARVIS"
$ModeloUrl    = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
$ModeloDest   = Join-Path $Raiz "models\ggml-base.bin"
$ModeloBytes  = 147951465
$WhisperDir   = Join-Path $Raiz "third_party\whisper-prebuilt"

Set-Location $Raiz

# --- 1. Python ---
$versao = (& python -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
if ([version]$versao -lt [version]"3.12") {
    throw "Python $versao encontrado. O MILK exige 3.12 ou mais novo."
}
Write-Host "Python $versao" -ForegroundColor Green

# --- 2. Dependências ---
Write-Host "Instalando dependências..."
& python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install falhou" }

# --- 3. config/local/ a partir dos exemplos ---
$local = Join-Path $Raiz "config\local"
New-Item -ItemType Directory -Force -Path $local | Out-Null

foreach ($nome in @("audio_device", "whisper_local")) {
    $destino = Join-Path $local "$nome.json"
    if (Test-Path $destino) {
        Write-Host "config/local/$nome.json já existe, mantido."
    } else {
        Copy-Item (Join-Path $Raiz "config\$nome.example.json") $destino
        Write-Host "config/local/$nome.json criado do exemplo." -ForegroundColor Yellow
    }
}

# --- 4. Modelo do Whisper (148 MB) ---
if ((Test-Path $ModeloDest) -and ((Get-Item $ModeloDest).Length -eq $ModeloBytes)) {
    Write-Host "Modelo do Whisper já presente."
} else {
    Write-Host "Baixando o modelo do Whisper (148 MB)..."
    New-Item -ItemType Directory -Force -Path (Split-Path $ModeloDest) | Out-Null
    try {
        Invoke-WebRequest -Uri $ModeloUrl -OutFile $ModeloDest
    } catch {
        throw "Download do modelo falhou: $_`nRode INSTALAR.ps1 de novo; os passos anteriores serão pulados."
    }
}

# --- 5. Binário do Whisper ---
if (Test-Path (Join-Path $WhisperDir "Release\whisper-cli.exe")) {
    Write-Host "whisper-cli já presente."
} else {
    Write-Host "whisper-cli ausente em $WhisperDir." -ForegroundColor Yellow
    Write-Host "Rode installer\INSTALAR_WHISPER_PRECOMPILADO.ps1 e depois este script de novo."
    exit 1
}

# --- 6. Microfone ---
$audio = Get-Content (Join-Path $local "audio_device.json") | ConvertFrom-Json
if ($audio.input_device -eq 0) {
    Write-Host "Escolha o microfone:" -ForegroundColor Cyan
    & python "Selecionar_Microfone.py"
} else {
    Write-Host "Microfone já configurado (índice $($audio.input_device))."
}

# --- 7. Tarefa agendada ---
& powershell -ExecutionPolicy Bypass -File (Join-Path $Raiz "installer\REGISTRAR_TAREFA_AGENDADA.ps1")

# --- 8. Provar que funciona ---
Write-Host "Validando a instalação..."
& python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "os testes falharam; a instalação não está sã" }

Write-Host ""
Write-Host "MILK instalado. Versão: $(& python 'src\main.py' '--version')" -ForegroundColor Green
```

- [ ] **Passo 2: Verificar que é seguro nesta máquina**

Rodar: `powershell -ExecutionPolicy Bypass -File installer\INSTALAR.ps1`

Esperado: relata "já existe" / "já presente" nos passos 3, 4, 5 e 6, não
baixa nada, re-registra a tarefa e termina com os testes passando e a
versão impressa. **Nenhum arquivo de `config/local/` pode ser sobrescrito.**

Conferir depois: `cat config/local/audio_device.json` mantém o índice
original.

- [ ] **Passo 3: Commitar**

```bash
git add installer/INSTALAR.ps1
git commit -m "feat: instalação limpa validada por testes"
```

---

### Task 7: Reconciliar o executável com o ponto de entrada

**Arquivos:**
- Modificar: `installer/build_exe.ps1:11-16`

**Interfaces:**
- Consome: nada.
- Produz: nada.

- [ ] **Passo 1: Trocar o alvo do empacotamento**

`src/main.py` é o ponto de entrada único declarado; o executável empacota
`MILK_Command_Center.py`, que é o painel de monitoração. Em
`installer/build_exe.ps1`, trocar a verificação e o alvo:

```powershell
if (-not (Test-Path ".\src\main.py")) {
    throw "src\main.py não encontrado."
}

pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "MILK" `
  --add-data "assets;assets" `
  --add-data "config;config" `
  .\src\main.py
```

- [ ] **Passo 2: Registrar a limitação conhecida**

Acrescentar no topo de `installer/build_exe.ps1`:

```powershell
# ATENÇÃO: este build ainda NÃO inclui models/ (148 MB) nem
# third_party/ (108 MB). O executável gerado sai sem o modelo do Whisper
# e sem o binário que o executa, ou seja, sem reconhecimento de voz.
# Nesta máquina isso não aparece, porque os arquivos existem em
# C:\JARVIS e os caminhos em config/local/whisper_local.json são
# absolutos. Resolver na fase que tratar de distribuição.
```

- [ ] **Passo 3: Verificar que o script ainda é válido**

Rodar: `powershell -NoProfile -Command "& { . { $null = [ScriptBlock]::Create((Get-Content -Raw installer\build_exe.ps1)) }; 'sintaxe ok' }"`
Esperado: `sintaxe ok`

Não rodar o build em si: leva minutos e produz 200 MB em `dist/` sem
acrescentar informação a esta tarefa.

- [ ] **Passo 4: Commitar**

```bash
git add installer/build_exe.ps1
git commit -m "fix: empacota o ponto de entrada real, não o painel"
```

---

## Verificação final

- [ ] `python -m pytest -q` — todos passam (esperado: 54)
- [ ] `python src/main.py --version` imprime versão e commit
- [ ] `git status --porcelain` vazio
- [ ] `git ls-files config/ | grep -E "audio_device.json|whisper_local.json"` não retorna nada
- [ ] `cat logs/update.log` tem ao menos uma linha da verificação da Task 5
- [ ] O MILK sobe: `Start-ScheduledTask -TaskName MILK_Assistant`, e o
      overlay aparece
