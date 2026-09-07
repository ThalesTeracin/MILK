# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Janela de conversa da Milk."""

from PySide6.QtCore import QTimer

from PySide6.QtWidgets import QWidget

from milk.avatar.chat_ui import montar_interface
from milk.avatar.chat_tarefas import FilaDeTarefas

from milk.core.texto import (
    e_comando_parar,
    formatar_chat,
)

from milk.core.pessoa import (
    carregar_pessoa,
    salvar_pessoa,
    detectar_nome,
    identificar,
    e_dono,
)

from milk.core.config import MIC_SECONDS
from milk.voice.microfone import MicrofoneWorker
from milk.voice.escuta import tirar_o_nome
from milk.intelligence.claude_bridge import ClaudeWorker
from milk.intelligence.prompt import montar_prompt
from milk.intelligence.roteador import rotear
from milk.intelligence.ferramenta_worker import FerramentaWorker

from milk.core import eventos
from milk.tasks.gerente import gerente as gerente_do_processo
from milk.memory.memoria import memoria as memoria_do_processo
from milk.system.confirmacao import (
    confirmacao as confirmacao_do_processo,
    e_nao,
    e_sim,
)


PERGUNTA_NOME = "Com quem eu estou falando? 🐶"


class ChatBubble(FilaDeTarefas, QWidget):
    """A janela de conversa.

    O desenho está em `chat_ui.py`; a fila de tarefas e a resposta do
    Claude, em `chat_tarefas.py`. O que sobra aqui é quem está falando,
    o microfone, e a decisão do que fazer com cada pedido."""

    def __init__(
        self,
        milk,
        *,
        criar_claude_worker=ClaudeWorker,
        criar_microfone_worker=MicrofoneWorker,
        criar_ferramenta_worker=FerramentaWorker,
        roteador=rotear,
        montador_prompt=montar_prompt,
        ler_pessoa=carregar_pessoa,
        gravar_pessoa=salvar_pessoa,
        gerente_de_tarefas=None,
        memoria_da_milk=None,
        confirmacao_de_acao=None,
    ):
        """As dependências entram por argumento, mas todas têm o valor
        de sempre como padrão.

        `ChatBubble(milk)` continua funcionando igual. Os argumentos são
        somente-nomeados e servem para o teste trocar cada peça por um
        dublê, sem rede, sem thread e sem processo externo."""

        super().__init__()

        self.milk = milk

        self._criar_claude_worker = criar_claude_worker
        self._criar_microfone_worker = criar_microfone_worker
        self._criar_ferramenta_worker = criar_ferramenta_worker
        self._rotear = roteador
        self._montar_prompt = montador_prompt
        self._ler_pessoa = ler_pessoa
        self._gravar_pessoa = gravar_pessoa

        # A fila de tarefas. O padrão é a do processo, que já vem
        # do disco; o teste passa uma fila de mentira, só na memória.
        self._gerente = gerente_de_tarefas or gerente_do_processo()

        # O que ela lembra: fatos, projetos e a conversa de antes.
        self._memoria = memoria_da_milk or memoria_do_processo()

        # A acao de sistema que esta esperando um sim.
        self._confirmacao = (
            confirmacao_de_acao or confirmacao_do_processo()
        )

        self.claude_worker = None
        self.microfone_worker = None
        self.ferramenta_worker = None

        # A tarefa que o claude_worker está executando agora.
        self.tarefa_atual = None

        # Vira True quando entra fila; volta a False ao esvaziar.
        self.avisar_fim_da_fila = False

        # De onde veio o pedido: da caixa de texto ou do microfone.
        self.origem_do_pedido = "texto"

        # Cancelar uma tarefa é assunto do gerente; matar o processo
        # do Claude é assunto daqui. O barramento liga os dois sem
        # que um precise conhecer o outro.
        eventos.barramento.assinar(
            eventos.TAREFA_CANCELADA,
            self.quando_cancelam
        )

        # A conversa nao comeca do zero: as ultimas falas guardadas
        # voltam, entao ela sabe do que voces estavam falando.
        self.historico = [
            {
                "papel": fala.get("papel", "Usuário"),
                "texto": fala.get("texto", ""),
            }
            for fala in self._memoria.ultimas_falas()
        ]

        self.pessoa = self._ler_pessoa()
        self.aguardando_nome = self.pessoa is None

        self.progresso_texto = ""
        self.segundos = 0

        self.relogio = QTimer(self)
        self.relogio.setInterval(1000)
        self.relogio.timeout.connect(self.marcar_tempo)

        # O desenho da janela mora em chat_ui.py: aqui fica só
        # o que ela pensa e responde.
        montar_interface(self)

    # ========================================================
    # QUEM ESTÁ FALANDO
    # ========================================================

    def saudacao(self):
        if not self.pessoa:
            return f"Oi! {PERGUNTA_NOME}"

        if e_dono(self.pessoa):
            return f"Oi, {self.pessoa}. 🐾 Pode mandar."

        return (
            f"Oi, {self.pessoa}. Que bom te ver por aqui. "
            "Como eu posso ajudar?"
        )

    def registrar_pessoa(self, nome):
        """Guarda quem está falando e cumprimenta com um latido."""

        self.pessoa = nome
        self.aguardando_nome = False

        self._gravar_pessoa(nome)

        if e_dono(nome):
            recado = f"Oi, {nome}! 🐾 Que bom que é você."
        else:
            recado = (
                f"Prazer, {nome}. Fico feliz em te conhecer. "
                "Pode contar comigo."
            )

        self.chat.append(
            formatar_chat(
                "Milk",
                recado
            )
        )

        self.milk.latir()

        if self.milk.voz_ativa:
            self.milk.falar(recado)

    def trocar_pessoa(self, texto):
        """Alguém se apresentou no meio da conversa."""

        nome = detectar_nome(texto)

        if not nome:
            return False

        if self.pessoa and nome.lower() == self.pessoa.lower():
            return False

        self.registrar_pessoa(nome)

        return True

    # ========================================================
    # PROGRESSO
    # ========================================================

    def marcar_tempo(self):
        self.segundos += 1
        self.mostrar_progresso()

    def mostrar_progresso(self, texto=None):
        if texto:
            self.progresso_texto = texto

        base = (
            self.progresso_texto
            or
            "🧠 Pensando"
        )

        self.status.setText(
            f"{base} · {self.segundos}s"
        )

    def iniciar_progresso(self):
        self.progresso_texto = ""
        self.segundos = 0

        self.mostrar_progresso(
            "🧠 Pensando"
        )

        self.relogio.start()

    def parar_progresso(self):
        self.relogio.stop()

    # ========================================================
    # VOZ ON/OFF
    # ========================================================

    def alternar_voz(self):
        self.milk.voz_ativa = (
            not self.milk.voz_ativa
        )

        self.atualizar_botao_de_voz()

    def atualizar_botao_de_voz(self):
        """Deixa o botão igual ao estado real da voz.

        Quem chama é o próprio botão e a troca de modo pelo menu do
        avatar: os dois mexem na mesma coisa."""

        if self.milk.voz_ativa:
            self.botao_voz.setText(
                "🔊 Voz ligada"
            )
        else:
            self.botao_voz.setText(
                "🔇 Voz desligada"
            )

    # ========================================================
    # MICROFONE
    # ========================================================

    def ouvir(self):
        if (
            self.microfone_worker
            and
            self.microfone_worker.isRunning()
        ):
            self.status.setText(
                "Já estou ouvindo."
            )

            return

        self.milk.set_estado(
            "ouvindo"
        )

        # O botão grava sete segundos fixos. Enquanto isso a escuta
        # contínua fica quieta, senão a mesma fala seria transcrita
        # duas vezes, pelos dois caminhos.
        if hasattr(self.milk, "fechar_o_ouvido"):
            self.milk.fechar_o_ouvido(
                MIC_SECONDS + 3
            )

        self.botao_microfone.setEnabled(
            False
        )

        self.microfone_worker = self._criar_microfone_worker()

        self.microfone_worker.status.connect(
            self.status.setText
        )

        self.microfone_worker.texto_pronto.connect(
            self.receber_voz
        )

        self.microfone_worker.erro.connect(
            self.erro_microfone
        )

        self.microfone_worker.start()

    def receber_voz(self, texto):
        self.origem_do_pedido = "voz"

        self.botao_microfone.setEnabled(
            True
        )

        self.status.setText(
            f'Você disse: "{texto}"'
        )

        # O nome pode estar em qualquer lugar da frase ("que horas são,
        # Milk"). Quem sabe tirar é a escuta contínua, e é a mesma regra
        # aqui: o botão não pode entender menos do que o ouvido dela.
        texto_limpo = tirar_o_nome(texto)

        if not texto_limpo.strip():
            self.milk.falar(
                "Oi. Estou ouvindo."
            )

            self.status.setText(
                "Pode falar comigo."
            )

            return

        self.processar(
            texto_limpo
        )

    def erro_microfone(self, mensagem):
        self.botao_microfone.setEnabled(
            True
        )

        self.milk.set_estado(
            "parada"
        )

        self.status.setText(
            mensagem
        )

    # ========================================================
    # TEXTO DIGITADO
    # ========================================================

    def enviar_digitado(self):
        self.origem_do_pedido = "texto"

        texto = self.entrada.text().strip()

        if not texto:
            return

        self.entrada.clear()

        self.processar(
            texto
        )

    # ========================================================
    # PROCESSAR PEDIDO
    # ========================================================

    def processar(self, texto):
        if e_comando_parar(texto):
            self.milk.parar_fala()

            self.status.setText(
                "Parei de falar."
            )

            return

        # Ação sensível esperando resposta: "sim" faz, "não" cancela.
        if self.responder_confirmacao(texto):
            return

        if self.aguardando_nome:
            nome = identificar(texto)

            if nome:
                self.chat.append(
                    formatar_chat(
                        "Você",
                        texto
                    )
                )

                self.registrar_pessoa(nome)

                return

        elif self.trocar_pessoa(texto):
            self.chat.append(
                formatar_chat(
                    "Você",
                    texto
                )
            )

            return

        trabalhando = bool(
            self.claude_worker
            and
            self.claude_worker.isRunning()
        )

        consultando = bool(
            self.ferramenta_worker
            and
            self.ferramenta_worker.isRunning()
        )

        # Pergunta objetiva com resposta em uma API: resolve aqui.
        # Qualquer outra coisa continua sendo trabalho do Claude.
        decisao = self._rotear(texto, self.pessoa)

        if decisao:
            # Resposta local ("que horas são", "quais tarefas estão
            # pendentes") vale mesmo com o Claude trabalhando: ela não
            # mexe na barra de progresso nem nos botões.
            if decisao.local:
                self.usar_ferramenta(
                    texto,
                    decisao,
                    discreto=trabalhando
                )

                return

            if trabalhando:
                self.status.setText(
                    "Ainda estou no pedido anterior."
                )

                return

            if consultando:
                self.status.setText(
                    "Ainda estou naquela consulta."
                )

                return

            self.usar_ferramenta(
                texto,
                decisao
            )

            return

        # Sobrou trabalho, e trabalho vira tarefa: ganha identificador,
        # status e lugar na fila, e sobrevive a fechar a janela.
        tarefa = self._gerente.criar(
            texto,
            origem=self.origem_do_pedido
        )

        if trabalhando or consultando or self._gerente.pausada:
            self.avisar_fim_da_fila = True

            self.mostrar_pedido(texto)

            self.responder_direto(
                self.frase_da_fila(tarefa)
            )

            return

        self.iniciar_tarefa(tarefa)

    # ========================================================
    # FERRAMENTAS EXTERNAS
    # ========================================================

    def responder_confirmacao(self, texto):
        """Trata o "sim" ou o "não" de uma ação que está esperando.

        Devolve True quando a frase era a resposta da confirmação, e o
        pedido não precisa seguir para o roteador."""

        pendente = self._confirmacao.pendente()

        if pendente is None:
            return False

        if e_sim(texto):
            self.mostrar_pedido(texto)

            resultado = self._confirmacao.confirmar()

            self.responder_direto(
                resultado.texto
                if resultado is not None
                else "Aquilo já tinha passado do tempo. Pode pedir de novo."
            )

            return True

        if e_nao(texto):
            self.mostrar_pedido(texto)

            descricao = self._confirmacao.cancelar()

            self.responder_direto(
                f"Tudo bem, não fiz. ({descricao})"
                if descricao
                else "Tudo bem, deixei quieto."
            )

            return True

        # Qualquer outra coisa cancela por segurança: a pessoa mudou de
        # assunto, e um "sim" solto depois não pode valer para a ação.
        self._confirmacao.cancelar()

        return False

    def registrar_fala(self, papel, texto):
        """Guarda a fala no histórico da sessão e na memória em disco.

        A memória é o que faz ela lembrar da conversa depois de fechada.
        Falha ao gravar não pode atrapalhar a conversa em andamento."""

        self.historico.append({
            "papel": papel,
            "texto": texto,
        })

        try:
            self._memoria.registrar_fala(papel, texto)

        except Exception:
            pass

    def mostrar_pedido(self, texto):
        """Escreve o pedido na conversa, sem mexer em mais nada."""

        self.chat.append(
            formatar_chat(
                "Você",
                texto
            )
        )

    def preparar_pedido(self, texto, mostrar=True):
        """Mostra o pedido, trava os botões e liga o relógio."""

        if mostrar:
            self.mostrar_pedido(texto)

        self.milk.set_estado(
            "pensando"
        )

        self.botao_enviar.setEnabled(
            False
        )

        self.botao_microfone.setEnabled(
            False
        )

        self.iniciar_progresso()

    def usar_ferramenta(self, texto, decisao, discreto=False):
        """Consulta uma API em vez de gastar um pedido inteiro.

        `discreto` é para quando já existe trabalho em andamento: a
        resposta aparece e é falada, mas a barra de progresso e os
        botões continuam sendo do trabalho que está rodando."""

        if discreto:
            self.mostrar_pedido(texto)

        else:
            self.preparar_pedido(texto)

        self.registrar_fala(
            "Usuário",
            texto
        )

        if decisao.local:
            self.acao_local(
                decisao,
                discreto=discreto
            )

            return

        self.ferramenta_worker = self._criar_ferramenta_worker(
            decisao
        )

        self.ferramenta_worker.progresso.connect(
            self.mostrar_progresso
        )

        self.ferramenta_worker.sucesso.connect(
            self.receber_ferramenta
        )

        self.ferramenta_worker.erro.connect(
            self.receber_ferramenta
        )

        self.ferramenta_worker.start()

    def receber_ferramenta(self, resposta):
        """Sucesso e falha entram pelo mesmo caminho.

        A ferramenta já devolve uma frase amigável quando dá errado
        ("não achei esse CEP"), então a Milk fala isso normalmente, em
        vez de mostrar um aviso de erro técnico."""

        self.receber_claude(resposta)

        self.puxar_proxima()

    def acao_local(self, decisao, discreto=False):
        """Ação que resolve na hora, sem rede e sem thread.

        O latido é assim: `play()` volta na mesma hora e o som toca
        sozinho, então não há o que esperar nem o que travar."""

        if not discreto:
            self.mostrar_progresso(
                decisao.descricao
            )

        try:
            resultado = decisao.executar()

        except Exception as exc:
            self.responder(
                f"Não consegui fazer isso agora. ({exc})",
                falar=False,
                discreto=discreto
            )

            return

        self.responder(
            resultado.texto,
            falar=not decisao.silenciosa,
            discreto=discreto
        )

    def responder(self, texto, falar=True, discreto=False):
        """Resposta pronta: pelo caminho normal ou sem tocar na barra."""

        if discreto:
            self.responder_direto(
                texto,
                falar=falar
            )

            return

        self.receber_claude(
            texto,
            falar=falar
        )

    def responder_direto(self, texto, falar=True):
        """Escreve e fala, sem mexer no progresso nem nos botões.

        É o que permite responder "que horas são" no meio de uma tarefa
        longa sem bagunçar o estado do trabalho em andamento."""

        self.chat.append(
            formatar_chat(
                "Milk",
                texto
            )
        )

        self.registrar_fala(
            "Milk",
            texto
        )

        if falar and self.milk.voz_ativa:
            self.milk.falar(
                texto
            )
