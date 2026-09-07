# MILK MASTER PROMPT

## MISSÃO

Você é o engenheiro de software principal responsável por revisar, corrigir, completar, testar e evoluir o projeto **MILK** existente nesta pasta.

A Milk será uma cachorrinha virtual que ficará na área de trabalho do Windows e funcionará como interface visual, de voz e interação do Claude Code.

A Milk NÃO será uma IA independente concorrente.

A arquitetura conceitual principal deve ser:

**Usuário → Milk → Claude Code → Milk → Usuário**

O Claude Code será o cérebro principal.

A Milk será:

* avatar;
* interface;
* ouvidos;
* voz;
* presença na área de trabalho;
* sistema de interação;
* sistema de notificações;
* intermediária entre o usuário e o Claude.

---

# OBJETIVO FINAL

Quero poder usar o computador normalmente e dizer:

"Milk."

A Milk acorda.

Milk:

"Oi, estou aqui."

Eu:

"Milk, construa uma landing page moderna para uma loja."

A Milk entende o comando e envia a solicitação ao Claude Code.

O Claude:

* cria o projeto;
* cria arquivos;
* escreve código;
* instala dependências necessárias;
* executa testes;
* corrige problemas;
* verifica o resultado.

Enquanto isso, Milk mostra visualmente que Claude está trabalhando.

Ao terminar:

Milk:

"Pronto. O Claude terminou."

Esse é o objetivo principal deste projeto.

---

# REGRA FUNDAMENTAL DA ARQUITETURA

Milk não deve tentar substituir o Claude.

Milk recebe comandos, interpreta a interação, organiza tarefas e entrega solicitações ao Claude.

Claude decide como realizar tarefas complexas.

Arquitetura:

```text
Usuário
   ↓
Milk
   ↓
Voice / Interface / Intent Router
   ↓
Task Manager
   ↓
Claude Code
   ↓
Tools / MCP / Skills
   ↓
Resultado
   ↓
Milk
   ↓
Usuário
```

---

# FASE 1 — AUDITORIA COMPLETA DO PROJETO

ANTES DE MODIFICAR QUALQUER COISA:

Analise profundamente todos os arquivos existentes nesta pasta.

Descubra:

1. arquitetura atual;
2. linguagens utilizadas;
3. dependências;
4. módulos;
5. funcionalidades existentes;
6. funcionalidades parcialmente implementadas;
7. bugs;
8. código duplicado;
9. código abandonado;
10. arquivos obsoletos;
11. problemas de organização;
12. riscos de segurança;
13. problemas de performance;
14. integrações existentes;
15. recursos que já funcionam corretamente.

Não assuma que algo está quebrado sem verificar.

Não reescreva o projeto inteiro simplesmente porque outra arquitetura parece mais bonita.

PRESERVE TODO CÓDIGO FUNCIONAL.

A prioridade é:

**entender → preservar → corrigir → melhorar → testar**

---

# BACKUP ANTES DE ALTERAÇÕES GRANDES

Antes de mudanças estruturais importantes:

crie backup do estado funcional atual do projeto.

Nunca deixe o projeto sem uma versão recuperável.

---

# FASE 2 — DIAGNÓSTICO

Depois da auditoria, apresente um diagnóstico breve contendo:

## FUNCIONANDO

Recursos que já estão funcionando.

## PARCIAL

Recursos existentes mas incompletos.

## QUEBRADO

Recursos com problemas.

## AUSENTE

Recursos necessários que ainda não existem.

## RISCOS

Problemas de arquitetura, segurança ou estabilidade.

Depois do diagnóstico:

NÃO PARE.

Comece imediatamente as correções e implementações necessárias.

---

# FASE 3 — AVATAR MILK

Milk deve existir visualmente na área de trabalho.

Ela deve funcionar sem depender constantemente de uma janela tradicional aberta.

Criar uma arquitetura clara para o avatar.

Estados mínimos:

```text
IDLE
LISTENING
THINKING
WORKING
SPEAKING
HAPPY
CONFUSED
SLEEPING
ALERT
ERROR
```

