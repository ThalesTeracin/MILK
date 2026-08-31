# CONTEXT — MILK

## Objetivo atual

Projeto publicado no GitHub e revisão final da fase 33 concluída, ambos
em 2026-08-31. O próximo passo é rotacionar as chaves de Groq e Gemini,
que devem ser tratadas como expostas. Antes disso, duas conferências
visuais da fase 33 dependem só de você (ver pendência 1).

## Progresso concluído (2026-08-30, branch `fase-33`)

Cadeia de provedores implementada no router, com TDD.

- `src/ai/router.py` — reescrito. Lê `config/providers.json` e
  `AI_PROVIDER_ORDER`, monta a lista de provedores e tenta um a um.
  Falha de conexão, timeout ou HTTP diferente de 200 passa a vez ao
  próximo. Resposta 200 com conteúdo vazio **não** troca de provedor
  (é orçamento de tokens curto; repetir noutro gateway daria o mesmo
  resultado). Nova classe `Provedor`. `base_url`, `model` e `api_key`
  viraram propriedades do provedor ativo, preservando quem já as lia.
- `config/providers.json` — entradas novas `omniroute` (localhost:20128)
  e `freellmapi` (localhost:3001); todas as entradas ganharam
  `base_url_env` e `model_env`, para o `.env` sobrepor o versionado.
- `tests/test_ai_router_cadeia.py` — 10 testes novos (ordem, queda para
  o próximo, erro HTTP, chave por provedor, sobreposição pelo `.env`,
  cadeia inteira fora do ar, chave `_note` não vira provedor).
- `Configurar_Provedores.py` — parou de reescrever o `.env` do zero
  (apagava voz, caminhos e orçamento de tokens); agora mescla e
  pergunta URL/modelo de qualquer provedor que os declare.
- `Configurar_Cerebro_MILK.py` — põe o 9Router em primeiro sem apagar
  as reservas da ordem.
- `Testar_Provedores.py` e `Testar_IA.py` — corrigidos: chamavam
  `router.interpret()`, método que não existe, e importavam por
  `src.ai.router`, fora da convenção do projeto.
- `Testar_Sistema.py` — confere URL e modelo efetivos (env sobrepõe
  arquivo), sem o caso especial do 9Router.
- `.env.example` e `.env` — variáveis `OMNIROUTE_*` e `FREELLMAPI_*`
  adicionadas; ordem passou a
  `9router_custom,omniroute,freellmapi,openrouter_free,groq,gemini,nvidia`.

## Verificado

- `python -m pytest` — 238 testes passando.
- Cadeia carregada do `.env` real: ativo `9Router / Custom
  [orcustom/z-ai/glm-5.3-flash]`.
- `Testar_Sistema.py` seção 6b: `localhost:20128 respondendo`.

## Decisões de 2026-08-30 (tarde)

- **OmniRoute removido.** Estava rodando em modo dev na porta 20128, a
  mesma do 9Router, e o `NINEROUTER_API_KEY` do `.env` levava 401
  `Invalid API key` nele: a MILK estava sem cérebro sem que a
  verificação percebesse (a seção 6b só abria TCP). Processo encerrado e
  `C:\Users\Terac\Downloads\OmniRoute` apagado (2,7 GB).
- **9Router recolocado** na 20128 com `9router -t -n` (v0.5.59).
  `AIRouter.test()` respondeu `OK`.
- **FreeLLMAPI descartado.** Ele não tem modelos próprios: empilha
  contas gratuitas de terceiros, as mesmas que a cadeia da MILK já
  chama direto. Não compensa manter um serviço a mais de pé. O clone
  foi apagado.
- As entradas `omniroute` e `freellmapi` continuam em
  `config/providers.json` (custam nada e servem se voltarem), mas saíram
  do `AI_PROVIDER_ORDER`, que agora é
  `9router_custom,openrouter_free,groq,gemini,nvidia`.

## Decisão de 2026-08-31 — modelo do 9Router trocado

`NINEROUTER_MODEL` passou de `orcustom/z-ai/glm-5.3-flash` para
`orcustom/qwen/qwen3.8-flash`.

O motivo apareceu no log do router: *"o modelo gastou todo o max_tokens no
raciocínio e não sobrou resposta"*. O `AI_MAX_TOKENS` é 180, curto de
propósito porque a MILK fala as respostas; o glm raciocina antes de
responder e o raciocínio consome o orçamento inteiro. Como resposta vazia
**não** faz a cadeia passar a vez (decisão de 30/08), a MILK ficava muda
com o provedor no ar -- o `Testar_Provedores.py` acusava "respondeu vazio".

Medido antes de trocar, mesmo prompt e mesmos 180 tokens: o glm respondeu
2 de 3 vezes (é intermitente, não sempre quebrado) e o qwen 3 de 3, com
frases curtas. Outros candidatos foram descartados com evidência:
`gemini-3.5-flash-lite` e `gemini-3.7-flash` devolvem HTTP 402 Payment
Required, `nemotron-3.5-lightning:free` vaza o raciocínio no texto falado
("Here's a thinking process:") e `liquid/lfm-2.5-2.6b:free` volta vazio.

Depois da troca: `Testar_Provedores.py` -- 3 de 3 provedores no ar.

