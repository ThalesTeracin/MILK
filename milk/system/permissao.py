# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Camada de permissão.

Entre o que foi pedido e o que acontece na máquina existe esta camada.
Ela classifica a ação e decide: pode, precisa de confirmação, ou não
acontece de jeito nenhum.

    SAFE         abrir programa, abrir pasta, listar, consultar
    SENSITIVE    criar e mover arquivo, PowerShell, instalar
    DESTRUCTIVE  apagar, sobrescrever, encerrar processo
    CRITICAL     mexer no Windows, no boot, em contas, formatar

SAFE acontece na hora. SENSITIVE e DESTRUCTIVE só depois de o usuário
confirmar em voz ou por escrito. CRITICAL **nunca acontece**, nem com
confirmação: a Milk explica e para por aí.

O caminho também pesa: apagar um arquivo em Downloads é DESTRUCTIVE;
o mesmo apagar dentro de C:\\Windows é CRITICAL.
"""

import os
import re


class Nivel:
    SEGURA = "SAFE"
    SENSIVEL = "SENSITIVE"
    DESTRUTIVA = "DESTRUCTIVE"
    CRITICA = "CRITICAL"

    ORDEM = (
        SEGURA,
        SENSIVEL,
        DESTRUTIVA,
        CRITICA,
    )

    @classmethod
    def maior(cls, um, outro):
        return max(
            um,
            outro,
            key=lambda nivel: cls.ORDEM.index(nivel)
        )


# Nível de cada ação, quando o alvo não agrava nada.
NIVEL_DA_ACAO = {
    "abrir_programa": Nivel.SEGURA,

    # Fechar pelo nome e o mesmo que clicar no X: o programa recebe
    # o pedido e ainda pergunta se voce quer salvar. Diferente de
    # "encerrar_processo", que mata o processo e perde o que nao
    # foi salvo — esse continua destrutivo, logo abaixo.
    "fechar_programa": Nivel.SEGURA,
    "abrir_pasta": Nivel.SEGURA,
    "abrir_arquivo": Nivel.SEGURA,
    "abrir_url": Nivel.SEGURA,
    "procurar_arquivo": Nivel.SEGURA,
    "ver_computador": Nivel.SEGURA,
    "listar_processos": Nivel.SEGURA,
    "copiar_texto": Nivel.SEGURA,

    "criar_arquivo": Nivel.SENSIVEL,
    "criar_pasta": Nivel.SENSIVEL,
    "mover_arquivo": Nivel.SENSIVEL,
    "copiar_arquivo": Nivel.SENSIVEL,
    "renomear_arquivo": Nivel.SENSIVEL,
    "powershell": Nivel.SENSIVEL,
    "instalar": Nivel.SENSIVEL,

    "apagar_arquivo": Nivel.DESTRUTIVA,
    "encerrar_processo": Nivel.DESTRUTIVA,
    "sobrescrever_arquivo": Nivel.DESTRUTIVA,

    "formatar": Nivel.CRITICA,
    "mexer_no_registro": Nivel.CRITICA,
    "alterar_boot": Nivel.CRITICA,
    "remover_conta": Nivel.CRITICA,
    "desligar": Nivel.CRITICA,
}


# Pastas em que o Windows mora. Escrever aqui é sempre crítico.
PASTAS_DO_SISTEMA = (
    r"c:\windows",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\programdata\microsoft\windows",
    r"c:\$recycle.bin",
    r"c:\system volume information",
    r"c:\boot",
    r"c:\recovery",
)


# Apelidos do PowerShell que apagam arquivo: ri e rm são Remove-Item,
# clc é Clear-Content. São curtos demais para procurar em qualquer lugar
# da linha — uma pasta chamada "ri" viraria comando —, então só contam no
# começo do comando ou logo depois de ; | &.
APELIDOS_QUE_APAGAM = r"(?:^|[;|&]\s*)\s*(?:ri|rm|clc)\b"

# Apelidos que matam processo: kill e spps são Stop-Process.
APELIDOS_QUE_MATAM = r"(?:^|[;|&]\s*)\s*(?:kill|spps)\b"

# Pastas do Windows escritas dentro de um comando.
ALVO_DO_SISTEMA = r"[^|]*\b(?:c:\\windows|c:\\program files|\$env:windir)"


# Comandos que não passam, mesmo com confirmação.
COMANDOS_CRITICOS = re.compile(
    r"\bformat(?:-volume)?\b|"
    r"\bdiskpart\b|"
    r"\bbcdedit\b|"
    r"\bbootrec\b|"
    r"\bmbr2gpt\b|"
    r"\bcipher\s+/w\b|"
    r"\bvssadmin\s+delete\b|"
    r"\bwbadmin\s+delete\b|"
    r"\bshutdown\b|"
    r"\brestart-computer\b|"
    r"\bstop-computer\b|"
    r"\bremove-item" + ALVO_DO_SISTEMA + r"|" +
    APELIDOS_QUE_APAGAM + ALVO_DO_SISTEMA + r"|"
    r"\brd\s+/s\b|\brmdir\s+/s\b|"
    r"\bdel\s+/[fsq]{1,3}\s+c:\\\\?\s*\*|"
    r"\bnet\s+user\s+\S+\s+/delete\b|"
    r"\bremove-localuser\b|"
    r"\bnew-localuser\b|"
    r"\breg\s+delete\s+hklm\b|"
    r"\bremove-itemproperty[^|]*hklm\b|"
    r"\bset-executionpolicy\s+unrestricted\b|"
    r"\bdisable-windowsoptionalfeature\b|"
    r"\bset-mppreference\b|"
    r"\badd-mppreference\b|"
    r"\btakeown\s+/f\s+c:\\windows\b|"
    r"\bicacls\s+c:\\windows\b",
    re.IGNORECASE
)


# PowerShell que baixa e executa da internet: não passa.
BAIXAR_E_EXECUTAR = re.compile(
    r"(?:invoke-webrequest|iwr|curl|wget|invoke-restmethod|irm)"
    r"[^|;]*\|\s*(?:iex|invoke-expression|powershell)",
    re.IGNORECASE
)


class Decisao:
    """O que a permissão respondeu sobre uma ação.

    pode        acontece agora
    confirmar   acontece se o usuário disser sim
    bloqueada   não acontece
    """

    def __init__(self, nivel, permitida, precisa_confirmar, motivo=""):
        self.nivel = nivel
        self.permitida = permitida
        self.precisa_confirmar = precisa_confirmar
        self.motivo = motivo

    @property
    def bloqueada(self):
        return not self.permitida

    def __repr__(self):
        estado = (
            "bloqueada"
            if self.bloqueada
            else ("confirmar" if self.precisa_confirmar else "pode")
        )

        return f"<Permissao {self.nivel} {estado}>"


def normalizar_caminho(caminho):
    try:
        return os.path.abspath(
            os.path.expandvars(
                os.path.expanduser(str(caminho))
            )
        ).lower()

    except Exception:
        return str(caminho or "").lower()


def e_do_sistema(caminho):
    """O caminho está dentro de uma pasta do Windows?"""

    if not caminho:
        return False

    inteiro = normalizar_caminho(caminho)

    for pasta in PASTAS_DO_SISTEMA:
        if inteiro == pasta or inteiro.startswith(pasta + os.sep):
            return True

    # A raiz do disco também não é lugar de mexer.
    if re.fullmatch(r"[a-z]:\\?", inteiro):
        return True

    return False


def nivel_do_comando(comando):
    """Classifica um comando de PowerShell pelo que ele faz."""

    texto = str(comando or "")

    if COMANDOS_CRITICOS.search(texto) or BAIXAR_E_EXECUTAR.search(texto):
        return Nivel.CRITICA

    if re.search(
        r"\bremove-item\b|\bdel\b|\berase\b|\brd\b|\brmdir\b|"
        r"\bstop-process\b|\btaskkill\b|\bclear-content\b|" +
        APELIDOS_QUE_APAGAM + r"|" + APELIDOS_QUE_MATAM,
        texto,
        re.IGNORECASE
    ):
        return Nivel.DESTRUTIVA

    return Nivel.SENSIVEL


def classificar(acao, alvo=None):
    """O nível daquela ação sobre aquele alvo."""

    nivel = NIVEL_DA_ACAO.get(acao, Nivel.SENSIVEL)

    if acao == "powershell":
        nivel = Nivel.maior(
            nivel,
            nivel_do_comando(alvo)
        )

    # Escrever dentro do Windows é sempre crítico. Ler não.
    if nivel != Nivel.SEGURA and e_do_sistema(alvo):
        nivel = Nivel.CRITICA

    return nivel


MOTIVO_CRITICA = (
    "Isso mexe em parte do Windows que pode quebrar o computador. "
    "Não vou fazer, nem se você confirmar."
)


def avaliar(acao, alvo=None):
    """A decisão da camada de permissão sobre a ação pedida."""

    nivel = classificar(acao, alvo)

    if nivel == Nivel.CRITICA:
        return Decisao(
            nivel,
            permitida=False,
            precisa_confirmar=False,
            motivo=MOTIVO_CRITICA,
        )

    if nivel == Nivel.SEGURA:
        return Decisao(
            nivel,
            permitida=True,
            precisa_confirmar=False,
        )

    return Decisao(
        nivel,
        permitida=True,
        precisa_confirmar=True,
        motivo=(
            "Isso apaga coisa do seu computador."
            if nivel == Nivel.DESTRUTIVA
            else "Isso mexe nos seus arquivos ou executa um comando."
        ),
    )