Exemplos:

IDLE:
Milk está tranquila.

LISTENING:
Milk percebeu que foi chamada.

THINKING:
pedido está sendo interpretado.

WORKING:
Claude está executando tarefa.

SPEAKING:
Milk está falando.

HAPPY:
tarefa concluída.

ERROR:
ocorreu problema.

SLEEPING:
computador ficou ocioso.

---

# ANIMAÇÕES

Avaliar e implementar progressivamente:

* respiração;
* piscar dos olhos;
* movimento dos olhos;
* movimento das orelhas;
* pequena movimentação corporal;
* sentar;
* dormir;
* acordar;
* caminhar pela área de trabalho;
* olhar para o cursor ocasionalmente;
* reagir ao usuário;
* reação quando chamada;
* reação quando Claude termina uma tarefa;
* reação a erros;
* movimento da boca durante fala;
* sincronização labial simples;
* latido ocasional.

As animações não podem consumir CPU excessivamente.

---

# FASE 4 — WAKE WORD

Milk deve reconhecer quando o usuário disser:

"Milk"

Exemplos:

"Milk."

"Milk, venha aqui."

"Milk, abra o navegador."

"Milk, crie um projeto."

"Milk, veja esse erro."

"Milk, construa uma landing page."

Depois da palavra Milk:

entrar imediatamente em modo de escuta.

Objetivos:

* baixa latência;
* poucos falsos positivos;
* português brasileiro;
* funcionamento contínuo;
* consumo baixo de CPU.

---

# FASE 5 — RECONHECIMENTO DE VOZ

Priorizar solução local existente quando já estiver funcionando.

Requisitos:

* português brasileiro;
* boa precisão;
* baixa latência;
* funcionamento em background;
* não abrir terminal visível;
* não bloquear interface;
* detectar início da fala;
* detectar silêncio/fim da fala;
* enviar transcrição ao Intent Router.

Evitar capturar continuamente áudio desnecessário.

---

# FASE 6 — TEXT TO SPEECH

Milk deverá falar com voz feminina natural.

Características:

* feminina;
* natural;
* suave;
* simpática;
* português brasileiro;
* sem aspecto robótico exagerado.

Criar sistema de fila de fala.

Nunca permitir duas falas sobrepostas.

Comandos:

"Milk, pare."

deve interromper a fala atual.

---

# PERSONALIDADE DA MILK

Milk deve ser:

* simpática;
* carinhosa;
* inteligente;
* objetiva;
* confiável.

Evitar infantilização excessiva.

Milk é uma cachorrinha inteligente que auxilia Claude.

Exemplo:

Usuário:

"Milk."

Milk:

"Oi, estou aqui."

Usuário:

"Crie uma landing page."

Milk:

"Claro. Vou passar isso para o Claude."

Quando terminar:

"Pronto. O Claude terminou."

---

# FASE 7 — CLAUDE COMO CÉREBRO PRINCIPAL

Esta regra é fundamental.

Quando Milk receber tarefas complexas:

encaminhar para Claude.

Exemplos:

"Milk, construa uma landing page."

"Milk, analise esse projeto."

"Milk, corrija meu código."

"Milk, crie uma API."

"Milk, investigue esse erro."

"Milk, organize esse projeto."

Claude deve poder:

* analisar arquivos;
* criar arquivos;
* editar código;
* executar comandos;
* testar aplicações;
* criar projetos;
* investigar erros;
* instalar dependências;
* navegar em estrutura de diretórios;
* usar ferramentas;
* usar MCP;
* usar Skills.

Nunca fingir que uma ação foi executada.

---

# FASE 8 — INTENT ROUTER

Criar um módulo responsável por entender o tipo de pedido.

Nem todo pedido precisa chamar Claude.

Exemplo:

"Milk, que horas são?"

Pode ser resolvido localmente.

"Milk, abra o bloco de notas."

Pode usar uma ferramenta Windows.

"Milk, construa uma aplicação."

Deve chamar Claude.

