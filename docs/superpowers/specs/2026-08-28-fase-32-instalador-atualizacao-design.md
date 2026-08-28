# Fase 32 — Instalador final e atualização segura

Data: 2026-08-28
Estado: proposto, aguardando implementação

## Problema

O MILK é instalado copiando arquivos à mão e atualizado do mesmo jeito. Isso
produz três falhas concretas, todas já observadas neste repositório:

**Config de máquina é sobrescrita pela atualização.**
`config/audio_device.json` guarda `{"input_device": 24}` — o índice do
microfone desta máquina — e `config/whisper_local.json` guarda caminhos
absolutos para `C:\JARVIS\third_party\...`. Ambos estão versionados no git.
Um `git pull` sobrescreve a escolha de dispositivo do usuário. O README
antigo instruía "NÃO apague `config/whisper_local.json`", o que documenta o
problema em vez de resolvê-lo.

**Não há como saber o que está rodando.** Não existe arquivo `VERSION`, nem
`--version`, nem registro de atualizações. Quando o comportamento muda, não
há resposta rápida para "o que mudou e quando".

**Uma atualização com defeito não tem volta.** Nada valida a atualização
antes de deixá-la ativa, e nada a reverte. O processo em segundo plano
(`MILK_Assistant`) segue rodando durante a troca de arquivos, com o banco
SQLite aberto em modo WAL.

## Decisões

Duas decisões do usuário guiam o desenho:

1. **Alvo:** resolver esta máquina agora, com versionamento e separação
   código/dados desde já, para que a distribuição para outras máquinas não
   exija refazer o trabalho.
2. **Mecanismo:** atualização por `git pull` protegida por um script, com
   reversão automática. Não haverá pacote versionado nesta fase.

## Escopo

Dentro: separação de config de máquina, versionamento, script de
atualização com reversão, script de instalação limpa, e a reconciliação do
ponto de entrada entre o executável e a tarefa agendada.

Fora: empacotamento para distribuição (ver Pendências conhecidas),
atualização automática sem intervenção, e qualquer interface gráfica para
essas operações.

## Componente 1 — Resolvedor de config

`src/core/config.py` expõe uma função:

```python
def config_path(nome):
    """
    Devolve config/local/<nome> se existir, senão config/<nome>.
    """
```

`config/local/` é ignorado pelo git e guarda o que pertence a esta máquina.
Os três pontos de leitura passam a usar a função:

| Arquivo | Linha | Hoje |
|---|---|---|
| `src/voice/listener.py` | 12 | `Path("config/whisper_local.json")` |
| `Selecionar_Microfone.py` | 5 | `Path("config/audio_device.json")` |
| `MILK_Command_Center.py` | 370 | `ROOT / "config" / "whisper_local.json"` |

`Selecionar_Microfone.py` é o único que **escreve**, e passa a escrever
sempre em `config/local/`. Se escrevesse no arquivo versionado, o problema
retornaria na execução seguinte.

`config/audio_device.json` e `config/whisper_local.json` saem do controle de
versão (`git rm --cached`; o conteúdo permanece em disco e é movido para
`config/local/`). Entram no lugar `config/audio_device.example.json` e
`config/whisper_local.example.json`, que documentam o formato e servem de
semente ao instalador.

Consequência aceita: uma máquina nova deixa de receber os caminhos do
Whisper prontos. É o comportamento correto — os caminhos atuais são
absolutos e válidos apenas nesta máquina — mas transfere esse trabalho para
o instalador.

## Componente 2 — Atualização segura

`installer/Atualizar_MILK.ps1`, na ordem:

```
1. Verifica árvore limpa (git status --porcelain vazio)
   Se houver alteração não commitada, aborta sem tocar em nada.
2. Guarda o commit atual: $antes = git rev-parse HEAD
3. Para a tarefa MILK_Assistant e aguarda o processo terminar
4. git pull
5. Roda a migração de schema (abre LongMemory uma vez)
6. python -m pytest
7. Reinicia a tarefa

Se 4, 5 ou 6 falhar:
   git reset --hard $antes
   reinicia a tarefa
   relata o passo que falhou
```

Três propriedades sustentam esse fluxo:

**O passo 1 é o que torna a reversão segura.** `git reset --hard` descarta
alterações não commitadas. Exigir árvore limpa na entrada é o que garante
que não existe trabalho a destruir na saída.

**O passo 3 precede o passo 5 porque o banco está aberto.** O processo roda
em segundo plano com SQLite em WAL; migrar com ele vivo arrisca lock ou
corrupção. `Stop-ScheduledTask` retorna antes do processo morrer, então o
script aguarda o PID desaparecer, com teto de tempo e falha explícita se
não desaparecer.

