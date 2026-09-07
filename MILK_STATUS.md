# MILK STATUS

Última atualização: 05/09/2026 (memória, ferramentas do Windows, escuta contínua, modos, Milk Doctor)
Especificação de referência: `MILK MASTER PROMPT.md`

Ambiente verificado: Windows 11 ARM64, Python 3.14.7 em `.venv`, Claude Code CLI 2.1.251.

---

## FUNCIONANDO

Verificado por execução, não por leitura de código.

- **Avatar na área de trabalho** — `MilkMascot`, janela sem borda, fundo transparente, sempre no topo, arrastável, posicionada no canto inferior direito. Ícone na bandeja do sistema com menu.
- **Janela de conversa** — `ChatBubble`, entrada por texto, histórico das últimas 8 mensagens enviado como contexto.
- **Ponte com o Claude Code** — `ClaudeWorker` executa `claude -p <prompt>` em subprocesso oculto (`CREATE_NO_WINDOW`), timeout de 600 s. Testado: retorno correto.
- **Gravação de microfone** — `sounddevice` grava 7 segundos do dispositivo padrão; conversão para 16 kHz mono via ffmpeg embutido (`imageio_ffmpeg`). O caminho inteiro roda, mas em 05/09/2026 o aparelho estava entregando silêncio (pico 15 em 32767). Ver QUEBRADO.
- **Reconhecimento de voz** — Google Web Speech em pt-BR. **Corrigido nesta sessão** (ver QUEBRADO). Testado sobre `milk_microfone.wav`: transcreveu "Milk Quem é você".
- **Síntese de voz** — `edge_tts` com a voz `pt-BR-FranciscaNeural`, reprodução por `QMediaPlayer`. Testado: áudio gerado.
- **Fila de fala** — falas nunca se sobrepõem, respeitam a ordem, e "Milk, pare." interrompe e limpa a fila. Testado.
- **Identificação de quem fala** — `milk/core/pessoa.py`. Ela pergunta só quando não sabe, guarda o nome em `milk_pessoa.json` e troca de pessoa quando alguém se apresenta no meio da conversa. Com o dono ela é direta; com visita, cordial. Testado.
- **Persona fechada** — ela não cita a tecnologia por trás e não se declara humana. Testado com pergunta direta.
- **Estilo de fala** — o plugin caveman está desligado neste projeto (`.claude/settings.json`) e também na chamada da Milk (`--settings`). Fora da pasta ele continua ativo. Verificado.
- **Progresso do trabalho** — o `ClaudeWorker` lê o processo em fluxo (`--output-format stream-json`) e mostra a ferramenta em uso e o tempo decorrido na barra de status. Testado ao vivo.
- **Ferramentas externas** — oito APIs públicas em `milk/tools/`, cada uma no seu módulo, todas por `urllib` (nenhuma dependência nova): Open-Meteo (clima), ViaCEP e BrasilAPI (CEP), Frankfurter (moedas), Wikipédia, GitHub, Nager.Date (feriados) e Nominatim (lugares). Testadas ao vivo, uma a uma, incluindo os casos de falha.
- **Roteador de intenção** — `milk/intelligence/roteador.py` decide entre ferramenta e Claude. É conservador de propósito: na dúvida, o pedido vai para o Claude. Testado com 59 frases, positivas e negativas.
- **Horário e calendário** — `milk/tools/relogio.py` responde hora, data, dia da semana, amanhã, ontem, mês, ano e contagem de dias até uma data, lendo o relógio da máquina. Sem rede, sem thread e sem Claude. Coberto por 35 testes.
- **Memória em três camadas (Fase 11)** — `milk/memory/`. Conversa recente, fatos e preferências, e projetos, tudo em disco. Volta ao abrir. Senha, token e chave são recusados. O que ela sabe entra no prompt em bloco curto.
- **Ferramentas do Windows (Fase 10)** — `milk/system/acoes.py`. Abre programa, pasta, arquivo e site; procura arquivo; conta memória, disco e bateria; lista processos; cria, copia, move e apaga arquivo; roda PowerShell. Resultado sempre estruturado (SUCCESS/ERROR/DENIED/TIMEOUT).
- **Camada de permissão** — `milk/system/permissao.py`. SAFE roda na hora; SENSITIVE e DESTRUCTIVE só depois de um "sim" que caduca em dois minutos; CRITICAL não acontece nem confirmado. O caminho agrava: apagar em Downloads é destrutivo, dentro de C:\\Windows é crítico.
- **Escuta contínua com wake word (Fases 4 e 5)** — `milk/voice/escuta.py` e `milk/voice/vad.py`. Detecta início e fim de fala por energia, transcreve só o trecho falado e atende quando a frase começa com "Milk". Ligada pelo menu. **Testada com áudio gerado; nunca ouvida de verdade, porque o microfone desta máquina está mudo.**
- **Modos (Fase 28)** — normal, silencioso e não perturbe, guardados em disco.
- **Milk Doctor (Fases 23 e 25)** — `python milk.py doutor` ou "Milk, você está bem?". Treze exames com causa e conserto; o do microfone mede o nível de verdade.
- **Logs (Fase 18)** — `logs/` por área, com rotação. Token e senha viram *** antes de serem escritos.
- **Início com o Windows (Fase 22)** — pelo menu do avatar, na chave Run do usuário. `Milk.bat` abre sem terminal.
- **Posição salva (Fase 27)** — ela volta para onde estava, se ainda couber na tela.
- **Fila de tarefas (Fase 9)** — `milk/tasks/`. Pedido de trabalho vira tarefa com id, status, prioridade, progresso e resultado, gravada em `milk_tarefas.json` por escrita atômica. Segundo pedido durante um trabalho entra na fila em vez de ser recusado, e começa sozinho quando o anterior termina. Prioridade sai do jeito de pedir ("isso é urgente"). Controle por voz: o que está fazendo, pendentes, progresso, pausar, continuar, cancelar, priorizar, adiar, repetir e limpar concluídas.
- **Barramento de eventos (Fase 9)** — `milk/core/eventos.py`, com os nomes da especificação. Já é usado de verdade: cancelar uma tarefa chega na conversa por evento e encerra o processo do Claude, sem que gerente e janela se conheçam.
- **Latido** — `assets/sounds/latido.wav` é um trecho de 0,64 s de um latido real (Orange Free Sounds, CC BY-NC 4.0). Verificado tocando pelo `QSoundEffect`.
- **Ferramenta fora da interface** — `FerramentaWorker` (QThread) roda a chamada HTTP sem travar a janela. Verificado: a interface continuou respondendo durante a consulta.