Categorias sugeridas:

```text
LOCAL_COMMAND
SYSTEM_TOOL
CLAUDE_TASK
CONVERSATION
MEMORY
SCREEN_ANALYSIS
FILE_OPERATION
BROWSER_TASK
```

Fluxo:

```text
Voice
 ↓
Transcription
 ↓
Intent Router
 ↓
Decisão
```

---

# FASE 9 — TASK MANAGER

Criar um Task Manager central.

Milk NÃO deve disparar tarefas complexas diretamente.

Fluxo correto:

```text
Milk
 ↓
Intent Router
 ↓
Task Manager
 ↓
Claude / Tools
```

---

# FILA DE TAREFAS

Criar fila persistente.

Permitir:

"Milk, crie uma landing page."

Depois:

"Milk, depois analise meu projeto Python."

Depois:

"Milk, quando terminar abra a pasta."

Fila:

```text
1. Criar landing page
2. Analisar projeto
3. Abrir pasta
```

Cada tarefa deve possuir:

* ID;
* descrição;
* prompt original;
* data de criação;
* status;
* prioridade;
* origem;
* progresso;
* resultado;
* erro;
* início;
* término.

---

# STATUS DE TAREFA

Usar:

```text
QUEUED
RUNNING
WAITING
PAUSED
COMPLETED
FAILED
CANCELLED
INTERRUPTED
```

---

# PRIORIDADES

Usar:

```text
LOW
NORMAL
HIGH
URGENT
```

Exemplo:

"Milk, isso é urgente."

Nova tarefa recebe:

URGENT

Não interromper operações críticas ou destrutivas de maneira insegura.

---

# CONTROLE DA FILA POR VOZ

Milk deverá entender:

"Milk, o que você está fazendo?"

"Milk, quais tarefas estão pendentes?"

"Milk, qual o progresso?"

"Milk, pause."

"Milk, continue."

"Milk, cancele essa tarefa."

"Milk, cancele a próxima."

"Milk, coloque isso como prioridade."

"Milk, faça isso depois."

"Milk, repita a última tarefa."

"Milk, limpe as tarefas concluídas."

---

# PROGRESSO

Claude deverá informar estados reais.

Exemplos:

```text
Analisando arquivos
Instalando dependências
Executando testes
Corrigindo erros
Gerando build
Finalizando
```

Não inventar porcentagem.

Quando não existir progresso mensurável:

usar estado textual.

---

# EVENT BUS

Criar sistema simples de eventos internos.

Eventos sugeridos:

```text
TASK_CREATED
TASK_STARTED
TASK_PROGRESS
TASK_COMPLETED
TASK_FAILED
TASK_CANCELLED

VOICE_LISTENING
VOICE_RECOGNIZED

CLAUDE_STARTED
CLAUDE_THINKING
CLAUDE_RESPONSE
CLAUDE_ERROR

MILK_IDLE
MILK_LISTENING
MILK_WORKING
MILK_SPEAKING
MILK_HAPPY
MILK_ERROR
```

Isso deve permitir que módulos se comuniquem sem forte acoplamento.

---

# ARQUITETURA SUGERIDA

Avaliar organização semelhante:

```text
milk/

  core/
    app
    events
    config

  avatar/
    controller
    animations
    states

  voice/
    wake_word
    speech_to_text
    text_to_speech
    audio_manager

  intelligence/
    intent_router
    claude_bridge
    context_manager

  tasks/
    manager
    queue
    worker
    models
    persistence

  memory/
    short_term
    long_term
    projects

  tools/
    windows
    files
    browser
    powershell

  skills/

  mcp/

  ui/
    command_center

  logs/

  config/

  tests/
```

Não aplicar cegamente essa estrutura se a arquitetura existente já for boa.

Adaptar.

---

# FASE 10 — FERRAMENTAS DO WINDOWS

Criar arquitetura de ferramentas que permita ao Claude/Milk:

