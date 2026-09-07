# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Comandos que mexem no Windows.

"Abre o Chrome", "abre a pasta de downloads", "cadê o arquivo relatório",
"como está o computador", "roda esse comando no PowerShell".

Como a especificação pede na Fase 29, a mesma intenção pode ser dita de
várias formas: abre, abra, abrir, inicia, executa, entra no. O que muda
é a palavra, não o que ela quer.

Conservador do mesmo jeito que o resto do roteador: **só intercepta
quando reconhece o alvo**. "Abra um arquivo novo e escreva um script"
não vira ação de sistema — não existe programa com esse nome, então o
pedido segue para o Claude, que sabe programar.

Ação sensível ou destrutiva não acontece aqui: ela vira uma pergunta, e
só acontece depois do "sim". Quem guarda o meio do caminho é
`milk/system/confirmacao.py`.
"""

import os
import re

from pathlib import Path

from milk.tools import certo, falhou
from milk.system import acoes
from milk.system.confirmacao import confirmacao
from milk.system.permissao import avaliar


# ============================================================
# DO RESULTADO DO SISTEMA PARA A FALA DELA
# ============================================================

def falar(resultado):
    """Traduz o resultado estruturado para o que aparece na conversa."""

    if resultado.ok:
        return certo(resultado.texto, resultado.dados)

    if resultado.codigo == acoes.Codigo.NEGADA:
        return falhou(resultado.texto)

    if resultado.codigo == acoes.Codigo.TEMPO:
        return falhou(resultado.texto)

    return falhou(resultado.texto)


def com_permissao(acao, alvo, descricao, executar):
    """Roda agora se for segura; senão, pergunta antes.

    Crítica não acontece de jeito nenhum, e a Milk explica por quê."""

    permissao = avaliar(acao, alvo)

    if permissao.bloqueada:
        return falhou(permissao.motivo)

    if permissao.precisa_confirmar:
        pergunta = confirmacao().pedir(
            descricao,
            lambda: falar(executar()),
            permissao.nivel,
            permissao.motivo,
        )

        return certo(pergunta)

    return falar(executar())


# ============================================================
# PASTAS COM NOME DE GENTE
# ============================================================

PASTAS_CONHECIDAS = {
    "downloads": "~/Downloads",
    "download": "~/Downloads",
    "documentos": "~/Documents",
    "documento": "~/Documents",
    "imagens": "~/Pictures",
    "fotos": "~/Pictures",
    "área de trabalho": "~/Desktop",
    "area de trabalho": "~/Desktop",
    "desktop": "~/Desktop",
    "músicas": "~/Music",
    "musicas": "~/Music",
    "vídeos": "~/Videos",
    "videos": "~/Videos",
}


def caminho_da_pasta(nome):
    """Resolve 'downloads', 'C:\\coisas' ou None se não existir."""

    limpo = " ".join(
        str(nome or "").strip().strip("\"'").split()
    )

    if not limpo:
        return None

    conhecida = PASTAS_CONHECIDAS.get(limpo.lower())

    if conhecida:
        caminho = Path(os.path.expanduser(conhecida))

        return caminho if caminho.is_dir() else None

    caminho = Path(
        os.path.expandvars(
            os.path.expanduser(limpo)
        )
    )

    if caminho.is_dir():
        return caminho

    return None


# ============================================================
# PADRÕES
# ============================================================

# Muitas formas de dizer a mesma coisa (Fase 29).
ABRIR = r"(?:abr[ae]|abrir|abra|inicia|inicie|iniciar|executa|execute|" \
        r"roda|rode|chama|chame|entra\s+n[oa]|entre\s+n[oa]|vai\s+n[oa])"

# Fechar tem tantas formas quanto abrir. Sem isto, 'fecha o
# navegador' descia para o Claude e custava seis segundos.
FECHAR = r"(?:fech[ae]|fechar|feche|encerr[ae]|encerrar|sai\s+d[oa]|sair\s+d[oa])"

FECHAR_PROGRAMA = re.compile(
    FECHAR + r"\s+(?:o\s+|a\s+)?(.+)$",
    re.IGNORECASE
)

ABRIR_PROGRAMA = re.compile(
    ABRIR + r"\s+(?:o\s+|a\s+|no\s+|na\s+)?(.+)$",
    re.IGNORECASE
)

ABRIR_PASTA = re.compile(
    ABRIR + r"\s+(?:a\s+)?pasta\s+(?:de\s+|do\s+|da\s+)?(.+)$",
    re.IGNORECASE
)

ABRIR_ARQUIVO = re.compile(
    ABRIR + r"\s+(?:o\s+)?arquivo\s+(.+)$",
    re.IGNORECASE
)

ABRIR_SITE = re.compile(
    ABRIR + r"\s+(?:o\s+)?(?:site|endere[çc]o|link|p[áa]gina)\s+(.+)$|"
    + ABRIR + r"\s+((?:https?://|www\.)\S+)$",
    re.IGNORECASE
)

PROCURAR = re.compile(
    r"(?:procur[ae]|procurar|ach[ae]|achar|encontr[ae]|encontrar|"
    r"cad[êe]|onde\s+(?:est[áa]|ta|tá))\s+"
    r"(?:o\s+|a\s+)?(?:arquivo|documento|pasta)\s+(.+)$",
    re.IGNORECASE
)

VER_COMPUTADOR = re.compile(
    r"\bcomo\s+(?:est[áa]|ta|tá)\s+(?:o\s+)?(?:computador|pc|m[áa]quina|"
    r"notebook|sistema)\b|"
    r"\bstatus\s+d[oa]\s+(?:computador|m[áa]quina|sistema)\b|"
    r"\bquant[ao]\s+(?:de\s+)?(?:mem[óo]ria|ram|espa[çc]o|disco|bateria)\b|"
    r"\bmem[óo]ria\s+(?:livre|dispon[íi]vel)\b|"
    r"\bespa[çc]o\s+(?:livre|em\s+disco)\b|"
    r"\bcomo\s+(?:est[áa]|ta|tá)\s+a\s+bateria\b",
    re.IGNORECASE
)

PROCESSOS = re.compile(
    r"\bque\s+programas?\s+(?:est[ãa]o|ta|tá|t[ãa]o)\s+(?:abertos?|rodando)\b|"
    r"\bo\s+que\s+(?:est[áa]|ta|tá)\s+(?:aberto|rodando|gastando\s+mem[óo]ria)\b|"
    r"\bprogramas?\s+abertos?\b|"
    r"\bprocessos\s+(?:abertos|rodando)\b",
    re.IGNORECASE
)

POWERSHELL = re.compile(
    r"(?:rod[ae]|rodar|execut[ae]|executar)\s+"
    r"(?:esse\s+|este\s+|o\s+)?comando\s*[:,]?\s*(.+)$|"
    r"\bno\s+powershell\s*[:,]?\s*(.+)$|"
    r"(?:rod[ae]|execut[ae])\s+no\s+powershell\s*[:,]?\s*(.+)$",
    re.IGNORECASE
)

CRIAR_PASTA = re.compile(
    r"(?:cri[ae]|criar|faz|fa[çc]a)\s+(?:uma\s+)?pasta\s+"
    r"(?:chamada\s+|com\s+o\s+nome\s+)?(.+)$",
    re.IGNORECASE
)

APAGAR = re.compile(
    r"(?:apag[ae]|apagar|delet[ae]|deletar|exclu[ai]|excluir|remov[ae])\s+"
    r"(?:o\s+)?arquivo\s+(.+)$",
    re.IGNORECASE
)


DIAGNOSTICO = re.compile(
    r"\bvoc[êe]\s+(?:est[áa]|ta|tá)\s+bem\b|"
    r"\bdiagn[óo]stico\b|"
    # O roteador tira o "Milk," da frente antes de chegar aqui, então
    # "Milk doctor" chega como "doctor".
    r"\b(?:milk\s+)?doctor\b|"
    r"\bautoteste\b|"
    r"\b(?:est[áa]|ta|tá)\s+tudo\s+funcionando\b|"
    r"\btest[ae]\s+(?:os\s+)?seus\s+sistemas\b|"
    r"\bcomo\s+voc[êe]\s+(?:est[áa]|ta|tá)\s+de\s+sa[úu]de\b",
    re.IGNORECASE
)


def diagnosticar():
    """Roda o Milk Doctor e responde com o resumo.

    O relatório inteiro tem catorze linhas: bom de ler, ruim de ouvir.
    Ele vai para o log, e a resposta falada é o resumo — com o conserto
    junto, quando alguma coisa está ruim."""

    from milk.core.doutor import examinar, relatorio, resumo_falado
    from milk.core.log import logger

    resultados = examinar()

    inteiro = relatorio(resultados)

    logger("app").info("diagnóstico:\n" + inteiro)

    resumo = resumo_falado(resultados)

    return certo(
        resumo,
        {"relatorio": inteiro},
    )


def limpar(alvo):
    return " ".join(
        str(alvo or "").strip().strip("?!.,;:\"'").split()
    )


# ============================================================
# ROTA
# ============================================================

def rota_sistema(texto):
    """Devolve a Decisao da ação de sistema, ou None.

    A ordem importa. "Roda o comando X" e "roda o Chrome" começam
    igual, então o que mexe na máquina é olhado antes do que só abre.
    Nenhum trecho devolve None no meio: quem não reconhece o alvo passa
    a vez para o próximo, e o que sobrar vai para o Claude."""

    from milk.intelligence.roteador import Decisao

    # --- consultas, que não mexem em nada ---

    if DIAGNOSTICO.search(texto):
        return Decisao(
            "sistema",
            "🩺 Vendo se está tudo bem",
            diagnosticar,
        )

    if VER_COMPUTADOR.search(texto):
        return Decisao(
            "sistema",
            "💻 Vendo o computador",
            lambda: falar(acoes.ver_computador()),
            local=True,
        )

    if PROCESSOS.search(texto):
        return Decisao(
            "sistema",
            "💻 Vendo os programas abertos",
            lambda: falar(acoes.listar_processos()),
        )

    achado = PROCURAR.search(texto)

    if achado:
        alvo = limpar(achado.group(1))

        if len(alvo) >= 2:
            return Decisao(
                "sistema",
                f"🔎 Procurando {alvo}",
                lambda: falar(acoes.procurar_arquivo(alvo)),
            )

    # --- o que mexe na máquina: pergunta antes de fazer ---

    achado = POWERSHELL.search(texto)

    if achado:
        comando = limpar(
            achado.group(1) or achado.group(2) or achado.group(3)
        )

        if comando and len(comando) >= 2:
            return Decisao(
                "sistema",
                "⌨️ Comando do Windows",
                lambda: com_permissao(
                    "powershell",
                    comando,
                    f"Vou rodar: {comando}",
                    lambda: acoes.executar_powershell(comando),
                ),
                local=True,
            )

    achado = CRIAR_PASTA.search(texto)

    if achado:
        nome = limpar(achado.group(1))

        if len(nome) >= 2:
            destino = (
                Path(nome)
                if os.path.isabs(nome)
                else Path(os.path.expanduser("~/Desktop")) / nome
            )

            return Decisao(
                "sistema",
                "📁 Criando a pasta",
                lambda: com_permissao(
                    "criar_pasta",
                    str(destino),
                    f"Vou criar a pasta {destino}",
                    lambda: acoes.criar_pasta(destino),
                ),
                local=True,
            )

    achado = APAGAR.search(texto)

    if achado:
        caminho = Path(
            os.path.expanduser(
                limpar(achado.group(1))
            )
        )

        return Decisao(
            "sistema",
            "🗑️ Apagando arquivo",
            lambda: com_permissao(
                "apagar_arquivo",
                str(caminho),
                f"Vou apagar {caminho}",
                lambda: acoes.apagar_arquivo(caminho),
            ),
            local=True,
        )

    # --- abrir coisas: só o que ela reconhece ---

    achado = ABRIR_PASTA.search(texto)

    if achado:
        caminho = caminho_da_pasta(
            limpar(achado.group(1))
        )

        if caminho:
            return Decisao(
                "sistema",
                f"📂 Abrindo {caminho.name or caminho}",
                lambda: falar(acoes.abrir_pasta(caminho)),
                local=True,
            )

    achado = ABRIR_ARQUIVO.search(texto)

    if achado:
        alvo = Path(
            os.path.expanduser(
                limpar(achado.group(1))
            )
        )

        if alvo.is_file():
            return Decisao(
                "sistema",
                f"📄 Abrindo {alvo.name}",
                lambda: falar(acoes.abrir_arquivo(alvo)),
                local=True,
            )

    achado = ABRIR_SITE.search(texto)

    if achado:
        endereco = limpar(
            achado.group(1) or achado.group(2)
        )

        if acoes.endereco_valido(endereco):
            return Decisao(
                "sistema",
                f"🌐 Abrindo {endereco}",
                lambda: falar(acoes.abrir_url(endereco)),
                local=True,
            )

    achado = FECHAR_PROGRAMA.search(texto)

    if achado:
        nome = limpar(achado.group(1))

        executavel, chave = acoes.programa_conhecido(nome)

        # So programa que ela conhece. 'fecha o negocio com o
        # cliente' nao e ordem de sistema.
        if executavel is not None:
            return Decisao(
                "sistema",
                f"🖥️ Fechando {chave}",
                lambda: falar(acoes.fechar_programa(nome)),
                local=True,
            )
    achado = ABRIR_PROGRAMA.search(texto)

    if achado:
        nome = limpar(achado.group(1))

        executavel, chave = acoes.programa_conhecido(nome)

        # Só programa que ela conhece. O resto é conversa com o Claude.
        if executavel is not None:
            return Decisao(
                "sistema",
                f"🖥️ Abrindo {chave}",
                lambda: falar(acoes.abrir_programa(nome)),
                local=True,
            )

    return None