---

## PARCIAL

- **Estados do avatar** — existem 4 (`parada`, `ouvindo`, `pensando`, `falando`) contra os 10 da Fase 3, e o que muda é o texto do rótulo. O corpo tem animação procedural (quique, inclinação, respiro e espelhamento), mas não tem arte de caminhada: o PNG é a cachorrinha sentada e de frente.
- **Escuta contínua** — o código está pronto e testado com áudio gerado, mas nunca foi ouvida de verdade, porque o microfone desta máquina está entregando silêncio.
- **Contexto de conversa** — as últimas falas ficam em `milk_conversa.json` e voltam ao abrir. O que vai para o Claude continua sendo um recorte curto, de propósito.

---

## QUEBRADO

- **[RESOLVIDO em 05/09/2026] Ela ouvia e não atendia.** O nome só valia no começo da fala, então "Olá milk", "fecha o navegador para mim milk" e "jamilk boa noite" eram descartados — todas frases reais do log das 20h. Agora o nome vale em qualquer lugar da frase (`NOME_FORTE`, em `milk/voice/escuta.py`), ela late no instante em que é chamada, e chamar só "Milk" ganhou resposta falada (`so_o_nome`). A escuta contínua sobe junto com ela (`microfone.escuta_automatica`), e o ouvido fecha enquanto ela late e fala, para a própria voz dela não virar pedido.