* abrir aplicações;
* abrir pastas;
* abrir arquivos;
* criar arquivos;
* mover arquivos;
* copiar arquivos;
* renomear arquivos;
* pesquisar arquivos;
* executar PowerShell;
* abrir navegador;
* abrir URLs;
* copiar textos;
* criar projetos;
* iniciar aplicações;
* analisar processos;
* consultar status do computador;
* instalar dependências quando autorizado.

Cada ferramenta deve retornar resultado estruturado:

```text
SUCCESS
ERROR
DENIED
TIMEOUT
```

Nunca responder que algo foi realizado sem confirmação real.

---

# PERMISSION LAYER

Criar camada de segurança entre Claude e ações potencialmente perigosas.

Classificar operações:

```text
SAFE
SENSITIVE
DESTRUCTIVE
CRITICAL
```

SAFE:

* abrir programa;
* consultar arquivos;
* listar diretório.

SENSITIVE:

* instalar software;
* alterar configurações.

DESTRUCTIVE:

* excluir arquivos;
* sobrescrever dados;
* matar processos importantes.

CRITICAL:

* operações que possam danificar Windows;
* apagar diretórios de sistema;
* alterar boot;
* remover contas;
* formatar unidades.

Operações destrutivas ou críticas devem ser bloqueadas ou exigir autorização explícita.

---

# FASE 11 — MEMÓRIA

Criar três camadas.

## MEMÓRIA DE CURTO PRAZO

Conversa atual.

## MEMÓRIA PERSISTENTE

Preferências úteis.

## MEMÓRIA DE PROJETOS

Informações sobre projetos em desenvolvimento.

Exemplo:

"Milk, continue aquele projeto de ontem."

Milk deve conseguir localizar contexto relevante.

Não armazenar:

* senhas;
* tokens;
* credenciais;
* dados sensíveis desnecessários.

---

# HISTÓRICO DE TAREFAS

Registrar:

* pedido;
* resultado;
* arquivos modificados;
* duração;
* erros;
* status final.

Exemplo:

"Milk, o que fizemos ontem?"

Milk poderá consultar histórico.

---

# FASE 12 — CONTEXTO DE TELA

Criar arquitetura para captura de tela sob demanda.

Exemplos:

"Milk, olha esse erro."

"Milk, veja essa janela."

"Milk, por que isso não abriu?"

Fluxo:

```text
Comando
 ↓
Captura de tela
 ↓
Análise
 ↓
Claude
 ↓
Resposta
```

Evitar captura constante sem necessidade.

---

# OCR

Usar OCR apenas quando necessário.

Preferir análise visual direta quando possível.

---

# FASE 13 — BROWSER

Avaliar integração via navegador ou MCP.

Claude poderá futuramente:

* abrir páginas;
* navegar;
* pesquisar;
* preencher formulários;
* interagir com sistemas;
* analisar sites.

Manter sessão de navegador quando possível.

Nunca armazenar senhas em código.

---

# FASE 14 — MCP

Aproveitar MCP sempre que fizer sentido.

Claude poderá usar servidores MCP para:

* navegador;
* arquivos;
* GitHub;
* banco de dados;
* automação;
* ferramentas externas.

Evitar acoplamento excessivo.

---

# FASE 15 — SKILLS

Criar arquitetura modular.

Exemplo:

```text
skills/

browser/
windows/
coding/
files/
email/
calendar/
github/
research/
system/
```

Uma nova Skill deve poder ser adicionada sem modificar profundamente o núcleo.

---

# FASE 16 — COMMAND CENTER

Criar ou melhorar painel administrativo.

Mostrar:

* Milk;
* Claude;
* microfone;
* wake word;
* voz;
* tarefas;
* memória;
* Skills;
* MCP;
* ferramentas;
* logs;
* erros;
* configurações.

Painel não deve ser necessário para operação normal.

---

# TASK CENTER

Mostrar:

* tarefa atual;
* fila;
* status;
* prioridade;
* progresso;
* histórico;
* erros.

Permitir:

* pausar;
* continuar;
* cancelar;
* repetir;
* alterar prioridade;
* remover tarefa concluída.

---

