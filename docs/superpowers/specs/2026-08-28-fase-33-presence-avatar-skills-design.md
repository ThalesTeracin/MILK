# Fase 33 — Integração profunda Presence + Avatar + Skills — Design

**Data:** 2026-08-28
**Branch:** `fase-33`
**Base:** `master` em `ee2fa3e` (fase 32 entregue)

## Problema

O roadmap chama a fase 33 de "integração profunda", e o levantamento mostrou
por quê: os três subsistemas existem, mas não se falam.

**As skills são inalcançáveis.** `src/skills/advanced_router.py` não é
importado por nenhum ponto do aplicativo — só por `Testar_Fase31.py`, um
script de teste manual. Falar "status do git" ou "abrir projetos" não faz
nada. As quatro skills embutidas nunca rodaram fora daquele script.

**O avatar tem duas verdades.** `MilkCore.activity` vive em memória e move o
overlay de `src/presence/unified_app.py`. Em paralelo,
`src/avatar/runtime_state.py` grava `data/milk_runtime_state.json`, lido por
`src/overlay/mini_overlay.py` e `src/avatar/avatar_window.py` — mas nada no
aplicativo em execução escreve nesse arquivo. O mini overlay mostra o estado
padrão para sempre. `src/avatar/speaker_state_patch.py` são seis linhas de
instrução ("use this mixin in the existing NaturalSpeaker") que nunca foram
aplicadas.

**A interface congela.** `UnifiedApp._poll_events` roda na thread do Tk e
chama `_on_heard`, que chama `core.handle(text)` — a chamada de IA inteira,
a memória e o TTS acontecem dentro da thread que deveria estar animando. O
`after()` para, e o avatar congela em "pensando", que é exatamente quando ele
deveria se mexer. O próprio código documenta isso como limitação conhecida.

## Objetivo

Uma única fonte de verdade para o estado, as skills alcançáveis por voz, e a
interface livre para animar enquanto o cérebro trabalha.

## Decisões tomadas

Registradas com o motivo, para não serem re-litigadas na implementação.

1. **As duas superfícies de avatar continuam vivas** — o overlay grande do
   `unified_app` e o mini overlay em processo separado. Logo, o arquivo de
   estado é contrato entre processos de verdade, não detalhe interno.
2. **Roteamento de skill é por palavra-chave local, sem IA.** Rápido, sem
   token, e continua funcionando com o provedor de IA fora do ar. O custo
   aceito: só casa as frases previstas.
3. **O contrato de estado carrega só a atividade.** Os campos `speaking`,
   `listening`, `thinking`, `emotion` e `last_text` do arquivo atual
   desaparecem — nunca foram escritos por ninguém, e `emotion` não tem quem
   decida seu valor.
4. **Frescor por carimbo de tempo, não por apagar o arquivo na saída.** Uma
   queda ou um `kill` não deixam estado mentiroso para trás.
5. **Um módulo dedicado é o dono do estado**, em vez de uma property no
   `MilkCore` ou de uma thread publicadora. É a única forma testável sem
   subir Tkinter, MilkCore ou microfone.
6. **As skills devolvem frase e dados.** O MILK fala a frase; os dados ficam
   para log, teste e para o Command Center mostrar o número exato sem
   re-executar a skill.

## Arquitetura

### Módulo de estado: `src/core/activity_state.py`

Dono único da atividade. Fica em `core/` e não em `avatar/` porque quem
escreve é o `MilkCore`, e o cérebro não deve importar de um pacote de
interface.

```python
definir_atividade(nome)   # "idle" | "listening" | "thinking" | "speaking"
atividade()               # o valor em memoria, para quem esta no mesmo processo
ler_do_arquivo()          # (atividade, fresco: bool), para o mini overlay
pulsar()                  # regrava o carimbo sem mudar a atividade
```

