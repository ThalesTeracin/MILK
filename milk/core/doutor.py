# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Milk Doctor (Fases 23 e 25).

Diagnóstico honesto de cada peça: o que está de pé, o que está torto e
o que está quebrado — com a causa provável e o que fazer.

Cada exame é independente e nenhum derruba o programa. Exame que não
consegue concluir vira ATENÇÃO, não vira silêncio: dizer "não consegui
verificar" é diferente de dizer "está tudo bem".

O exame do microfone é o único que mede o mundo real: ele grava meio
segundo e olha o nível. É o que mostra, sem opinião, se o microfone
está entregando som ou silêncio.

Roda de dois jeitos:

    python milk.py doutor          no terminal
    "Milk, você está bem?"         na conversa
"""

import os
import shutil
import subprocess

from pathlib import Path

from milk.core.config import (
    AVATAR_FILE,
    BARK_FILE,
    BASE_DIR,
    LOGS_DIR,
    MEMORIA_FILE,
    SETTINGS_FILE,
    TASKS_FILE,
)


OK = "OK"
ATENCAO = "ATENÇÃO"
FALHA = "FALHA"


SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Exame:
    """O resultado de um exame, com o que fazer quando não está bem."""

    def __init__(self, nome, estado, detalhe="", conserto=""):
        self.nome = nome
        self.estado = estado
        self.detalhe = detalhe
        self.conserto = conserto

    @property
    def ok(self):
        return self.estado == OK

    def linha(self):
        texto = f"{self.nome}: {self.estado}"

        if self.detalhe:
            texto += f" — {self.detalhe}"

        return texto

    def __repr__(self):
        return f"<{self.nome}: {self.estado}>"


# ============================================================
# EXAMES
# ============================================================

def exame_arquivos():
    """Os arquivos que a Milk precisa para existir."""

    faltando = []

    if not Path(AVATAR_FILE).is_file():
        faltando.append("a imagem do avatar")

    if not Path(SETTINGS_FILE).is_file():
        faltando.append("o config/settings.json")

    if faltando:
        return Exame(
            "Avatar e configuração",
            FALHA,
            "está faltando " + " e ".join(faltando),
            "Confira se algum arquivo foi movido da pasta do projeto.",
        )

    return Exame("Avatar e configuração", OK)


def exame_latido():
    if Path(BARK_FILE).is_file():
        return Exame("Latido", OK)

    return Exame(
        "Latido",
        ATENCAO,
        "não tem o arquivo do latido",
        f"Coloque um WAV em {BARK_FILE}.",
    )


def exame_microfone(segundos=0.5):
    """Grava meio segundo e mede. É o exame que não aceita opinião."""

    try:
        from milk.voice import dispositivos

    except Exception as erro:
        return Exame(
            "Microfone",
            FALHA,
            f"não consegui carregar o áudio ({erro})",
            "Reinstale as dependências no .venv.",
        )

    entrada = dispositivos.escolher()

    if entrada is None:
        return Exame(
            "Microfone",
            FALHA,
            "não achei nenhum microfone",
            "Confira se o microfone está conectado e habilitado.",
        )

    # O aparelho escolhido no settings.json pode simplesmente não estar
    # ligado agora — é o caso de fone Bluetooth, que some quando desliga.
    pedido = dispositivos.dispositivo_pedido()

    if pedido and not dispositivos.combinam(entrada, pedido):
        return Exame(
            "Microfone",
            ATENCAO,
            f"{pedido} não está conectado; usando {entrada.nome}",
            f"Ligue o {pedido} (se for Bluetooth, ele some da lista "
            "quando desliga) ou troque microfone.dispositivo no "
            "config/settings.json.",
        )

    pico, _ = dispositivos.medir(entrada, segundos)

    if pico < 0:
        return Exame(
            "Microfone",
            FALHA,
            f"não consegui gravar em {dispositivos.descrever(entrada)}",
            "Veja se outro programa está usando o microfone.",
        )

    if pico < dispositivos.PICO_MINIMO:
        # Procurar outro aparelho só faz sentido em automático. Se o
        # nome está fixo no settings.json, foi escolha de alguém, e meio
        # segundo de sala vazia não é motivo para mandar trocar — ainda
        # mais porque o mesmo microfone aparece com nomes diferentes em
        # cada API do Windows ("Driver de captura de som primário" é o
        # mesmo aparelho visto pelo DirectSound).
        if not pedido:
            outro = dispositivos.procurar_quem_ouve()

            if outro is not None and outro.indice != entrada.indice:
                return Exame(
                    "Microfone",
                    ATENCAO,
                    f"{entrada.nome} está mudo, mas {outro.nome} "
                    "está captando",
                    "Ponha o nome dele em microfone.dispositivo, no "
                    "config/settings.json.",
                )

        # Meio segundo de sala vazia também dá pico baixo. O exame não
        # tem como saber se o microfone está mudo ou se ninguém falou,
        # e chamar sala em silêncio de FALHA assusta à toa.
        if pico == 0:
            return Exame(
                "Microfone",
                FALHA,
                f"{entrada.nome} está entregando zero absoluto",
                "Abra as configurações de som do Windows, veja se a "
                "entrada não está muda, se o volume não está em zero e "
                "se o áudio não está indo para outro aparelho.",
            )

        return Exame(
            "Microfone",
            ATENCAO,
            f"{entrada.nome} não ouviu nada agora "
            f"(pico {pico} de 32767)",
            "Se a sala estava em silêncio, isso é normal: fale perto do "
            "microfone e rode o exame de novo. Se mesmo falando o pico "
            "não passar de 200, veja no som do Windows se a entrada não "
            "está muda ou com o volume em zero.",
        )

    return Exame(
        "Microfone",
        OK,
        f"{dispositivos.descrever(entrada)} captando (pico {pico})",
    )


def exame_reconhecimento():
    """A correção do FLAC precisa estar valendo nesta máquina ARM64."""

    try:
        from milk.voice.flac_fix import corrigir_flac_windows

        corrigir_flac_windows()

        # O remendo troca a função dentro de speech_recognition.audio,
        # que é a que o reconhecimento chama de verdade. O nome
        # reexportado no pacote continua sendo o original, e olhar para
        # ele daria um diagnóstico errado.
        import speech_recognition.audio as sr_audio

        caminho = sr_audio.get_flac_converter()

    except Exception as erro:
        return Exame(
            "Reconhecimento de voz",
            FALHA,
            f"não carregou ({erro})",
            "Reinstale o speech_recognition no .venv.",
        )

    if not caminho:
        return Exame(
            "Reconhecimento de voz",
            FALHA,
            "o conversor FLAC não foi encontrado",
            "É a correção de Windows ARM64 em milk/voice/flac_fix.py.",
        )

    return Exame(
        "Reconhecimento de voz",
        OK,
        f"usando {Path(str(caminho)).name}",
    )


def exame_voz():
    """Sintetiza uma palavra de verdade e vê se saiu áudio.

    Só conferir o import não provava nada: o que costuma falhar é a
    síntese em si, e num executável empacotado ela é justamente uma das
    peças que podem ter ficado de fora."""

    try:
        import asyncio
        import edge_tts

    except Exception as erro:
        return Exame(
            "Voz",
            FALHA,
            f"o edge_tts não carregou ({erro})",
            "Reinstale o edge_tts no .venv.",
        )

    import tempfile

    from milk.core.config import (
        VOICE_NAME,
        VOICE_RATE,
        VOICE_PITCH,
    )

    destino = Path(tempfile.gettempdir()) / "milk_exame_voz.mp3"

    async def gerar():
        await edge_tts.Communicate(
            text="Au au",
            voice=VOICE_NAME,
            rate=VOICE_RATE,
            pitch=VOICE_PITCH,
        ).save(str(destino))

    try:
        asyncio.run(
            gerar()
        )

        tamanho = destino.stat().st_size

    except Exception as erro:
        return Exame(
            "Voz",
            ATENCAO,
            f"não consegui sintetizar agora ({erro})",
            "A voz é um serviço on-line: confira a internet. "
            "Sem ela a Milk continua respondendo por escrito.",
        )

    finally:
        try:
            destino.unlink()

        except OSError:
            pass

    if tamanho < 1000:
        return Exame(
            "Voz",
            FALHA,
            f"o áudio saiu vazio ({tamanho} bytes)",
            "Confira a internet e o nome da voz em milk/core/config.py.",
        )

    return Exame(
        "Voz",
        OK,
        f"{VOICE_NAME} sintetizando ({tamanho} bytes de prova)",
    )


def exame_claude(prazo=20):
    """O Claude Code responde na linha de comando?"""

    if not shutil.which("claude"):
        return Exame(
            "Claude",
            FALHA,
            "o comando claude não está no PATH",
            "Instale o Claude Code e abra a Milk de novo.",
        )

    try:
        processo = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=prazo,
            creationflags=SEM_JANELA,
        )

    except subprocess.TimeoutExpired:
        return Exame(
            "Claude",
            ATENCAO,
            "demorou demais para responder",
            "Pode ser internet lenta. Tente de novo em um minuto.",
        )

    except Exception as erro:
        return Exame(
            "Claude",
            FALHA,
            f"não consegui chamar ({erro})",
            "Confira a instalação do Claude Code.",
        )

    if processo.returncode != 0:
        return Exame(
            "Claude",
            FALHA,
            "respondeu com erro",
            (processo.stderr or "").strip()[:120]
            or "Rode 'claude --version' no terminal para ver.",
        )

    versao = (processo.stdout or "").strip().splitlines()

    return Exame(
        "Claude",
        OK,
        versao[0] if versao else "",
    )


def exame_configuracao_do_claude():
    """O settings do projeto é o que desliga o plugin caveman aqui.

    `CLAUDE_SETTINGS` não é caminho: é o próprio JSON que a Milk passa
    em `--settings`. O arquivo que importa neste exame é o do projeto."""

    arquivo = Path(BASE_DIR) / ".claude" / "settings.json"

    if arquivo.is_file():
        return Exame("Estilo de fala", OK)

    return Exame(
        "Estilo de fala",
        ATENCAO,
        "não achei o .claude/settings.json do projeto",
        "Sem ele, uma sessão aberta nesta pasta pode deixar a fala "
        "dela telegráfica.",
    )


def exame_tarefas():
    from milk.tasks.gerente import gerente

    try:
        fila = gerente()

    except Exception as erro:
        return Exame(
            "Tarefas",
            FALHA,
            f"a fila não abriu ({erro})",
            f"Veja se {TASKS_FILE} não está corrompido.",
        )

    pendentes = len(fila.pendentes())
    rodando = fila.em_andamento()

    detalhe = f"{pendentes} na fila"

    if rodando:
        detalhe += f", fazendo: {rodando.descricao}"

    return Exame("Tarefas", OK, detalhe)


def exame_memoria():
    from milk.memory.memoria import memoria

    try:
        lembranca = memoria()

    except Exception as erro:
        return Exame(
            "Memória",
            FALHA,
            f"não abriu ({erro})",
            f"Veja se {MEMORIA_FILE} não está corrompido.",
        )

    return Exame(
        "Memória",
        OK,
        f"{len(lembranca.fatos)} anotações, "
        f"{len(lembranca.projetos)} projetos",
    )


def exame_ferramentas():
    from milk.core.settings import obter

    try:
        obter("http", "timeout_segundos", 10)

    except Exception as erro:
        return Exame(
            "Ferramentas",
            ATENCAO,
            f"as configurações não leram ({erro})",
            "A Milk usa os padrões internos enquanto isso.",
        )

    return Exame("Ferramentas", OK)


def exame_internet(prazo=6):
    """Sem internet, voz e reconhecimento não funcionam."""

    import socket

    try:
        socket.setdefaulttimeout(prazo)

        with socket.create_connection(("1.1.1.1", 53), timeout=prazo):
            pass

    except OSError:
        return Exame(
            "Internet",
            FALHA,
            "não consegui alcançar a rede",
            "Sem internet a Milk não fala nem entende voz.",
        )

    return Exame("Internet", OK)


def exame_disco():
    try:
        uso = shutil.disk_usage(
            os.environ.get("SystemDrive", "C:") + "\\"
        )

    except OSError:
        return Exame("Disco", ATENCAO, "não consegui medir o disco")

    livre = uso.free / (1024 ** 3)

    if livre < 1:
        return Exame(
            "Disco",
            FALHA,
            f"só {livre:.1f} giga livre",
            "Libere espaço: sem disco a Milk não grava nem a fila.",
        )

    if livre < 5:
        return Exame(
            "Disco",
            ATENCAO,
            f"{livre:.1f} gigas livres",
            "Está apertado.",
        )

    return Exame("Disco", OK, f"{livre:.0f} gigas livres")


def exame_logs():
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        teste = LOGS_DIR / ".escrita"

        teste.write_text("ok", encoding="utf-8")
        teste.unlink()

    except OSError as erro:
        return Exame(
            "Logs",
            ATENCAO,
            f"não consigo escrever em {LOGS_DIR} ({erro})",
            "Sem log, um problema não deixa rastro.",
        )

    return Exame("Logs", OK)


# Ordem em que aparecem no relatório.
EXAMES = (
    exame_arquivos,
    exame_claude,
    exame_configuracao_do_claude,
    exame_internet,
    exame_microfone,
    exame_reconhecimento,
    exame_voz,
    exame_latido,
    exame_tarefas,
    exame_memoria,
    exame_ferramentas,
    exame_disco,
    exame_logs,
)


def examinar(exames=EXAMES):
    """Roda todos os exames. Um que estoure vira FALHA, não derruba."""

    resultados = []

    for exame in exames:
        try:
            resultados.append(exame())

        except Exception as erro:
            resultados.append(
                Exame(
                    getattr(exame, "__name__", "exame"),
                    FALHA,
                    f"o próprio exame falhou ({erro})",
                )
            )

    return resultados


def relatorio(resultados=None):
    """O texto do diagnóstico, do jeito que a especificação pede."""

    resultados = resultados if resultados is not None else examinar()

    linhas = ["MILK SYSTEM STATUS", ""]

    for exame in resultados:
        linhas.append(exame.linha())

    problemas = [
        exame
        for exame in resultados
        if not exame.ok and exame.conserto
    ]

    if problemas:
        linhas.append("")
        linhas.append("O QUE FAZER:")

        for exame in problemas:
            linhas.append(f"- {exame.nome}: {exame.conserto}")

    return "\n".join(linhas)


def resumo_falado(resultados=None):
    """A versão curta, para ela dizer em voz alta."""

    resultados = resultados if resultados is not None else examinar()

    ruins = [
        exame
        for exame in resultados
        if exame.estado == FALHA
    ]

    atencao = [
        exame
        for exame in resultados
        if exame.estado == ATENCAO
    ]

    if not ruins and not atencao:
        return f"Estou bem: {len(resultados)} verificações, tudo certo."

    partes = []

    if ruins:
        partes.append(
            "Com problema: "
            + "; ".join(
                f"{exame.nome} ({exame.detalhe})" if exame.detalhe
                else exame.nome
                for exame in ruins
            )
        )

    if atencao:
        partes.append(
            "Para olhar: "
            + "; ".join(exame.nome for exame in atencao)
        )

    conserto = next(
        (exame.conserto for exame in ruins if exame.conserto),
        "",
    )

    frase = ". ".join(partes) + "."

    if conserto:
        frase += f" {conserto}"

    return frase