Backup do arquivo de ambiente anterior em `.env.bak-20260831`.

## Reservas ativas (verificado em 2026-08-30)

`python Testar_Provedores.py` -- 3 de 3 provedores no ar:

1. 9Router / Custom -- `localhost:20128` [`orcustom/z-ai/glm-5.3-flash`]
2. Groq -- [`openai/gpt-oss-20b`]
3. Google Gemini -- [`gemini-2.5-flash`]

A queda foi testada de verdade, não só no teste unitário: com o 9Router
derrubado de propósito, `AIRouter.chat()` respondeu "Está no ar." pelo
Groq e registrou a falha do primeiro no log.

## Pendências

- **Rotacionar as chaves de Groq e Gemini.** As duas foram digitadas no
  chat do assistente, então devem ser tratadas como expostas: gerar
  novas em `console.groq.com/keys` e `aistudio.google.com/apikey`,
  revogar as antigas e colar as novas com
  `python Configurar_Provedores.py`, que usa `getpass` e não ecoa.
- `OPENROUTER_API_KEY` e `NVIDIA_API_KEY` continuam vazias -- opcional,
  a cadeia já tem duas reservas.

## Git

`origin` criado em 2026-08-31: **https://github.com/ThalesTeracin/MILK**,
repositório **privado**, branch padrão `master`, 264 arquivos enviados.
O updater da fase 32 finalmente tem de onde puxar.

Histórico linear preservado. Dois commits novos entraram antes do push:
as 27 renomeações para `archive/` (que estavam em staging desde antes da
fase 33) e a saída de `data/session_memory.json` do versionamento.
Árvore limpa, 238 testes passando depois das duas mudanças.

Conferido no remoto: o `.env` real não subiu (só o `.env.example`) e o
`data/session_memory.json` também não.

Em 31/08, depois do push, entraram as correções da revisão final da fase
33: `5d7cc9a` (o "pensando" passa a valer enquanto o cérebro trabalha),
`321f622` (estado de runtime publicado por troca de nome) e `a17bed7`
(plano para de ensinar os blocos substituídos). 242 testes passando.

## Pendências numeradas (atualizado em 2026-08-31)

Concluídos em 31/08: publicação no GitHub (era 1), a revisão dos
arquivos de `data/` antes de publicar (era 2) e o destino das 27
renomeações para `archive/` (era 4). Ver a seção Git acima.

1. **Rotacionar as chaves de Groq e Gemini** (foram digitadas no chat).
   Gerar novas em `console.groq.com/keys` e `aistudio.google.com/apikey`,
   revogar as antigas e gravar com `python Configurar_Provedores.py`,
   que usa `getpass` e não ecoa. É o próximo passo.
2. **Duas conferências visuais da fase 33 — só você pode fazer.**
   (a) `python src/main.py` com o 9Router no ar, dizer "milk", fazer uma
   pergunta que puxe a IA e conferir se o avatar continua se mexendo
   durante a espera **e se o rótulo diz "pensando…"**. Até 31/08 ele dizia
   "ouvindo…" durante toda a resposta; o defeito foi corrigido e nunca foi
   visto na tela por ninguém.
   (b) fechar a MILK, abrir `INICIAR_MILK_MINI_OVERLAY.bat` e conferir se
   ele mostra "MILK · DESLIGADA" em até 5 segundos.
   O resto da fase 33 está fechado: a revisão final foi feita em 31/08,
   três achados corrigidos e três parked mantidos com o motivo revisto.
   Detalhe em
   `.superpowers/sdd/2026-08-28-fase-33-presence-avatar-skills/progress.md`.
3. **Tarefa agendada `MILK_Assistant` nunca foi registrada** -- a MILK
   não sobe sozinha no logon. `installer/REGISTRAR_TAREFA_AGENDADA.ps1`
   existe e nunca rodou; você decidiu não registrar nada no Windows,
   então isto só muda se você quiser.
4. **Apagar a branch `fase-32-backup-andaimes`** quando estiver claro
   que não é mais necessária.
5. **Campos de chave deixados em aberto, de propósito.**
   `OPENROUTER_API_KEY` e `NVIDIA_API_KEY` estão vazias e continuam no
   `AI_PROVIDER_ORDER`: um provedor sem chave é pulado em silêncio, e
   basta colar a chave para ele entrar na cadeia, sem tocar em código.
   O usuário não tem mais conta OpenRouter.
6. **Investigar usar as assinaturas que o usuário já paga, em vez de
   API avulsa.** Restrição declarada em 30/08: *não* quer pagar nenhuma
   API por fora. Ele tem conta do Claude Code e do ChatGPT, e quer a
   MILK conectada a elas.
   **O usuário informou em 30/08 que o 9Router já tem todos esses
   provedores**, incluindo as contas de assinatura. Se confirmar, não há
   código novo a escrever: basta escolher o modelo certo no painel do
   9Router e apontar `NINEROUTER_MODEL`. Confirmar no painel antes de
   cogitar qualquer provedor de tipo "CLI" no router.
   A única coisa que o 9Router não cobre é o **FreeLLMAPI**, que o
   usuário quer manter como opção -- por isso a entrada `freellmapi`
   segue em `config/providers.json` (porta 3001), pronta para receber
   chave e modelo, mesmo com o clone do repositório já apagado.
