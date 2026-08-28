# Dependências nativas e o Smart App Control

## O problema

Em 2026-08-28 a geração de documentos Word e PowerPoint parou de funcionar
nesta máquina. O erro era sempre o mesmo:

```
ImportError: DLL load failed while importing _elementpath:
Uma política de Controle de Aplicativo bloqueou este arquivo.
```

A causa é o **Smart App Control** do Windows, ligado nesta máquina:

```powershell
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy' `
  -Name VerifiedAndReputablePolicyState
# 1  (0 = desligado, 1 = ligado, 2 = avaliação)
```

Ele bloqueia binários de **baixa reputação**. Uma wheel Python com extensão
nativa (`.pyd`) recém-publicada, ou pouco baixada, ainda não acumulou
reputação no serviço da Microsoft e é barrada. `python-docx` e `python-pptx`
dependem de `lxml`, então o bloqueio de um `.pyd` do lxml derrubava o import
dos dois pacotes inteiros.

## O que foi testado

A primeira hipótese — "é a versão do Python" ou "é a arquitetura ARM64" —
foi descartada por medição. Mesma versão de lxml (6.1.2) em três ambientes:

| Ambiente | lxml | numpy | pydantic_core |
|---|---|---|---|
| Python 3.14 AMD64 (o da MILK) | bloqueado | OK | OK |
| Python 3.12 ARM64 nativo | OK | **bloqueado** | OK |
| Python 3.11 x86_64 | OK | OK | **bloqueado** |

Nenhum ambiente passa em tudo, e cada instalação nova bloqueia um binário
diferente. Não é versão nem arquitetura: é **reputação de cada arquivo**.

Conclusão prática: **migrar de interpretador não resolve, e piora.** O venv
3.12 ARM64 quebrou `numpy`, e com ele `voice.listener`, que é núcleo — troca
de um problema pequeno por um grande. O ambiente `C:\Python314` atual é o
mais confiável da máquina porque seus binários já estão "curtidos".

## A decisão

Ficar no Python 3.14 e **remover a dependência nativa onde ela é evitável**.
Código Python puro não tem `.pyd`, logo não há o que a política bloquear.

- **DOCX** — `src/documents/docx_agent.py` foi reescrito com `zipfile` +
  `xml` da stdlib. Um `.docx` é um ZIP com cinco partes XML, e o subconjunto
  que a MILK usa (título, dois níveis de heading, parágrafos) cabe nisso.
  `python-docx` saiu do `requirements.txt`. Coberto por
  `tests/test_docx_agent.py`, que lê o pacote gerado de volta e confere o XML.
- **PPTX** — continua usando `python-pptx`. Gerar OOXML de apresentação à mão
  exige slideMaster, slideLayouts, tema e relacionamentos por slide; um erro
  em qualquer um faz o PowerPoint recusar o arquivo. Não compensa enquanto
  DOCX, PDF e XLSX cobrem o uso real. O que mudou é que o import virou tardio
  (`pptx_agent._carregar()`), então a indisponibilidade fica contida nesse
  agente: `DocumentManager` captura o `ImportError` e responde sugerindo DOCX
  ou PDF, em vez de derrubar o import de todos os formatos.
- **PDF e XLSX** — `reportlab` e `openpyxl` nunca dependeram de lxml e
  seguem funcionando.

## Regra para a Fase 32 (instalador)

O `requirements.txt` deve conter apenas o que a MILK precisa para subir.
Qualquer pacote com extensão nativa que não seja essencial vai para
`requirements-optional.txt`, e o código que o usa precisa degradar com
mensagem tratada.

Isso não é específico desta máquina: **qualquer usuário com Smart App Control
ligado bate na mesma parede**, e o instalador não pode depender de um binário
que a política do sistema pode barrar.

## O que não fazer

Desligar o Smart App Control resolveria, mas ele **só pode ser religado
reinstalando o Windows do zero**. Não vale trocar uma proteção permanente do
sistema por uma dependência de um formato de arquivo.

## Como verificar o estado atual

```
cd C:\JARVIS
python .\Testar_Sistema.py
```

O bloco "2b. Dependencias opcionais" mostra o que está indisponível. Pacote
opcional bloqueado sai como aviso e **não** reprova a verificação.