`definir_atividade` guarda em memória e escreve `data/milk_runtime_state.json`
no formato `{"activity": "thinking", "at": 1756400000.0}`.

`ler_do_arquivo` devolve `("idle", False)` quando o arquivo não existe, está
corrompido, tem formato inesperado, ou quando o carimbo passou do limite de
frescor.

**Limite de frescor: 5 segundos.**

**Por que `pulsar()` precisa existir:** o estado só é escrito quando muda. Com
o MILK parado ouvindo, o carimbo envelheceria e o mini overlay o declararia
desligado enquanto ele está vivo. `UnifiedApp` já tem um `after()` de 1 em 1
segundo (`_idle_watch`); ele passa a chamar `pulsar()`. Cinco pulsos podem se
perder antes de o mini declarar o MILK morto.

Mudanças nos consumidores:

- `MilkCore` deixa de guardar `self.activity` como atributo e passa a chamar
  `definir_atividade`.
- `UnifiedApp._animate` lê `atividade()` da memória — não toca disco a cada
  120 ms.
- `overlay/mini_overlay.py` passa a importar de `core.activity_state` e a
  tratar o caso "não fresco" mostrando que o MILK está desligado.
- `avatar/runtime_state.py`, `avatar/avatar_window.py`,
  `avatar/speaker_state_patch.py` e `Testar_Avatar_Animado.py` recebem o
  cabeçalho `SUBSTITUÍDO (Fase 33)`, na mesma convenção de
  `MILK_Presence.py`: ficam no lugar, como referência histórica, e não são
  editados nem usados. Nenhum deles é apagado — `Testar_Avatar_Animado.py`
  importa `runtime_state`, e apagar um sem o outro deixaria script quebrado
  no repositório.

### Skills alcançáveis

`MilkCore.handle` consulta `AdvancedSkillRouter.route_local(text)` logo antes
de `nlu.interpret`. Casou, executa e fala. Não casou, o fluxo segue
exatamente como hoje.

**O gate duplicado colapsa.** O conjunto `RISKY` do router sai. Ele é uma
cópia pior do que já está em `config/permission_profiles.json`: as mesmas
ações (`delete_file`, `git_push`, `deploy`, `send_email`, `system_change`,
`arbitrary_shell`), sem distinguir negar de confirmar, e com `admin_shell`
onde o perfil diz `open_admin`. O router passa a chamar
`PermissionManager.check(nome_da_skill)` e a reaproveitar o
`_pending_confirmation` que o `handle` já usa para "diga confirmar".

Nenhuma das skills reais é sensível, então na prática o gate fica quieto —
mas fica certo para quando não estiver.

**Três duplicações somem:**

- `BuiltinSkills.system_status` devolve `{cpu, memory, disk}`;
  `WindowsAgent.system_status` devolve "CPU em 30 por cento, memória em 60
  por cento e disco C em 45 por cento" e já está ligado ao intent
  `system_status`. A skill sai; o agente fica.
- `BuiltinSkills.web_search` abre o Google pelo `webbrowser` do sistema, sem
  nenhum controle sobre a página aberta. `BrowserAgent.search` dirige uma
  página do Playwright, devolve "Pesquisei por X." e já está ligado ao intent
  `browser_search` — e é o que permite os `browser_click_text` e
  `browser_fill` que vêm depois. A skill sai; o agente fica. O ramo
  "pesquisa no google" de `route_local` sai junto.
- `config/skills.json` declara quatro skills `restricted` — `git_push`,
  `deploy`, `send_email`, `system_change` — sem implementação nenhuma: nomes
  sem nada atrás. Saem do arquivo. O registro passa a listar só o que existe.

**Formato de retorno das skills:**

```python
{"ok": True, "fala": "Estou na branch master, sem alterações pendentes.",
 "dados": {"branch": "master", "pendentes": 0}}
```

O `MilkCore` fala o campo `fala`. `dados` fica para log, teste e para o
Command Center.

