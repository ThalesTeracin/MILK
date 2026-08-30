# CONTEXT — MILK

## Objetivo atual

Deixar a MILK com uma cadeia de cérebros em vez de um só, para que ela
continue respondendo quando o gateway principal estiver fora do ar ou
uma assinatura estiver indisponível.

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
- Nada commitado. Há renomeações para `archive/` em staging, de antes
  deste trabalho.

## Próximo passo exato

Rotacionar as duas chaves expostas e rodar `python Testar_Provedores.py`
para confirmar que as novas respondem.