**A reversão só é segura enquanto as migrações forem aditivas.** Se o passo
5 concluir e o passo 6 falhar, o código volta e o banco permanece adiante.
Como `LongMemory._migrate()` só executa `ADD COLUMN`, o código anterior
ignora a coluna nova. Isso deixa de valer no dia em que uma migração
remover ou renomear algo. Fica como regra registrada junto de `MIGRATIONS`:
**somente aditivo**. A fase 34 (memória semântica/embeddings) é a primeira
que vai exercitá-la.

## Componente 3 — Versionamento

Arquivo `VERSION` na raiz, texto puro (`32.0`), e `src/core/version.py`:

```python
def version_info():
    """Devolve (versao, commit)."""
```

A versão vem do arquivo e acompanha máquinas sem git; o commit vem de
`git rev-parse` quando disponível e identifica exatamente o código em
execução. `python src/main.py --version` imprime ambos.

O updater registra cada execução em `logs/update.log`:

```
2026-08-28 14:02  32.0 (c53d469) -> 32.1 (a1b2c3d)  OK
2026-08-28 15:40  32.1 (a1b2c3d) -> 32.2 (e4f5g6h)  FALHOU: 2 testes  revertido
```

## Componente 4 — Instalação limpa

`installer/INSTALAR.ps1`:

```
1. Valida Python >= 3.12 (a máquina de referência roda 3.14.7)
2. pip install -r requirements.txt
3. Cria config/local/ a partir dos arquivos .example
4. Obtém o modelo do Whisper (models/ggml-base.bin, 148 MB)
5. Obtém o whisper-prebuilt (third_party/)
6. Roda Selecionar_Microfone para preencher config/local/audio_device.json
7. Registra a tarefa agendada MILK_Assistant
8. python -m pytest para provar que a instalação funciona
```

Os passos 4 e 5 são os únicos que dependem de rede e concentram os 250 MB
que o git não carrega. Falham por causas próprias (rede, disco, URL
alterada), então recebem mensagem específica e podem ser reexecutados
isoladamente: um download de 148 MB interrompido não deve obrigar a refazer
a instalação de dependências.

As origens ficam como constantes no topo do script, uma por artefato, e
cada passo verifica antes se o destino já existe com o tamanho esperado —
em cuja hipótese não baixa nada. É o que faz o instalador ser seguro de
rodar nesta máquina, onde os dois artefatos já estão em disco.

### Reconciliação do ponto de entrada

`installer/build_exe.ps1` empacota `MILK_Command_Center.py`, enquanto a
tarefa agendada executa `src/main.py`. Como `src/main.py` é o ponto de
entrada único declarado desde a unificação de entry points, o executável é
que está incorreto: ele empacota o painel de monitoração, não o assistente.

`build_exe.ps1` passa a empacotar `src/main.py`. O Command Center permanece
disponível como ferramenta separada.

## Critérios de aceitação

1. Após `git pull`, `config/local/audio_device.json` permanece intacto.
2. `Selecionar_Microfone.py` grava em `config/local/`, nunca em `config/`.
3. `Atualizar_MILK.ps1` recusa executar com árvore de trabalho suja.
4. Uma atualização cujos testes falhem deixa o repositório no commit
   anterior e a tarefa `MILK_Assistant` em execução.
5. `python src/main.py --version` imprime versão e commit.
6. Cada execução do updater acrescenta uma linha a `logs/update.log`.
7. A suíte pytest continua passando, com testes novos cobrindo
   `config_path()` e `version_info()`.

## Pendências conhecidas

**O executável sai sem reconhecimento de voz.** `build_exe.ps1` inclui
`assets/` e `config/` via `--add-data`, mas não `models/` nem
`third_party/`. Um `.exe` gerado hoje não leva o modelo do Whisper nem o
binário que o executa. Isso não afeta esta máquina, onde os arquivos
existem em `C:\JARVIS` e os caminhos são absolutos. Afeta a primeira
instalação em outra máquina, e pertence à fase que tratar de distribuição.

**Duas árvores do projeto coexistem.** `C:\Claude-JArvis` divergiu deste
repositório a partir do commit inicial e permanece em disco. O trabalho
útil que havia lá (persona, detecção de fim de fala, migração de schema)
já foi portado para cá em 2026-08-28. Enquanto as duas existirem, há risco
de trabalho ser feito na árvore errada — como já ocorreu com `core/proc.py`,
implementado duas vezes de forma independente.

**O plano de correções usa numeração própria.** Os comentários no código
citam "Fase 1" a "Fase 6" referindo-se a um plano de auditoria distinto do
roadmap de funcionalidades (12 a 36) descrito em `ROADMAP_PROXIMAS_FASES.txt`
e `ROADMAP_ATUALIZADO.txt`. Esse plano não está documentado no repositório;
existe apenas como referências no código.