# FASE 17 — RECOVERY

A Milk deve sobreviver a erros.

Se falhar:

* Whisper;
* microfone;
* TTS;
* Claude;
* navegador;
* MCP;
* Tool;
* subprocesso;

a aplicação principal não deve morrer.

Usar:

* tratamento de exceções;
* timeout;
* retry controlado;
* fallback;
* recuperação de processo.

---

# RECUPERAÇÃO DA FILA

Se Milk fechar durante uma tarefa:

ao iniciar novamente identificar tarefas RUNNING.

Alterar para:

```text
INTERRUPTED
```

Nunca retomar automaticamente operação destrutiva.

Avaliar segurança antes de continuar.

---

# FASE 18 — LOGS

Organizar logs.

Exemplo:

```text
logs/
  app/
  voice/
  claude/
  tasks/
  tools/
  mcp/
  errors/
```

Nunca registrar:

* senhas;
* tokens;
* API keys;
* credenciais.

---

# FASE 19 — CONFIGURAÇÕES

Centralizar configurações.

Usar:

```text
.env
config.json
config.yaml
```

ou solução existente adequada.

Nunca colocar credenciais diretamente no código.

Quando necessário usar:

* Windows Credential Manager;
* variáveis de ambiente;
* armazenamento seguro.

---

# FASE 20 — PERFORMANCE

Milk deverá permanecer ligada continuamente.

Priorizar:

* baixo consumo de CPU;
* baixo consumo de RAM;
* operações assíncronas;
* poucas threads;
* poucos subprocessos;
* evitar polling agressivo;
* evitar loops infinitos consumindo CPU;
* caching quando adequado;
* eventos em vez de polling.

Interface nunca deve congelar durante operações do Claude.

---

# FASE 21 — WINDOWS BACKGROUND

Evitar abrir janelas pretas de terminal.

Subprocessos devem preferencialmente executar ocultos.

Não comprometer capacidade de diagnóstico.

Logs devem continuar disponíveis.

---

# FASE 22 — STARTUP

Criar inicialização simples.

Idealmente:

```text
Milk.exe
```

Ou provisoriamente:

```text
Milk.ps1
Milk.bat
python milk.py
```

Preparar arquitetura para iniciar com Windows futuramente.

---

# FASE 23 — MILK DOCTOR

Criar diagnóstico do sistema.

Comando sugerido:

```text
milk doctor
```

Resultado esperado:

```text
MILK SYSTEM STATUS

Core: OK
Avatar: OK
Microphone: OK
Wake Word: OK
Speech Recognition: OK
TTS: OK
Claude: OK
Task Manager: OK
Memory: OK
Tools: OK
MCP: OK
Skills: OK
```

Quando falhar:

mostrar causa provável e correção.

---

# FASE 24 — TESTES

Adicionar testes reais.

Testar:

* inicialização;
* wake word;
* voz;
* intent router;
* fila;
* Claude bridge;
* memória;
* ferramentas;
* eventos;
* recovery;
* configurações.

Não considerar código pronto apenas por não apresentar erro de sintaxe.

Execute testes.

---

# FASE 25 — HEALTH CHECK

Criar monitor leve dos componentes principais.

Exemplo:

```text
Claude: ONLINE
Voice: ONLINE
TTS: ONLINE
Tasks: HEALTHY
Memory: HEALTHY
```

Não usar monitoramento agressivo.

---

# FASE 26 — NOTIFICAÇÕES

Milk deve reagir naturalmente.

Quando iniciar tarefa:

"Vou pedir para o Claude cuidar disso."

Quando terminar:

"Pronto. O Claude terminou."

Quando existir próxima tarefa:

"Terminei essa. Vou começar a próxima."

Quando tudo terminar:

"Terminei tudo."

Quando ocorrer erro:

"Claude encontrou um problema nessa tarefa."

---

# FASE 27 — PRESENÇA

Milk deve parecer presente sem atrapalhar.

Considerar:

