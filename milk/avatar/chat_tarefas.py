# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""A fila de tarefas da janela de conversa, e a resposta do Claude.

Um pedido que não tem resposta pronta vira tarefa: ganha identificador,
entra na fila e sobrevive a fechar a janela. Aqui está o que acontece
com ela do começo ao fim — entrar na fila, começar, avisar que demora,
terminar, falhar, ser cancelada, e puxar a próxima.

É um pedaço do `ChatBubble`, separado só para o `chat.py` não crescer
demais. Os atributos que ele usa (`milk`, `status`, `_gerente`,
`claude_worker`, `tarefa_atual`) nascem no `__init__` de lá."""

from milk.core.texto import formatar_chat
from milk.intelligence.rotas_conversa import espera_pelo_trabalho


class FilaDeTarefas:
    """Os métodos de fila e de resposta do Claude do ChatBubble."""

    # ========================================================
    # FILA DE TAREFAS
    # ========================================================

    def frase_da_fila(self, tarefa):
        """O que ela responde quando o pedido só entra na fila."""

        pendentes = self._gerente.pendentes()

        try:
            posicao = pendentes.index(tarefa) + 1

        except ValueError:
            posicao = len(pendentes)

        if self._gerente.pausada:
            return (
                f"Anotei: {tarefa.descricao}. "
                "A fila está pausada, é só me mandar continuar."
            )

        if posicao <= 1:
            return (
                f"Anotei: {tarefa.descricao}. "
                "Faço assim que terminar o que estou fazendo."
            )

        return (
            f"Anotei: {tarefa.descricao}. "
            f"Ficou em {posicao}º na fila."
        )

    def iniciar_tarefa(self, tarefa, mostrar_pedido=True):
        """Tira a tarefa da fila e põe o Claude para trabalhar nela."""

        if tarefa is None:
            return None

        anterior = self.claude_worker

        # O QThread que acabou de terminar ainda pode estar saindo do
        # run(). Trocar a referência antes disso derruba o programa.
        if anterior is not None and hasattr(anterior, "wait"):
            anterior.wait(3000)

        self._gerente.iniciar(tarefa)

        self.tarefa_atual = tarefa

        if mostrar_pedido:
            self.preparar_pedido(tarefa.prompt)

        else:
            self.chat.append(
                formatar_chat(
                    "Milk",
                    f"Terminei essa. Vou começar a próxima: "
                    f"{tarefa.descricao}."
                )
            )

            self.preparar_pedido(
                tarefa.prompt,
                mostrar=False
            )

        prompt = self._montar_prompt(
            tarefa.prompt,
            self.historico,
            self.pessoa
        )

        self.registrar_fala(
            "Usuário",
            tarefa.prompt
        )

        self.claude_worker = self._criar_claude_worker(
            prompt
        )

        self.claude_worker.progresso.connect(
            self.progresso_da_tarefa
        )

        self.claude_worker.sucesso.connect(
            self.tarefa_concluida
        )

        self.claude_worker.erro.connect(
            self.tarefa_falhou
        )

        self.claude_worker.start()

        self.avisar_que_vai_demorar()

        return tarefa

    def avisar_que_vai_demorar(self):
        """Um "já vou ver" enquanto o Claude trabalha.

        Medido nesta máquina: só abrir o processo do Claude custa seis
        segundos, e um pedido comum leva catorze. Quem pediu por voz
        não está olhando para a barra de progresso da janela — para essa
        pessoa a Milk simplesmente emudeceu. Uma frase curta aqui é a
        diferença entre ela estar pensando e ela ter travado.

        Só vale para pedido falado: quem digitou está vendo o progresso
        na tela e não precisa ser interrompido."""

        if self.origem_do_pedido != "voz":
            return

        self.milk.falar(
            espera_pelo_trabalho()
        )

    def progresso_da_tarefa(self, texto):
        """O estado real que veio do Claude, guardado e mostrado."""

        self._gerente.anotar_progresso(
            self.tarefa_atual,
            texto
        )

        self.mostrar_progresso(texto)

    def tarefa_concluida(self, resposta):
        tarefa = self.tarefa_atual

        self.tarefa_atual = None

        self._gerente.concluir(
            tarefa,
            resposta
        )

        self.receber_claude(resposta)

        self.puxar_proxima()

    def tarefa_falhou(self, mensagem):
        tarefa = self.tarefa_atual

        self.tarefa_atual = None

        # Tarefa que já terminou aqui é a que o usuário mandou cancelar:
        # o "erro" é só o processo do Claude morrendo, e ele já sabe.
        if tarefa is not None and tarefa.terminou():
            self.parar_progresso()

            self.botao_enviar.setEnabled(True)
            self.botao_microfone.setEnabled(True)

            self.status.setText(
                "Tarefa cancelada."
            )

            self.milk.set_estado(
                "parada"
            )

        else:
            self._gerente.falhar(
                tarefa,
                mensagem
            )

            self.erro_claude(mensagem)

        self.puxar_proxima()

    def puxar_proxima(self):
        """Começa a próxima da fila, se houver e se der.

        Quando não há próxima e acabou de terminar alguma coisa, ela
        avisa que terminou tudo — em vez de ficar em silêncio."""

        proxima = self._gerente.proxima()

        if proxima is None:
            self.avisar_que_acabou()

            return None

        return self.iniciar_tarefa(
            proxima,
            mostrar_pedido=False
        )

    def avisar_que_acabou(self):
        """"Terminei tudo." Só quando havia mesmo uma fila esperando."""

        if self._gerente.pausada:
            return False

        if self._gerente.em_andamento() is not None:
            return False

        if not self.avisar_fim_da_fila:
            return False

        self.avisar_fim_da_fila = False

        self.status.setText(
            "Terminei tudo. 🐾"
        )

        return True

    def quando_cancelam(self, evento, dados):
        """Chega pelo barramento quando alguém cancela uma tarefa.

        Se for a que está rodando, o processo do Claude é encerrado."""

        tarefa = dados.get("tarefa")

        if tarefa is None or self.tarefa_atual is None:
            return

        if tarefa.identificador != self.tarefa_atual.identificador:
            return

        if self.claude_worker and hasattr(self.claude_worker, "cancelar"):
            self.claude_worker.cancelar()

    # ========================================================
    # RESPOSTA DO CLAUDE
    # ========================================================

    def receber_claude(self, resposta, falar=True):
        """falar=False mostra a resposta sem mandar para a voz.

        Serve para o latido: o som já falou por ela, e a voz neural
        dizendo "au au" era justamente o que soava errado."""

        self.parar_progresso()

        self.chat.append(
            formatar_chat(
                "Milk",
                resposta
            )
        )

        self.registrar_fala(
            "Milk",
            resposta
        )

        self.botao_enviar.setEnabled(
            True
        )

        self.botao_microfone.setEnabled(
            True
        )

        self.entrada.setFocus()

        if falar and self.milk.voz_ativa:
            self.status.setText(
                "Falando... 🗣️"
            )

            self.milk.falar(
                resposta
            )
        else:
            self.status.setText(
                "Pronta. 🐾"
            )

            self.milk.set_estado(
                "parada"
            )

    def erro_claude(self, mensagem):
        self.parar_progresso()

        self.chat.append(
            formatar_chat(
                "⚠ Erro",
                mensagem
            )
        )

        self.botao_enviar.setEnabled(
            True
        )

        self.botao_microfone.setEnabled(
            True
        )

        self.status.setText(
            "Não consegui concluir."
        )

        self.milk.set_estado(
            "parada"
        )