- **[RESOLVIDO em 05/09/2026] Ela gravou "Fechar" como nome do dono.** A palavra escapou de "fechar navegador" enquanto ela esperava a resposta de "com quem eu estou falando?". `milk_pessoa.json` voltou para `Thales` e `PALAVRAS_NAO_NOME` passou a recusar palavra de comando.

- **[RESOLVIDO em 05/09/2026] O microfone não captava.** O padrão do Windows continua mudo; o `Grupo de Microfones (Qualcomm...)` capta e está fixado no `config/settings.json`. Medido pelo Milk Doctor.

- **[CONTORNADO — não é software] O microfone padrão do Windows é mudo.** Medido em 05/09/2026: gravação de 7 s do padrão com pico de 15 em 32767 e RMS 3,3. Permissão do Windows liberada (HKCU e HKLM = Allow) e os dois endpoints OK. Provável causa: entrada muda no mixer ou volume zerado. A Milk não depende mais disso: `milk/voice/dispositivos.py` escolhe o aparelho que está captando, e o nome dele está fixado no `config/settings.json`. Arrumar o padrão do Windows continua sendo assunto da máquina, não do código.

- **[CORRIGIDO] Reconhecimento de voz nunca funcionou nesta máquina.**
  Causa raiz: `speech_recognition` só procura o binário FLAC embutido quando `platform.machine()` é `x86`/`AMD64`. Esta máquina reporta `ARM64`, então a biblioteca levantava
  `OSError: FLAC conversion utility not available` em toda transcrição.
  O `flac-win32.exe` embutido roda normalmente por emulação x86 (verificado: `flac 1.3.2`).
  Correção: `corrigir_flac_windows()` em `milk.py` aponta o caminho do binário apenas quando a detecção original falha.

- **[CORRIGIDO] Falas perdidas.** `falar()` descartava o texto em silêncio quando já havia uma fala em andamento. Substituído por fila.

- **[CORRIGIDO] Respostas cortadas no chat.** As mensagens eram inseridas com `QTextEdit.append()` sem escape, então qualquer `<` em código era interpretado como HTML e o trecho sumia da tela. Agora passam por `formatar_chat()` com `html.escape()`.

- **[CORRIGIDO] Silêncio quando ocupada.** Pedidos feitos durante um trabalho do Claude, ou cliques no microfone durante a gravação, retornavam sem nenhum aviso. Agora informam o motivo na barra de status.

---

## AUSENTE

Nada disso existe hoje no projeto.

- Contexto de tela e OCR (Fase 12).
- Browser controlado pela Milk (Fase 13) — ela abre sites, mas não navega sozinha.
- MCP (Fase 14) e Skills como pastas próprias (Fase 15). O que existe hoje são as rotas em `milk/intelligence/`, que resolvem o mesmo problema com menos máquina.
- Command Center e Task Center (Fase 16).
- Configuração centralizada (Fase 19) — parcial. `config/settings.json` já guarda as configurações das ferramentas (lido por `milk/core/settings.py`), mas `BASE_DIR` continua fixo em `C:\AssistenteAvatar` e o resto das constantes segue em `milk/core/config.py`.
- Testes automatizados no repositório (Fase 24) — **parcial**. `tests/` tem 307 testes em `unittest` (chat, passeio, animação, quadros, relógio, tarefas, memória, sistema, escuta, doutor). As 8 APIs externas ainda não têm teste dentro do projeto.
- Documentação: `ARCHITECTURE.md`, `MILK_ROADMAP.md`, `CHANGELOG.md`, `TROUBLESHOOTING.md`. O `README.md` foi escrito.

---

## RISCOS

