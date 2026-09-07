# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Decide se um pedido vira ferramenta ou vai para o Claude.

A regra é ser conservador: só intercepta quando a intenção está muito
clara. Na dúvida, `rotear()` devolve None e o pedido segue o caminho
normal, com o Claude pensando.

Isso é código determinístico de propósito. Ele não interpreta nada
complexo; ele reconhece um punhado de perguntas objetivas e entrega o
resto para quem raciocina.
"""

import re
import datetime

from milk.core.config import BARK_TEXT
from milk.tools import certo, falhou
from milk.voice import latido as ferramenta_latido
from milk.tools import cep as ferramenta_cep
from milk.tools import clima as ferramenta_clima
from milk.tools import moedas as ferramenta_moedas
from milk.tools import relogio as ferramenta_relogio
from milk.intelligence.rotas_tarefas import rota_tarefas
from milk.intelligence.rotas_conversa import rota_conversa
from milk.intelligence.rotas_memoria import rota_memoria
from milk.intelligence.rotas_sistema import rota_sistema
from milk.tools import feriados as ferramenta_feriados
from milk.tools import github_api as ferramenta_github
from milk.tools import wikipedia as ferramenta_wikipedia
from milk.tools import localizacao as ferramenta_localizacao


class Decisao:
    """Uma ferramenta escolhida, já com os argumentos prontos."""

    def __init__(
        self,
        ferramenta,
        descricao,
        executar,
        local=False,
        silenciosa=False,
    ):
        self.ferramenta = ferramenta
        self.descricao = descricao
        self.executar = executar

        # local: roda na hora, sem thread, porque nao ha rede envolvida.
        self.local = local

        # silenciosa: a resposta aparece escrita, mas nao vai para a voz.
        self.silenciosa = silenciosa

    def __repr__(self):
        return f"<Decisao {self.ferramenta}>"


# O nome dela na frente não muda a intenção.
PREFIXO_MILK = re.compile(
    r"^\s*(?:milk|milque|milki|milc)\s*[,;:\-]?\s*",
    re.IGNORECASE
)


# Se o pedido é para FAZER alguma coisa, não é consulta: é trabalho, e
# trabalho é com o Claude.
VETO = re.compile(
    r"\b("
    # "vai fazer frio" e pergunta de tempo, nao pedido de trabalho.
    r"fa[çc]a(?!\s+(?:frio|calor|sol|au))|"
    r"faz(?:er)?(?!\s+(?:frio|calor|sol|au))|"
    r"crie|criar|cria|gere|gerar|escreva|escrever|"
    r"programe|programar|c[óo]digo|script|fun[çc][ãa]o|classe|arquivo|"
    r"pasta|diret[óo]rio|projeto|corrija|corrigir|conserte|refatore|"
    r"implemente|implementar|instale|instalar|configure|configurar|"
    r"rode|rodar|execute|executar|abra|abrir|clone|clonar|suba|subir|"
    r"publique|publicar|push|commitar|apague|apagar|delete|deletar|"
    r"mova|mover|renomeie|renomear|salve|salvar|baixe|baixar|teste|"
    r"testar|simule|automatize|me ensine|ensina|tutorial|exemplo de"
    r")\b",
    re.IGNORECASE
)


# Pronomes e referências que só fazem sentido com o resto da conversa.
ANAFORA = re.compile(
    r"^(?:voc[êe]|vc|tu|eu|ele|ela|eles|elas|isso|isto|aquilo|esse|"
    r"essa|aquele|aquela|milk|a milk|meu|minha|nosso|a gente)\b",
    re.IGNORECASE
)


NUMEROS_FALADOS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "três": 3,
    "cinco": 5,
    "dez": 10,
    "quinze": 15,
    "vinte": 20,
    "trinta": 30,
    "cinquenta": 50,
    "cem": 100,
    "duzentos": 200,
    "quinhentos": 500,
    "mil": 1000,
}


def limpar(texto):
    """Tira o 'Milk,' da frente e normaliza os espaços."""

    limpo = PREFIXO_MILK.sub(
        "",
        str(texto or "")
    )

    return re.sub(
        r"\s+",
        " ",
        limpo
    ).strip()


def numero_falado(texto):
    """'1.234,50' e 'cem' viram números. Devolve None se não der."""

    bruto = str(texto or "").strip().lower()

    if bruto in NUMEROS_FALADOS:
        return float(NUMEROS_FALADOS[bruto])

    if not re.match(r"^\d[\d.,]*$", bruto):
        return None

    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")

    elif re.match(r"^\d{1,3}(?:\.\d{3})+$", bruto):
        bruto = bruto.replace(".", "")

    try:
        return float(bruto)

    except ValueError:
        return None


# ============================================================
# LATIDO
# ============================================================

# Só pedido direto para ela latir. Nada de "pesquise sobre latidos".
LATIDO = re.compile(
    r"^late\b|"
    r"\blate\s+(?:pra|para)\s+mim\b|"
    r"\b(?:d[áa]|d[êe]|manda|solta|solte)\s+(?:um\s+)?latido\b|"
    r"\bquero\s+(?:te\s+)?ouvir\s+(?:voc[êe]\s+)?latir\b|"
    r"\b(?:fa[çc]a|faz|fala|solta|solte)\s+au\s*au\b|"
    r"\bpode\s+latir\b|"
    r"\blatir\s+(?:pra|para)\s+mim\b",
    re.IGNORECASE
)


def executar_latido():
    """Toca o som e devolve a frase curta que aparece na conversa."""

    if ferramenta_latido.latir():
        return certo(
            f"{BARK_TEXT} 🐶"
        )

    return falhou(
        ferramenta_latido.descrever_problema()
    )


def rota_latido(texto):
    if not LATIDO.search(texto):
        return None

    return Decisao(
        "latido",
        "🐶 Latindo",
        executar_latido,
        local=True,
        silenciosa=True,
    )


# ============================================================
# RELÓGIO E CALENDÁRIO
# ============================================================

# Tudo aqui é local: sai do relógio da máquina, sem rede e sem Claude.

QUE_HORAS = re.compile(
    r"\bque\s+horas?\s+(?:s[ãa]o|é|e|tem|ser[ãa]o)\b|"
    r"\bhoras?\s+s[ãa]o\s+agora\b|"
    r"\bqual\s+(?:é\s+|e\s+)?(?:a\s+)?hora\b"
    r"(?!\s+(?:d[eoa]s?|para|pra|que|em|marcada))|"
    r"\bhora\s+certa\b|"
    r"\bhor[áa]rio\s+(?:agora|atual|certo)\b|"
    r"\bme\s+(?:diz|diga|fala|fale|d[êe])\s+(?:as\s+horas|a\s+hora)\b",
    re.IGNORECASE
)

DIA_DA_SEMANA = re.compile(
    r"\bque\s+dia\s+da\s+semana\b|"
    r"\bdia\s+da\s+semana\s+(?:é|e)\s+hoje\b|"
    r"\bem\s+que\s+dia\s+da\s+semana\s+(?:n[óo]s\s+)?estamos\b",
    re.IGNORECASE
)

QUE_DIA_HOJE = re.compile(
    r"\bque\s+dia\s+(?:é|e)\s+hoje\b|"
    r"\bque\s+data\s+(?:é|e)\s+hoje\b|"
    r"\bdata\s+de\s+hoje\b|"
    r"\bqual\s+(?:é\s+|e\s+)?(?:a\s+)?data\s+(?:de\s+)?hoje\b|"
    r"\bqual\s+(?:é\s+|e\s+)?o\s+dia\s+de\s+hoje\b|"
    r"\bem\s+que\s+dia\s+(?:n[óo]s\s+)?estamos\b",
    re.IGNORECASE
)

QUE_DIA_AMANHA = re.compile(
    r"\bque\s+dia\s+(?:é|e|ser[áa]|vai\s+ser)\s+amanh[ãa]\b|"
    r"\bamanh[ãa]\s+(?:é|e|ser[áa])\s+que\s+dia\b",
    re.IGNORECASE
)

QUE_DIA_ONTEM = re.compile(
    r"\bque\s+dia\s+(?:foi|era|é|e)\s+ontem\b|"
    r"\bontem\s+foi\s+que\s+dia\b",
    re.IGNORECASE
)

QUE_MES = re.compile(
    r"\bem\s+que\s+m[êe]s\s+(?:n[óo]s\s+)?estamos\b|"
    r"\bque\s+m[êe]s\s+(?:é|e)\s+(?:esse|este|agora|hoje)\b|"
    r"\bqual\s+(?:é\s+|e\s+)?o\s+m[êe]s\s+(?:atual|de\s+hoje)\b",
    re.IGNORECASE
)

QUE_ANO = re.compile(
    r"\bem\s+que\s+ano\s+(?:n[óo]s\s+)?estamos\b|"
    r"\bque\s+ano\s+(?:é|e)\s+(?:esse|este|agora|hoje)\b|"
    r"\bqual\s+(?:é\s+|e\s+)?o\s+ano\s+(?:atual|de\s+hoje)\b",
    re.IGNORECASE
)

QUANTOS_DIAS = re.compile(
    r"\bquantos?\s+dias\s+(?:ainda\s+)?(?:faltam|falta|restam|resta)\s+"
    r"(?:para|pro|pra|at[ée])\s+(.+)$|"
    r"\b(?:faltam|falta)\s+quantos\s+dias\s+(?:para|pro|pra|at[ée])\s+"
    r"(.+)$",
    re.IGNORECASE
)


def rota_relogio(texto):
    if QUE_HORAS.search(texto):
        return Decisao(
            "relogio",
            "🕒 Vendo as horas",
            ferramenta_relogio.que_horas,
            local=True,
        )

    if DIA_DA_SEMANA.search(texto):
        return Decisao(
            "relogio",
            "📅 Vendo o dia da semana",
            ferramenta_relogio.dia_da_semana,
            local=True,
        )

    if QUE_DIA_AMANHA.search(texto):
        return Decisao(
            "relogio",
            "📅 Vendo que dia é amanhã",
            lambda: ferramenta_relogio.dia_vizinho(1),
            local=True,
        )

    if QUE_DIA_ONTEM.search(texto):
        return Decisao(
            "relogio",
            "📅 Vendo que dia foi ontem",
            lambda: ferramenta_relogio.dia_vizinho(-1),
            local=True,
        )

    if QUE_DIA_HOJE.search(texto):
        return Decisao(
            "relogio",
            "📅 Vendo a data de hoje",
            ferramenta_relogio.que_dia_e_hoje,
            local=True,
        )

    if QUE_MES.search(texto):
        return Decisao(
            "relogio",
            "📅 Vendo em que mês estamos",
            ferramenta_relogio.mes_atual,
            local=True,
        )

    if QUE_ANO.search(texto):
        return Decisao(
            "relogio",
            "📅 Vendo em que ano estamos",
            ferramenta_relogio.ano_atual,
            local=True,
        )

    achado = QUANTOS_DIAS.search(texto)

    if achado:
        dito = achado.group(1) or achado.group(2)

        alvo = ferramenta_relogio.entender_data(dito)

        # Data que ela não reconhece ("para eu viajar") é conversa,
        # e conversa é com o Claude.
        if not alvo:
            return None

        return Decisao(
            "relogio",
            "📅 Contando os dias",
            lambda: ferramenta_relogio.dias_para(alvo),
            local=True,
        )

    return None


# ============================================================
# CEP
# ============================================================

def rota_cep(texto):
    if not re.search(r"\bcep\b", texto, re.IGNORECASE):
        return None

    digitos = re.sub(
        r"\D",
        "",
        texto
    )

    if len(digitos) != 8:
        return None

    formatado = f"{digitos[:5]}-{digitos[5:]}"

    return Decisao(
        "cep",
        f"📮 Procurando o CEP {formatado}",
        lambda: ferramenta_cep.buscar_cep(digitos),
    )


# ============================================================
# MOEDAS
# ============================================================

MOEDAS_FALADAS = "|".join(
    sorted(
        (
            re.escape(nome)
            for nome in ferramenta_moedas.NOMES
        ),
        key=len,
        reverse=True,
    )
)

VALOR = r"(\d[\d.,]*|" + "|".join(
    re.escape(palavra)
    for palavra in NUMEROS_FALADOS
) + r")"

CONVERSAO = re.compile(
    VALOR
    + r"\s*(" + MOEDAS_FALADAS + r")\b"
    + r"\s*(?:em|para|pra|equivalem? a|valem? em|d[ãa]o em)\s*"
    + r"(" + MOEDAS_FALADAS + r")\b",
    re.IGNORECASE
)

COTACAO = re.compile(
    r"\b(?:cota[çc][ãa]o|pre[çc]o|valor)\s+d[oae]s?\s+("
    + MOEDAS_FALADAS
    + r")\b",
    re.IGNORECASE
)


def rota_moedas(texto):
    achado = CONVERSAO.search(texto)

    if achado:
        valor = numero_falado(
            achado.group(1)
        )

        if valor is None:
            return None

        origem = ferramenta_moedas.codigo_da_moeda(
            achado.group(2)
        )

        destino = ferramenta_moedas.codigo_da_moeda(
            achado.group(3)
        )

        if not origem or not destino:
            return None

        return Decisao(
            "moedas",
            f"💱 Convertendo {origem} para {destino}",
            lambda: ferramenta_moedas.converter(
                valor,
                origem,
                destino
            ),
        )

    achado = COTACAO.search(texto)

    if achado:
        origem = ferramenta_moedas.codigo_da_moeda(
            achado.group(1)
        )

        if not origem:
            return None

        return Decisao(
            "moedas",
            f"💱 Vendo a cotação de {origem}",
            lambda: ferramenta_moedas.cotacao(origem),
        )

    return None


# ============================================================
# CLIMA
# ============================================================

CHUVA = re.compile(
    r"\bvai\s+chover\b|\b(?:est[áa]|ta|tá)\s+chovendo\b|"
    r"\bvai\s+dar\s+chuva\b|\bchance\s+de\s+chuva\b",
    re.IGNORECASE
)

TEMPO = re.compile(
    r"\bprevis[ãa]o\s+do\s+tempo\b|"
    r"\bcomo\s+(?:est[áa]|ta|tá|vai\s+estar|vai\s+ficar)\s+o\s+"
    r"(?:tempo|clima)\b|"
    r"\bqual\s+(?:é\s+|e\s+)?o\s+clima\b|"
    r"\bo\s+tempo\s+(?:hoje|amanh[ãa])\b",
    re.IGNORECASE
)

TEMPERATURA = re.compile(
    r"\btemperatura\b",
    re.IGNORECASE
)

MOLDURA_TEMPERATURA = re.compile(
    r"\b(qual|quanto|quantos|est[áa]|ta|tá|agora|hoje|amanh[ãa]|"
    r"l[áa]\s+fora|fora)\b",
    re.IGNORECASE
)

FRIO_CALOR = re.compile(
    r"\bvai\s+(?:fazer|estar|ficar)\s+(?:frio|calor)\b|"
    r"\b(?:est[áa]|ta|tá)\s+(?:frio|calor)\s+(?:hoje|agora|amanh[ãa])\b",
    re.IGNORECASE
)

NAO_E_CIDADE = {
    "graus",
    "celsius",
    "fahrenheit",
    "casa",
    "ponto",
    "media",
    "média",
}


def cidade_do_texto(texto):
    """Pega o 'em Curitiba' do fim da frase. Sem isso, usa o padrão."""

    achado = re.search(
        r"\bem\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'\-\s]{1,40})$",
        texto.strip().rstrip("?!."),
        re.IGNORECASE
    )

    if not achado:
        return None

    cidade = achado.group(1)

    cidade = re.sub(
        r"\b(hoje|agora|amanh[ãa]|de\s+manh[ãa]|[àa]\s+noite|"
        r"de\s+tarde|mais\s+tarde)\b",
        "",
        cidade,
        flags=re.IGNORECASE
    )

    cidade = cidade.strip(" ,.-")

    if not cidade or cidade.lower() in NAO_E_CIDADE:
        return None

    return cidade


def rota_clima(texto):
    chuva = CHUVA.search(texto)
    tempo = TEMPO.search(texto)

    temperatura = (
        TEMPERATURA.search(texto)
        and
        MOLDURA_TEMPERATURA.search(texto)
    )

    frio_calor = FRIO_CALOR.search(texto)

    if not (chuva or tempo or temperatura or frio_calor):
        return None

    cidade = cidade_do_texto(texto)

    amanha = re.search(
        r"\bamanh[ãa]\b",
        texto,
        re.IGNORECASE
    )

    onde = cidade or "aqui"

    if chuva:
        quando = "amanha" if amanha else "hoje"

        return Decisao(
            "clima",
            f"🌦️ Vendo a chuva {onde}",
            lambda: ferramenta_clima.vai_chover(
                cidade,
                quando
            ),
        )

    if amanha:
        return Decisao(
            "clima",
            f"🌤️ Vendo a previsão de amanhã {onde}",
            lambda: ferramenta_clima.previsao_amanha(cidade),
        )

    if temperatura and not tempo:
        return Decisao(
            "clima",
            f"🌡️ Vendo a temperatura {onde}",
            lambda: ferramenta_clima.temperatura_agora(cidade),
        )

    return Decisao(
        "clima",
        f"🌤️ Vendo o tempo {onde}",
        lambda: ferramenta_clima.clima_agora(cidade),
    )


# ============================================================
# FERIADOS
# ============================================================

MOLDURA_FERIADO = re.compile(
    r"\bpr[óo]xim|\bquais\b|\bquando\b|\bqual\b|\blista\b|"
    r"\bquantos\b|\bvem\b|\btem\b|\b20\d{2}\b",
    re.IGNORECASE
)


def rota_feriados(texto):
    if not re.search(r"\bferiado", texto, re.IGNORECASE):
        return None

    if not MOLDURA_FERIADO.search(texto):
        return None

    ano = re.search(
        r"\b(20\d{2})\b",
        texto
    )

    if ano:
        numero = int(
            ano.group(1)
        )

        return Decisao(
            "feriados",
            f"📅 Vendo os feriados de {numero}",
            lambda: ferramenta_feriados.feriados_do_ano(numero),
        )

    if re.search(
        r"\bano\s+que\s+vem\b|\bpr[óo]ximo\s+ano\b",
        texto,
        re.IGNORECASE
    ):
        numero = datetime.date.today().year + 1

        return Decisao(
            "feriados",
            f"📅 Vendo os feriados de {numero}",
            lambda: ferramenta_feriados.feriados_do_ano(numero),
        )

    return Decisao(
        "feriados",
        "📅 Vendo os próximos feriados",
        lambda: ferramenta_feriados.proximos_feriados(),
    )


# ============================================================
# GITHUB
# ============================================================

NOME_COMPLETO = re.compile(
    r"\b([\w.-]+/[\w.-]+)\b"
)

DEPOIS_DE_REPO = re.compile(
    r"\b(?:reposit[óo]rio|repo|projeto)\s+"
    r"(?:d[oae]\s+)?[\"']?([\w.\-]+(?:/[\w.\-]+)?)[\"']?",
    re.IGNORECASE
)

PEDIDO_COMMITS = re.compile(
    r"\bcommits?\b.*\b(recentes|[úu]ltimos|novos|quais|mostr|veja|ver)\b|"
    r"\b(recentes|[úu]ltimos|quais|mostr|veja|ver)\b.*\bcommits?\b",
    re.IGNORECASE
)

PALAVRAS_VAZIAS = {
    "do",
    "da",
    "de",
    "no",
    "na",
    "o",
    "a",
    "um",
    "uma",
    "repositorio",
    "repositório",
    "repo",
    "projeto",
    "github",
}


def alvo_github(texto):
    achado = NOME_COMPLETO.search(texto)

    if achado:
        return achado.group(1)

    achado = DEPOIS_DE_REPO.search(texto)

    if achado:
        alvo = achado.group(1).strip()

        if alvo.lower() not in PALAVRAS_VAZIAS:
            return alvo

    return None


def rota_github(texto):
    tem_github = re.search(
        r"\bgithub\b",
        texto,
        re.IGNORECASE
    )

    tem_repo = re.search(
        r"\breposit[óo]rio\b|\brepo\b",
        texto,
        re.IGNORECASE
    )

    if not (tem_github or tem_repo):
        return None

    alvo = alvo_github(texto)

    if not alvo:
        return None

    if PEDIDO_COMMITS.search(texto):
        return Decisao(
            "github",
            f"🐙 Vendo os commits de {alvo}",
            lambda: ferramenta_github.commits_recentes(alvo),
        )

    return Decisao(
        "github",
        f"🐙 Vendo o repositório {alvo}",
        lambda: ferramenta_github.descrever_repositorio(alvo),
    )


# ============================================================
# LOCALIZAÇÃO
# ============================================================

ONDE_FICA = re.compile(
    r"\bonde\s+(?:que\s+)?(?:fica|é|e|est[áa]|se\s+localiza)\s+"
    r"(?:o\s+|a\s+|os\s+|as\s+)?(.+)$",
    re.IGNORECASE
)

NAO_E_LUGAR = re.compile(
    r"\.(py|json|txt|md|exe|log|wav|mp3|png)\b|[\\/]|"
    r"\b(fun[çc][ãa]o|vari[áa]vel|m[óo]dulo|classe|log|erro|config|"
    r"reposit[óo]rio|commit|branch|linha|bot[ãa]o|menu)\b",
    re.IGNORECASE
)


def rota_localizacao(texto):
    achado = ONDE_FICA.search(texto)

    if not achado:
        return None

    lugar = achado.group(1).strip().strip("?!.,")

    if len(lugar) < 3:
        return None

    if NAO_E_LUGAR.search(lugar) or ANAFORA.match(lugar):
        return None

    return Decisao(
        "localizacao",
        f"📍 Procurando {lugar} no mapa",
        lambda: ferramenta_localizacao.procurar_lugar(lugar),
    )


# ============================================================
# WIKIPÉDIA
# ============================================================

WIKIPEDIA_EXPLICITA = re.compile(
    r"\bwikip[éeê]dia\b[\s,:]*(?:sobre\s+)?(.*)$",
    re.IGNORECASE
)

QUEM_E = re.compile(
    r"^quem\s+(?:é|e|foi|eram|s[ãa]o)\s+"
    r"(?:o\s+|a\s+|os\s+|as\s+)?(.+)$",
    re.IGNORECASE
)

O_QUE_E = re.compile(
    r"^o\s+que\s+(?:é|e|s[ãa]o|era|eram)\s+"
    r"(?:o\s+|a\s+|um\s+|uma\s+|os\s+|as\s+)?(.+)$",
    re.IGNORECASE
)

NAO_E_VERBETE = re.compile(
    r"\.(py|json|txt|md|exe|log)\b|[\\/()]|\bisso\b|\bisto\b|\baquilo\b",
    re.IGNORECASE
)


def assunto_valido(assunto, limite_palavras=5):
    assunto = assunto.strip().strip("?!.,;:")

    if len(assunto) < 2:
        return None

    if ANAFORA.match(assunto):
        return None

    if NAO_E_VERBETE.search(assunto):
        return None

    if len(assunto.split()) > limite_palavras:
        return None

    return assunto


def rota_wikipedia(texto):
    # Pedido explícito: "pesquise na Wikipédia X".
    if re.search(r"wikip[éeê]dia", texto, re.IGNORECASE):
        achado = WIKIPEDIA_EXPLICITA.search(texto)

        if achado:
            assunto = assunto_valido(
                achado.group(1),
                limite_palavras=10
            )

            if assunto:
                return Decisao(
                    "wikipedia",
                    f"📚 Procurando {assunto} na Wikipédia",
                    lambda: ferramenta_wikipedia.pesquisar(assunto),
                )

        return None

    # "quem é X" e "o que é X", só com assunto curto e concreto.
    for padrao in (QUEM_E, O_QUE_E):
        achado = padrao.match(
            texto.strip()
        )

        if not achado:
            continue

        assunto = assunto_valido(
            achado.group(1)
        )

        if assunto:
            return Decisao(
                "wikipedia",
                f"📚 Procurando {assunto} na Wikipédia",
                lambda: ferramenta_wikipedia.pesquisar(assunto),
            )

    return None


# Ordem importa: o mais específico primeiro.
ROTAS = (
    rota_latido,
    rota_relogio,
    rota_cep,
    rota_moedas,
    rota_clima,
    rota_feriados,
    rota_github,
    rota_localizacao,
    rota_wikipedia,
)


def rotear(texto, pessoa=None):
    """Devolve a Decisao da ferramenta, ou None para mandar ao Claude."""

    limpo = limpar(texto)

    # Conversa curta ("oi", "tudo bem?", "obrigado") vem antes de tudo,
    # inclusive do tamanho mínimo: são justamente as frases mais curtas,
    # e mandá-las para o Claude custava seis segundos cada uma.
    try:
        conversa = rota_conversa(limpo, pessoa)

    except Exception:
        conversa = None

    if conversa:
        return conversa

    if len(limpo) < 3:
        return None

    # Comando sobre a propria fila, sobre a memoria ou sobre a
    # maquina vem antes do veto: "faca isso depois", "anote que..." e
    # "abra o bloco de notas" nao sao trabalho para o Claude, e todos
    # comecam com palavra que o veto pegaria.
    for rota_de_comando in (rota_tarefas, rota_memoria, rota_sistema):
        try:
            comando = rota_de_comando(limpo)

        except Exception:
            comando = None

        if comando:
            return comando

    if VETO.search(limpo):
        return None

    for rota in ROTAS:
        try:
            decisao = rota(limpo)

        except Exception:
            # O roteador nunca derruba a Milk: na dúvida, Claude resolve.
            continue

        if decisao:
            return decisao

    return None