* transparência;
* always-on-top opcional;
* click-through opcional;
* movimentação suave;
* posição salva;
* múltiplos monitores;
* escala de DPI do Windows;
* esconder durante tela cheia;
* modo silencioso.

---

# FASE 28 — MODO SILENCIOSO

Criar:

```text
NORMAL
SILENT
DO_NOT_DISTURB
```

No modo silencioso:

Milk pode mostrar indicação visual sem falar.

---

# FASE 29 — COMANDOS NATURAIS

Não exigir frases rígidas.

Exemplos equivalentes:

"Milk, abre o Chrome."

"Milk, abre o navegador."

"Milk, entra no Chrome."

O Intent Router deve mapear intenção.

---

# FASE 30 — CONVERSAÇÃO

Milk poderá conversar normalmente através do Claude.

Porém:

ações reais devem continuar passando pelo Task Manager e Permission Layer.

Separar claramente:

```text
CHAT
ACTION
TASK
```

---

# FASE 31 — CONTEXTO

Enviar ao Claude apenas contexto relevante.

Evitar enviar todo histórico indiscriminadamente.

Criar Context Manager.

Objetivo:

* reduzir tokens;
* aumentar precisão;
* evitar informações irrelevantes.

---

# FASE 32 — CLAUDE BRIDGE

Criar camada específica entre Milk e Claude.

Responsabilidades:

* enviar prompt;
* receber respostas;
* acompanhar processo;
* registrar erros;
* enviar eventos;
* interromper operação quando permitido;
* receber status.

Milk não deve depender diretamente da implementação do Claude em dezenas de módulos.

Tudo deve passar pelo Claude Bridge.

---

# FASE 33 — FALLBACK

Se Claude estiver indisponível:

Milk deve informar claramente.

Exemplo:

"Não consegui acessar o Claude agora."

Não inventar resposta de tarefa executada.

Operações locais simples poderão continuar funcionando.

---

# FASE 34 — PLUGINS FUTUROS

Preparar arquitetura para novos recursos como:

* Gmail;
* Google Calendar;
* GitHub;
* WhatsApp;
* Home Assistant;
* automação de navegador;
* banco de dados;
* APIs;
* outros modelos.

Não implementar tudo agora.

Apenas manter arquitetura extensível.

---

# FASE 35 — SEGURANÇA

Nunca permitir que conteúdo vindo de uma página web ou arquivo externo tome controle das regras da Milk.

Tratar conteúdo externo como dados.

Proteções contra:

* prompt injection;
* comandos maliciosos;
* scripts não confiáveis;
* downloads suspeitos;
* execução arbitrária.

---

# FASE 36 — OBSERVABILIDADE

Registrar:

* erros;
* tarefas;
* duração;
* estado dos componentes;
* uso aproximado de recursos.

Permitir diagnóstico fácil.

---

# DOCUMENTAÇÃO

Criar ou atualizar:

```text
README.md
ARCHITECTURE.md
MILK_ROADMAP.md
CHANGELOG.md
TROUBLESHOOTING.md
MILK_STATUS.md
```

---

# MILK_STATUS.md

Manter atualizado.

Estrutura:

```text
# MILK STATUS

## FUNCIONANDO

## PARCIAL

## EM DESENVOLVIMENTO

## NÃO IMPLEMENTADO

## BUGS CONHECIDOS

## PRÓXIMAS ETAPAS
```

---

# ARCHITECTURE.md

Documentar arquitetura real do projeto.

Não documentar arquitetura que não existe.

---

# CHANGELOG.md

Registrar alterações relevantes.

---

# TROUBLESHOOTING.md

Registrar problemas reais encontrados e soluções.

---

# README

Deve permitir que outra pessoa consiga entender:

* o que é Milk;
* como instalar;
* como iniciar;
* dependências;
* configuração;
* diagnóstico;
* arquitetura resumida.

---

# REGRAS DE DESENVOLVIMENTO

1. Não destruir código funcional.

2. Não apagar funcionalidade apenas para simplificar desenvolvimento.

3. Não reescrever projeto inteiro sem necessidade.

4. Corrigir antes de substituir.