Sobram duas skills ligadas por voz: `git_status` e `open_projects`.

Isso é pouco, e é honesto: das quatro skills embutidas, duas já existiam com
implementação melhor em outro lugar do sistema. O ganho da fase não é o
número de skills — é que a rota existe, passa pelo gate de permissão certo, e
a próxima skill escrita já nasce alcançável.

### A thread do Tk

Uma thread de trabalho consome a fila de frases ouvidas e chama
`core.handle`. A thread do Tk só anima, lê `atividade()` da memória e faz
fade in/out.

**Tkinter não aceita chamada de outra thread.** `_fade_in`, `_fade_out` e
qualquer coisa que toque em `self.overlay` continuam na thread do Tk. Hoje
`_on_heard` decide o fade olhando `core.state` antes e depois do `handle`.
Depois da mudança, a thread de trabalho não chama fade: ela só muda estado, e
a thread do Tk decide aparecer ou sumir a partir de `core.state`, no
`_idle_watch` que já roda de segundo em segundo. O fade deixa de ser
consequência direta do comando e passa a ser consequência do estado.

**Risco declarado:** `MilkCore.handle` nunca rodou fora da thread principal.
Se algum agente tocar em Tkinter indiretamente — `browser`, `coder`,
`windows_agent` abrindo alguma janela — isso vira erro só em execução, e
nenhum teste pega. A implementação varre os agentes atrás disso antes de
mexer; o que aparecer vira tarefa própria do plano, não surpresa.

## Tratamento de falhas

O estado é conveniência de interface: nada nele pode derrubar a voz.

- Escrita que falhe (disco cheio, arquivo travado por antivírus) é engolida
  com aviso. O valor em memória continua certo e o overlay do processo
  principal segue funcionando; só o mini fica cego.
- Leitura corrompida devolve `("idle", False)` — o mesmo que arquivo ausente.
- Skill que levante exceção vira frase de erro falada, não traceback: é como
  o `handle` já trata as outras ações.

## Testes

Três arquivos novos:

- `tests/test_activity_state.py` — transição, carimbo, frescor com carimbo
  forjado (sem `sleep`), arquivo ausente, arquivo corrompido, escrita que
  falha.
- `tests/test_skill_router.py` — frases que casam e que não casam, gate
  negando, gate pedindo confirmação, skill que levanta exceção. Com
  `PermissionManager` de perfil forjado, sem tocar em git, disco ou navegador
  reais.
- `tests/test_unified_app_eventos.py` — a fila e a transição de estado com um
  `MilkCore` falso, sem Tk.

**Verificações manuais, declaradas como não automatizadas:**

1. O avatar continua pulsando durante uma chamada de IA longa.
2. O mini overlay declara "desligado" alguns segundos depois de o MILK ser
   fechado.

Nenhuma das duas conta como aprovada por teste. São comportamento de janela.

## Fora de escopo

- Emoção do avatar — nada decide emoção hoje.
- Skills novas — a fase liga as que existem, não inventa outras.
- IA escolhendo skill — descartado na decisão 2.
- Registrar a tarefa agendada `MILK_Assistant` e resolver a ausência de
  remote git. São pendências abertas da fase 32 e continuam sendo decisão do
  usuário, não trabalho desta fase.

## Restrições herdadas

Valem as mesmas da fase 32, e não se repetem em cada tarefa:

- Python mínimo 3.12; máquina de referência 3.14.7.
- Imports absolutos com `src/` no `sys.path` (`from core.config import ...`),
  nunca relativos. Import relativo quebra neste projeto.
- Testes em `tests/`, rodados da raiz do repositório com `python -m pytest`.
  `tests/conftest.py` já põe `src/` no path.
- Tudo escrito para humanos — comentários, docstrings, mensagens, commits —
  em português.
- Configuração de máquina vai para `config/local/`, resolvida por
  `core.config.config_path`.
