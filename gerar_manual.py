# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Gera o manual da Milk em PDF.

    .venv\\Scripts\\python.exe gerar_manual.py

Sai em `Manual da Milk.pdf`, na pasta do projeto. O texto mora aqui
mesmo, em blocos, para o manual ser atualizado junto com o programa —
documentação que vive longe do código envelhece sozinha.
"""

import os
import sys

from datetime import date
from pathlib import Path

from fpdf import FPDF


BASE = Path(__file__).resolve().parent

FONTES = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

TITULO = "Manual da Milk"

SUBTITULO = "Assistente pessoal para Windows"

AUTOR = "Thales Teracin"

VERSAO = "1.0"


# Cores da casa.
AZUL = (37, 68, 110)
CINZA = (95, 99, 104)
CLARO = (240, 243, 247)
PRETO = (28, 30, 33)


class Manual(FPDF):
    """Cabeçalho, rodapé e os blocos de texto do manual."""

    def __init__(self):
        super().__init__(format="A4")

        self.set_auto_page_break(True, margin=20)

        self.set_margins(20, 18, 20)

        self.add_font("ui", "", str(FONTES / "segoeui.ttf"))
        self.add_font("ui", "B", str(FONTES / "segoeuib.ttf"))

        self.set_title(TITULO)
        self.set_author(AUTOR)
        self.set_creator("Milk")
        self.set_subject(SUBTITULO)

        self.capa = True

    # --------------------------------------------------------

    def header(self):
        if self.capa:
            return

        self.set_font("ui", "", 8)
        self.set_text_color(*CINZA)

        self.cell(0, 6, TITULO, align="L")
        self.cell(0, 6, f"© 2026 {AUTOR}", align="R", new_x="LMARGIN", new_y="NEXT")

        self.set_draw_color(220, 224, 230)
        self.line(20, 24, 190, 24)

        self.ln(6)

    def footer(self):
        if self.capa:
            return

        self.set_y(-15)

        self.set_font("ui", "", 8)
        self.set_text_color(*CINZA)

        self.cell(
            0,
            6,
            f"Página {self.page_no() - 1}",
            align="C",
        )

    # --------------------------------------------------------

    def titulo(self, texto):
        if self.get_y() > 230:
            self.add_page()

        self.ln(4)

        self.set_font("ui", "B", 15)
        self.set_text_color(*AZUL)

        self.multi_cell(0, 8, texto, new_x="LMARGIN", new_y="NEXT")

        self.ln(2)

    def subtitulo(self, texto):
        if self.get_y() > 245:
            self.add_page()

        self.ln(2)

        self.set_font("ui", "B", 11)
        self.set_text_color(*PRETO)

        self.multi_cell(0, 6, texto, new_x="LMARGIN", new_y="NEXT")

        self.ln(1)

    def paragrafo(self, texto):
        self.set_font("ui", "", 10.5)
        self.set_text_color(*PRETO)

        self.multi_cell(0, 5.6, texto, new_x="LMARGIN", new_y="NEXT")

        self.ln(2)

    def passo(self, numero, texto):
        self.set_font("ui", "B", 10.5)
        self.set_text_color(*AZUL)

        self.cell(8, 5.6, f"{numero}.")

        self.set_font("ui", "", 10.5)
        self.set_text_color(*PRETO)

        self.multi_cell(0, 5.6, texto, new_x="LMARGIN", new_y="NEXT")

        self.ln(1.5)

    def marcador(self, texto):
        self.set_font("ui", "", 10.5)
        self.set_text_color(*PRETO)

        self.cell(6, 5.6, "•")

        self.multi_cell(0, 5.6, texto, new_x="LMARGIN", new_y="NEXT")

        self.ln(0.8)

    def caixa(self, titulo, texto):
        """Um aviso destacado, para o que não pode passar batido."""

        altura = 8 + 5.2 * max(
            1,
            len(self.multi_cell(0, 5.2, texto, dry_run=True, output="LINES"))
        )

        if self.get_y() + altura > 265:
            self.add_page()

        topo = self.get_y()

        self.set_fill_color(*CLARO)
        self.set_draw_color(200, 210, 225)

        self.rect(20, topo, 170, altura, style="DF")

        self.set_xy(24, topo + 3)

        self.set_font("ui", "B", 10)
        self.set_text_color(*AZUL)

        self.cell(0, 5, titulo, new_x="LMARGIN", new_y="NEXT")

        self.set_x(24)

        self.set_font("ui", "", 10)
        self.set_text_color(*PRETO)

        self.multi_cell(162, 5.2, texto, new_x="LMARGIN", new_y="NEXT")

        self.set_y(topo + altura + 4)

    def codigo(self, texto):
        self.set_font("courier", "", 10)
        self.set_fill_color(245, 246, 248)
        self.set_text_color(*PRETO)

        self.multi_cell(
            0,
            5.4,
            texto,
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )

        self.ln(3)

    def tabela(self, cabecalho, linhas, larguras):
        if self.get_y() + 8 + 7 * len(linhas) > 265:
            self.add_page()

        self.set_font("ui", "B", 9.5)
        self.set_fill_color(*AZUL)
        self.set_text_color(255, 255, 255)

        for texto, largura in zip(cabecalho, larguras):
            self.cell(largura, 7, f" {texto}", fill=True, border=0)

        self.ln()

        self.set_font("ui", "", 9.5)
        self.set_text_color(*PRETO)

        claro = True

        for linha in linhas:
            altura = 6.2 * max(
                len(
                    self.multi_cell(
                        largura - 2,
                        6.2,
                        str(celula),
                        dry_run=True,
                        output="LINES",
                    )
                )
                for celula, largura in zip(linha, larguras)
            )

            if self.get_y() + altura > 268:
                self.add_page()

            self.set_fill_color(*(CLARO if claro else (255, 255, 255)))

            topo = self.get_y()
            esquerda = self.get_x()

            for celula, largura in zip(linha, larguras):
                self.set_xy(esquerda, topo)

                self.multi_cell(
                    largura,
                    altura,
                    f" {celula}",
                    fill=True,
                    border=0,
                    new_x="RIGHT",
                    new_y="TOP",
                    max_line_height=6.2,
                )

                esquerda += largura

            self.set_y(topo + altura)

            claro = not claro

        self.ln(4)


# ============================================================
# O CONTEÚDO
# ============================================================

def capa(pdf):
    pdf.add_page()

    pdf.ln(45)

    avatar = BASE / "assets" / "capa_manual.png"

    if not avatar.is_file():
        avatar = BASE / "milk_avatar.png"

    if avatar.is_file():
        pdf.image(str(avatar), x=80, w=50)

        pdf.ln(6)

    pdf.set_font("ui", "B", 30)
    pdf.set_text_color(*AZUL)

    pdf.cell(0, 14, TITULO, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("ui", "", 13)
    pdf.set_text_color(*CINZA)

    pdf.cell(0, 8, SUBTITULO, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    pdf.set_font("ui", "", 10.5)

    pdf.cell(
        0,
        6,
        f"Instalação e uso · versão {VERSAO} · {date.today().strftime('%d/%m/%Y')}",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(60)

    pdf.set_font("ui", "B", 10)
    pdf.set_text_color(*PRETO)

    pdf.cell(
        0,
        6,
        f"© 2026 {AUTOR} — Todos os direitos reservados",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font("ui", "", 8.5)
    pdf.set_text_color(*CINZA)

    pdf.multi_cell(
        0,
        4.6,
        "Software proprietário. É proibida a cópia, a distribuição, a modificação "
        "e a engenharia reversa, no todo ou em parte, sem autorização expressa e "
        "por escrito do autor. Este manual está protegido pelas mesmas condições.",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.capa = False


def o_que_e(pdf):
    pdf.add_page()

    pdf.titulo("1. O que é a Milk")

    pdf.paragrafo(
        "A Milk é uma assistente pessoal que mora na área de trabalho do Windows, "
        "em forma de cachorrinha. Você conversa com ela por texto ou por voz, e "
        "ela responde falando."
    )

    pdf.paragrafo("Ela faz quatro tipos de coisa:")

    pdf.marcador(
        "Responde na hora o que ela mesma sabe: hora, data, clima, CEP, cotação de "
        "moedas, Wikipédia, feriados, lugares no mapa e quantos dias faltam para uma data."
    )

    pdf.marcador(
        "Faz coisas no Windows: abre programas, pastas, arquivos e sites, procura "
        "arquivo pelo nome e conta como está o computador."
    )

    pdf.marcador(
        "Resolve trabalho de verdade com o Claude Code — programar, investigar, "
        "corrigir, analisar um projeto — mostrando o progresso passo a passo."
    )

    pdf.marcador(
        "Lembra do que foi conversado, guarda o que você pede para ela guardar e "
        "mantém uma fila de tarefas que sobrevive a fechar a janela."
    )

    pdf.ln(2)

    pdf.caixa(
        "O que ela nunca faz",
        "Ela não apaga, não move e não executa comando nenhum sem perguntar antes. "
        "E coisa que pode quebrar o Windows ela não faz nem se você confirmar."
    )


def instalacao(pdf):
    pdf.titulo("2. Instalação")

    pdf.subtitulo("2.1. O que precisa estar na máquina")

    pdf.tabela(
        ["Item", "Para quê", "Como conferir"],
        [
            ["Windows 10 ou 11", "É o sistema em que ela roda", "—"],
            [
                "Claude Code",
                "O cérebro dela para trabalho pesado",
                "No terminal: claude --version",
            ],
            [
                "Internet",
                "Voz e reconhecimento de fala",
                "Qualquer site abrindo",
            ],
            [
                "Microfone",
                "Só para falar com ela; digitar funciona sem",
                "Milk.exe doutor",
            ],
        ],
        [38, 66, 66],
    )

    pdf.subtitulo("2.2. Instalando pelo executável (mais simples)")

    pdf.passo(1, "Copie a pasta Milk inteira para onde você quiser guardar o programa. "
                 "Por exemplo: C:\\Milk ou a sua área de trabalho.")

    pdf.passo(2, "Dentro dela, dê dois cliques em Milk.exe.")

    pdf.passo(3, "A Milk aparece no canto inferior direito da tela. Pronto.")

    pdf.paragrafo(
        "A pasta precisa continuar inteira: o Milk.exe usa o que está ao lado dele "
        "(a pasta _internal, a pasta assets e a pasta config). Mover só o "
        "Milk.exe para outro lugar não funciona."
    )

    pdf.caixa(
        "Onde ficam os seus dados",
        "Tudo o que a Milk guarda (fila de tarefas, memória, conversa, modo e "
        "posição) fica em arquivos .json dentro da mesma pasta do Milk.exe, junto "
        "com a pasta logs. Nada é enviado para lugar nenhum além do que for "
        "necessário para responder você."
    )

    pdf.subtitulo("2.3. Instalando pelo código-fonte")

    pdf.paragrafo(
        "Se você prefere rodar pelo Python, a pasta do projeto já vem com o "
        "ambiente pronto em .venv. Use um destes:"
    )

    pdf.codigo(
        "Milk.bat                 abre a Milk\n"
        "Milk.bat doutor          diagnóstico no terminal\n"
        "python milk.py           o mesmo, com terminal aberto"
    )

    pdf.subtitulo("2.4. Abrir junto com o Windows")

    pdf.paragrafo(
        "Clique com o botão direito na Milk e marque \"Iniciar com o Windows\". "
        "Ela passa a abrir sozinha quando você liga o computador. Para desfazer, "
        "desmarque a mesma opção."
    )


def primeiro_uso(pdf):
    pdf.add_page()

    pdf.titulo("3. Primeiro uso")

    pdf.passo(1, "Clique na Milk. A janela de conversa abre.")

    pdf.passo(2, "Na primeira vez ela pergunta com quem está falando. "
                 "Responda, por exemplo: \"sou o Thales\". Ela guarda e não pergunta mais.")

    pdf.passo(3, "Escreva um pedido e aperte Enter. Ela responde por escrito e falando.")

    pdf.ln(2)

    pdf.subtitulo("Frases para experimentar")

    pdf.tabela(
        ["Escreva isto", "E ela..."],
        [
            ["que horas são?", "responde na hora, sem consultar nada"],
            ["vai chover amanhã?", "consulta a previsão do tempo"],
            ["abre a pasta de downloads", "abre a pasta no Windows"],
            ["lembre que eu prefiro respostas curtas", "guarda para sempre"],
            ["como está o computador?", "conta memória, disco e bateria"],
            ["analise o meu projeto em C:\\...", "chama o Claude e mostra o progresso"],
            ["quais tarefas estão pendentes", "lista a fila"],
            ["você está bem?", "faz o diagnóstico completo"],
            ["late", "late"],
        ],
        [70, 100],
    )


def conversando(pdf):
    pdf.titulo("4. Conversando com ela")

    pdf.subtitulo("4.1. Por texto")

    pdf.paragrafo(
        "Clique na Milk, escreva e aperte Enter. É o jeito que funciona sempre, "
        "com ou sem microfone."
    )

    pdf.subtitulo("4.2. Pelo botão do microfone")

    pdf.paragrafo(
        "O botão \"Falar\" grava sete segundos e transcreve o que você disse. "
        "Serve para um pedido rápido."
    )

    pdf.subtitulo("4.3. Chamando pelo nome (escuta contínua)")

    pdf.paragrafo(
        "No menu do botão direito, marque \"Escuta contínua\". A partir daí ela "
        "fica ouvindo a sala e atende quando a frase começa com o nome dela:"
    )

    pdf.codigo(
        "Milk, que horas são?\n"
        "Milk, abre o Chrome.\n"
        "Milk, analise o meu projeto."
    )

    pdf.paragrafo(
        "Depois que ela atende, você tem alguns segundos para continuar falando sem "
        "repetir o nome — como numa conversa normal. Fala que não começa com o nome "
        "dela é descartada e não aparece na conversa."
    )

    pdf.caixa(
        "Privacidade",
        "Com a escuta ligada, só os trechos em que alguém realmente falou são "
        "transcritos. O silêncio da sala não sai da máquina. Desligue a escuta "
        "quando não quiser ser ouvido — é a mesma opção do menu."
    )


def o_que_ela_faz(pdf):
    pdf.add_page()

    pdf.titulo("5. O que ela faz, em detalhe")

    pdf.subtitulo("5.1. Fila de tarefas")

    pdf.paragrafo(
        "Pedidos grandes viram tarefas. Se você pedir outra coisa enquanto ela "
        "trabalha, o pedido entra na fila e começa sozinho quando o anterior "
        "terminar. Dizer que é urgente muda a ordem."
    )

    pdf.tabela(
        ["Você diz", "Acontece"],
        [
            ["isso é urgente", "a tarefa passa na frente das outras"],
            ["quando puder, ...", "a tarefa vai para o fim da fila"],
            ["o que você está fazendo?", "ela conta a tarefa e o progresso"],
            ["quais tarefas estão pendentes", "lista a fila inteira"],
            ["pause / continue", "para e retoma a fila"],
            ["cancele essa tarefa", "encerra o que está rodando agora"],
            ["cancele a próxima / cancele tudo", "limpa a fila"],
            ["repita a última", "faz de novo o último pedido"],
            ["limpe as tarefas concluídas", "limpa o histórico"],
        ],
        [62, 108],
    )

    pdf.subtitulo("5.2. Memória")

    pdf.tabela(
        ["Você diz", "Acontece"],
        [
            ["lembre que ...", "ela guarda para sempre"],
            ["o que você sabe sobre mim?", "ela lista o que guardou"],
            ["esqueça o que eu falei sobre X", "ela apaga aquilo"],
            ["estou trabalhando no projeto X", "ela anota o projeto"],
            ["o que fizemos hoje / ontem", "ela consulta o histórico de tarefas"],
        ],
        [62, 108],
    )

    pdf.caixa(
        "Segredo não é guardado",
        "Se a frase tiver senha, token, chave ou cartão, ela recusa e explica. "
        "Isso não é opcional nem configurável."
    )

    pdf.subtitulo("5.3. Ações no Windows")

    pdf.tabela(
        ["Você diz", "Acontece"],
        [
            ["abre o Chrome / o bloco de notas", "abre o programa"],
            ["abre a pasta de downloads", "abre a pasta"],
            ["abre o site claude.ai", "abre no navegador"],
            ["procura o arquivo relatório", "procura nas suas pastas"],
            ["quanto de memória livre eu tenho", "responde na hora"],
            ["que programas estão abertos", "lista os que mais gastam memória"],
            ["crie uma pasta chamada X", "pergunta antes de criar"],
            ["apague o arquivo X", "pergunta antes de apagar"],
            ["roda o comando X no PowerShell", "pergunta antes de rodar"],
        ],
        [62, 108],
    )


def permissao(pdf):
    pdf.add_page()

    pdf.titulo("6. O que ela pode e o que ela não pode")

    pdf.paragrafo(
        "Toda ação que toca o seu computador passa por uma camada de permissão. "
        "São quatro níveis:"
    )

    pdf.tabela(
        ["Nível", "Exemplos", "O que acontece"],
        [
            [
                "Segura",
                "abrir programa, pasta, site; consultar",
                "acontece na hora",
            ],
            [
                "Sensível",
                "criar pasta, mover ou copiar arquivo, PowerShell",
                "ela pergunta e só faz depois do seu \"sim\"",
            ],
            [
                "Destrutiva",
                "apagar arquivo, encerrar programa",
                "ela avisa que apaga e espera o seu \"sim\"",
            ],
            [
                "Crítica",
                "formatar, mexer no Windows, apagar conta, desligar",
                "ela não faz, nem se você confirmar",
            ],
        ],
        [26, 74, 70],
    )

    pdf.paragrafo(
        "O caminho também pesa: apagar um arquivo na sua pasta de Downloads é "
        "destrutivo; o mesmo apagar dentro de C:\\Windows é crítico e não acontece."
    )

    pdf.subtitulo("Como confirmar")

    pdf.paragrafo(
        "Quando ela perguntar, responda \"sim\" (ou pode, claro, manda, ok) para "
        "fazer, e \"não\" (ou cancela, deixa, esquece) para desistir. Se você mudar "
        "de assunto, a ação é cancelada por segurança — um \"sim\" solto depois "
        "não vale. A pergunta também caduca em dois minutos."
    )


def modos(pdf):
    pdf.titulo("7. Modos de convivência")

    pdf.paragrafo(
        "No menu do botão direito você escolhe como ela se comporta. O trabalho "
        "continua acontecendo nos três; o que muda é o quanto ela aparece."
    )

    pdf.tabela(
        ["Modo", "O que muda"],
        [
            ["Normal", "ela fala, late e aparece"],
            ["Silencioso", "ela responde só por escrito"],
            ["Não perturbe", "ela não fala nem aparece sozinha"],
        ],
        [40, 130],
    )

    pdf.paragrafo(
        "O modo escolhido fica guardado: se você colocar em silêncio antes de uma "
        "reunião, ela continua em silêncio depois de reiniciar."
    )

    pdf.subtitulo("Outras opções do menu")

    pdf.marcador("Passear pela tela — ela caminha sozinha de vez em quando.")

    pdf.marcador("Escuta contínua — liga e desliga o \"diga Milk\".")

    pdf.marcador("Iniciar com o Windows — ela abre junto com o computador.")

    pdf.marcador("Diagnóstico — roda o Milk Doctor e conta o resultado.")

    pdf.marcador("Encerrar Milk — fecha o programa.")


def problemas(pdf):
    pdf.add_page()

    pdf.titulo("8. Quando alguma coisa não funciona")

    pdf.paragrafo(
        "Antes de qualquer outra coisa, peça o diagnóstico. Ele testa treze pontos "
        "e diz o que fazer com cada um que estiver ruim:"
    )

    pdf.codigo(
        "Milk.exe doutor          (ou Milk.bat doutor)\n"
        "\n"
        "ou, na conversa:  Milk, você está bem?"
    )

    pdf.subtitulo("8.1. Ela não escuta o que eu falo")

    pdf.paragrafo(
        "É o problema mais comum, e quase sempre é o microfone do Windows, não o "
        "programa. O diagnóstico mostra o nível captado. Confira, nesta ordem:"
    )

    pdf.passo(1, "O microfone certo está escolhido? Botão direito no ícone de som "
                 "→ Configurações de som → Entrada.")

    pdf.passo(2, "O volume da entrada está acima de zero e o microfone não está mudo?")

    pdf.passo(3, "Se for um fone Bluetooth, ele está ligado e conectado? "
                 "Fone desligado some da lista de aparelhos.")

    pdf.passo(4, "Rode o diagnóstico de novo. O pico precisa passar de 200.")

    pdf.paragrafo(
        "A Milk não usa obrigatoriamente o microfone padrão do Windows: em "
        "config\\settings.json, o campo microfone.dispositivo aceita um pedaço do "
        "nome do aparelho (por exemplo \"Headset\"), ou a palavra auto, que faz "
        "ela procurar sozinha uma entrada que esteja captando."
    )

    pdf.subtitulo("8.2. Ela não responde os pedidos grandes")

    pdf.paragrafo(
        "Esses vão para o Claude Code. Se o diagnóstico acusar problema na linha "
        "\"Claude\", abra um terminal e rode claude --version. Se não responder, é "
        "a instalação do Claude Code que precisa de atenção."
    )

    pdf.subtitulo("8.3. Ela não fala")

    pdf.paragrafo(
        "Veja se o modo não está em silencioso ou não perturbe, e se o botão da "
        "conversa está em \"Voz ligada\". A voz também precisa de internet."
    )

    pdf.subtitulo("8.4. Alguma coisa quebrou e eu quero ver o que foi")

    pdf.paragrafo(
        "Os registros ficam na pasta logs, ao lado do programa, separados por "
        "assunto: app, voice, claude, tasks, tools, system e errors. Senhas e "
        "tokens nunca são escritos ali."
    )


def arquivos(pdf):
    pdf.titulo("9. Os arquivos da Milk")

    pdf.tabela(
        ["Arquivo ou pasta", "O que é"],
        [
            ["Milk.exe", "o programa"],
            ["_internal", "as peças que o programa usa; não mexa"],
            ["assets", "a imagem dela e o som do latido"],
            ["config\\settings.json", "configurações que você pode editar"],
            ["logs", "registros do que aconteceu"],
            ["milk_tarefas.json", "a fila e o histórico de tarefas"],
            ["milk_memoria.json", "o que ela sabe e os projetos"],
            ["milk_conversa.json", "as últimas falas"],
            ["milk_pessoa.json", "com quem ela está falando"],
            ["milk_modo.json", "normal, silencioso ou não perturbe"],
            ["milk_posicao.json", "onde ela estava na tela"],
        ],
        [60, 110],
    )

    pdf.paragrafo(
        "Os arquivos .json podem ser apagados sem quebrar nada: ela recomeça "
        "aquela parte vazia. Apagar milk_memoria.json, por exemplo, é o mesmo que "
        "dizer \"esqueça tudo\"."
    )

    pdf.subtitulo("O que dá para configurar")

    pdf.paragrafo(
        "Abra config\\settings.json no Bloco de Notas. Os campos mais úteis:"
    )

    pdf.tabela(
        ["Campo", "Para quê"],
        [
            ["microfone.dispositivo", "qual microfone usar (ou auto)"],
            ["latido.volume", "volume do latido, de 0 a 1"],
            ["clima.cidade_padrao", "cidade quando você não disser qual"],
            ["moedas.origem_padrao", "moeda de origem nas conversões"],
        ],
        [55, 115],
    )

    pdf.caixa(
        "Nunca ponha senha aqui",
        "O settings.json é só para configuração. Nenhuma senha, token ou chave "
        "deve ser escrita nele."
    )


def direitos(pdf):
    pdf.add_page()

    pdf.titulo("10. Direitos autorais e uso")

    pdf.paragrafo(
        f"A Milk — programa, código-fonte, documentação e material que a acompanha "
        f"— é obra protegida por direito autoral, de titularidade exclusiva de "
        f"{AUTOR}, nos termos da Lei nº 9.610/1998 e da Lei nº 9.609/1998."
    )

    pdf.subtitulo("É proibido, sem autorização expressa e por escrito do autor:")

    pdf.marcador("copiar ou reproduzir, no todo ou em parte, por qualquer meio;")

    pdf.marcador(
        "distribuir, publicar, compartilhar, ceder, emprestar, alugar, vender ou "
        "transferir a terceiros, a qualquer título;"
    )

    pdf.marcador("modificar, adaptar, traduzir ou derivar obra nova;")

    pdf.marcador(
        "fazer engenharia reversa, descompilar ou desmontar o executável;"
    )

    pdf.marcador(
        "remover ou alterar este aviso e a identificação do autor."
    )

    pdf.ln(2)

    pdf.paragrafo(
        "O uso permitido é o pessoal e privado do autor e de quem ele "
        "expressamente autorizar. Nenhum outro direito é concedido."
    )

    pdf.paragrafo(
        "O programa é fornecido no estado em que se encontra, sem garantia de "
        "qualquer espécie. O autor não responde por danos decorrentes do uso ou da "
        "impossibilidade de uso."
    )

    pdf.ln(4)

    pdf.caixa(
        "Resumo",
        f"Este programa é de {AUTOR}. Não pode ser copiado nem repassado a "
        "ninguém. O texto completo está em LICENSE.txt, na pasta do programa."
    )

    pdf.ln(6)

    pdf.set_font("ui", "", 9)
    pdf.set_text_color(*CINZA)

    pdf.multi_cell(
        0,
        5,
        f"Manual da Milk, versão {VERSAO}. "
        f"© 2026 {AUTOR}. Todos os direitos reservados.",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )


def gerar(destino=None):
    pdf = Manual()

    capa(pdf)
    o_que_e(pdf)
    instalacao(pdf)
    primeiro_uso(pdf)
    conversando(pdf)
    o_que_ela_faz(pdf)
    permissao(pdf)
    modos(pdf)
    problemas(pdf)
    arquivos(pdf)
    direitos(pdf)

    caminho = Path(destino or (BASE / "Manual da Milk.pdf"))

    pdf.output(str(caminho))

    return caminho


if __name__ == "__main__":
    caminho = gerar(
        sys.argv[1] if len(sys.argv) > 1 else None
    )

    print("manual gerado:", caminho)