5. Fazer backup antes de alteração estrutural.

6. Não deixar pseudocódigo quando puder implementar solução real.

7. Não criar funções falsas.

8. Não fingir testes.

9. Não fingir execução.

10. Não esconder erros.

11. Tratar exceções.

12. Criar logs úteis.

13. Evitar dependências desnecessárias.

14. Manter código modular.

15. Priorizar estabilidade.

16. Testar cada etapa.

17. Corrigir problemas encontrados durante testes.

18. Não parar no primeiro erro.

19. Continuar autonomamente enquanto houver uma solução segura.

20. Não alterar partes funcionais sem justificativa.

---

# CLASSIFICAÇÃO DE MELHORIAS

Durante a auditoria, classifique sugestões como:

## ESSENCIAL

Necessário para funcionamento correto.

## RECOMENDADO

Melhora significativa.

## EXPERIMENTAL

Interessante, mas não essencial.

Não instalar tecnologia apenas por ser nova.

Estabilidade vem primeiro.

---

# ORDEM DE EXECUÇÃO

Siga esta ordem:

```text
1. AUDITORIA
2. BACKUP
3. DIAGNÓSTICO
4. CORREÇÃO DE BUGS
5. TESTES DO SISTEMA ATUAL
6. ORGANIZAÇÃO DA ARQUITETURA
7. CLAUDE BRIDGE
8. INTENT ROUTER
9. TASK MANAGER
10. EVENT BUS
11. VOICE
12. AVATAR
13. MEMORY
14. TOOLS
15. PERMISSIONS
16. MCP / SKILLS
17. RECOVERY
18. PERFORMANCE
19. TESTES
20. DOCUMENTAÇÃO
```

Não tente reconstruir tudo simultaneamente.

---

# IMPORTANTE SOBRE ALTERAÇÕES

Quando encontrar código estranho:

primeiro descubra POR QUE ele existe.

Pode haver uma correção específica de Windows ou compatibilidade.

Não remova simplesmente porque parece desnecessário.

---

# COMPATIBILIDADE WINDOWS

Este projeto deverá funcionar corretamente no Windows.

Considerar:

* paths Windows;
* PowerShell;
* Unicode;
* UTF-8;
* subprocessos;
* permissões;
* DPI;
* múltiplos monitores;
* áudio;
* microfone;
* startup;
* processos em background.

---

# EXPERIÊNCIA DE USO

Quero uma experiência natural.

Não quero precisar abrir terminal para conversar com Milk.

Não quero precisar clicar em dez botões.

Ideal:

```text
Computador ligado
↓
Milk inicia
↓
Milk fica discretamente no desktop
↓
Usuário diz "Milk"
↓
Milk acorda
↓
Usuário fala normalmente
↓
Milk entende
↓
Claude trabalha
↓
Milk informa resultado
```

---

# COMPORTAMENTO ESPERADO DO CLAUDE DURANTE ESTE PROJETO

Não fique apenas me dizendo o que poderia ser feito.

Faça o trabalho no projeto.

Quando possível:

* abra arquivos;
* analise;
* corrija;
* implemente;
* execute;
* teste;
* documente.

Se uma abordagem falhar:

investigue e tente outra abordagem tecnicamente válida.

Não fique preso repetindo o mesmo erro.

---

# PRIMEIRA AÇÃO AGORA

Comece imediatamente.

1. Leia todos os arquivos relevantes do projeto.

2. Descubra a arquitetura atual.

3. Não altere nada antes de compreender o estado existente.

4. Faça um backup apropriado.

5. Gere o diagnóstico:

```text
FUNCIONANDO
PARCIAL
QUEBRADO
AUSENTE
RISCOS
```

6. Depois do diagnóstico, comece imediatamente as correções prioritárias.

7. Não pare apenas no planejamento.

8. Teste as alterações realizadas.

9. Atualize MILK_STATUS.md.

O objetivo não é produzir apenas um relatório.

O objetivo é deixar a Milk progressivamente funcional, estável e integrada ao Claude Code.