- **[RESOLVIDO] Arquitetura em arquivo único.** O código foi separado em `milk/core`, `milk/voice`, `milk/avatar` e `milk/intelligence`. `milk.py` passou a ser só o ponto de entrada. O comportamento não mudou.
- **Pacote `milk/` e arquivo `milk.py` na mesma pasta.** Funciona porque o pacote tem prioridade na importação e `milk.py` só roda como `__main__`, mas confunde quem lê e quebraria um `import milk` feito de outra pasta.
- **Windows ARM64 limita o reconhecimento de voz local.** A especificação prefere solução local (Fase 5), mas as opções usuais dependem de rodas que não existem para esta plataforma: `torch` (Whisper original), `ctranslate2` (faster-whisper) e `vosk`. Antes de prometer transcrição local é preciso avaliar alternativas compatíveis, como a API de fala do próprio Windows.
- **Voz e transcrição dependem de internet.** `edge_tts` e o reconhecimento do Google são serviços online. Sem rede, a Milk fica muda e surda, e hoje não há aviso claro disso.
- **Áudio do microfone é gravado em disco sem limpeza.** `milk_microfone.wav` e `milk_microfone_convertido.wav` permanecem na pasta depois de cada uso.
- **Sem camada de permissão.** O pedido roda com as ferramentas padrão na pasta do projeto. Não existe a classificação `SAFE` / `SENSITIVE` / `DESTRUCTIVE` / `CRITICAL` pedida pela especificação.
- **Sem tratamento de reinício.** Se a Milk for fechada durante um pedido, o trabalho é perdido sem registro.
- **Falso positivo do roteador.** Ele é conservador e tem lista de veto, mas nenhuma regra escrita à mão cobre toda frase possível. Se ele interceptar algo que era conversa, a Milk responde com dado de API em vez de raciocínio.
- **As ferramentas dependem de internet.** Cada uma falha com frase amigável e não derruba a Milk, mas sem rede nenhuma delas responde.
- **Sem repique automático para o Claude.** Quando a ferramenta falha, a Milk avisa e para ali; ela não refaz o pedido pelo Claude sozinha.
- **ViaCEP oscila.** Medido: 0,5 s no caso normal, com uma resposta de 10,5 s observada. A reserva da BrasilAPI só entra quando há erro, não quando há lentidão.
- **Arquivos antigos soltos na raiz.** `milk_backup.py`, `milk_backup_homenagem.py`, `milk_v1_funcionando.py` e `milk_v2_backup.py` convivem com o arquivo atual sem indicação de qual é o vigente.

---

## PRÓXIMAS ETAPAS

Na ordem de execução definida pela especificação, continuando do item 5.

1. Testar a captura de voz de ponta a ponta com o microfone real, agora que a transcrição foi corrigida. Pendente com o usuário.
2. [CONCLUÍDO] Extrair `milk.py` para módulos (`core`, `voice`, `avatar`, `intelligence`), preservando o comportamento atual.
3. [CONCLUÍDO] Isolar a chamada em um bridge com eventos de progresso e com a montagem do prompt fora da janela de conversa.
4. [CONCLUÍDO — primeira parte] Roteador de intenção para as oito APIs externas. Falta a parte local da Fase 8: horas, calendário e ferramentas do Windows.
5. Criar o Task Manager com fila persistente.
6. Implementar a wake word "Milk".

---

## BACKUPS

- `backups/milk_20260830_144224_pre_masterprompt.py` — estado imediatamente anterior às correções de bugs.
- `backups/milk_20260830_181736_pre_modularizacao.py` — arquivo único completo, antes da separação em módulos.
- `backups/chat_20260831_200233_pre_tools.py` e `backups/config_20260831_200233_pre_tools.py` — estado anterior à camada de ferramentas.
- `milk_v2_backup.py`, `milk_v1_funcionando.py` — versões anteriores mantidas pelo autor.
