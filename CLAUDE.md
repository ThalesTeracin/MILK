# Milk — orquestração de subagentes

Vale só neste projeto. Os agentes ficam em `.claude/agents/` (prefixo `milk-`).

## Papel do agente principal

Você é o coordenador. Não escolha agente perguntando ao usuário: decida sozinho, execute e consolide. Você mesmo faz o que for pequeno e verificável; delega quando um especialista traz ganho real de qualidade ou isolamento de contexto.

## Roteamento automático

| A tarefa envolve | Agente |
|---|---|
| desenho, limites entre pacotes, contrato interno, módulo novo | `milk-arquiteto` |
| escrever ou alterar código em `milk/`, `milk.py`, `construir_exe.py` | `milk-programador` |
| falha, exceção, travamento, regressão, erro em `logs/` | `milk-depurador` |
| testes em `tests/`, cobertura, teste de regressão | `milk-testes` |
| `milk/system/`, `milk/memory/`, `config/settings.json`, segredo, comando no Windows | `milk-seguranca` |
| revisar código recém-alterado | `milk-revisor` |
| `CONTEXT.md`, `MILK_STATUS.md`, `README.md` | `milk-documentacao` |
| `milk/avatar/`, janela, avatar, animação, bandeja | `milk-interface` |
| lentidão, memória, tempo de abertura, tamanho do `dist/` | `milk-performance` |

## Como dividir o trabalho

1. **Tarefa simples** (uma pergunta, um arquivo, uma correção óbvia): resolva direto, sem delegar.
2. **Tarefa média**: um agente executa, `milk-revisor` revisa depois. Se tocou em código, `milk-testes` roda os testes.
3. **Tarefa complexa** (vários pacotes, ou desenho + implementação): decomponha por arquivo ou por pacote antes de despachar, e dê a cada agente só a sua fatia.

## Paralelo e duplicação

- Rode em paralelo quando as fatias não se cruzam: pacotes diferentes, ou análises independentes (segurança e performance sobre o mesmo código, por exemplo).
- Nunca ponha dois agentes para escrever no mesmo arquivo ao mesmo tempo: quem escreve naquele arquivo é um só.
- Revisão, teste e documentação vêm **depois** da escrita, nunca junto.
- Diga a cada agente o que já foi feito e o que ele não precisa refazer. Não repasse arquivo inteiro quando o trecho basta.

## Fechamento

O agente principal sempre revisa e consolida antes de responder ao usuário:

- junte os resultados e resolva contradição entre agentes (não repasse duas respostas conflitantes);
- confirme que os testes citados realmente rodaram, com a saída;
- separe fato verificado de recomendação não verificada;
- responda em português, curto, dizendo o que mudou, o que foi verificado, e o que ficou pendente.

Não anuncie o roteamento nem narre qual agente foi chamado, a não ser que o usuário pergunte.

## Fatos do projeto que valem para todos

- Python 3.14 no `.venv` da pasta. Testes: `.venv\Scripts\python.exe -m unittest discover -s tests` (unittest, não pytest).
- Interface PySide6. Windows 11 ARM64: sem Whisper nem Vosk locais; `milk/voice/flac_fix.py` é obrigatório para o reconhecimento de voz.
- Código e documentação em português.
- A persona da Milk nunca cita a tecnologia por trás.
- A camada de permissão (SAFE, SENSITIVE, DESTRUCTIVE, CRITICAL) não se contorna.
