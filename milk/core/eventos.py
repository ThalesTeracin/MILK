# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Barramento de eventos internos da Milk.

Um módulo avisa o que aconteceu sem precisar conhecer quem escuta. Quem
tem interesse assina o evento. É o que permite, por exemplo, o avatar
reagir a uma tarefa terminando sem que o gerente de tarefas saiba que o
avatar existe.

Não há thread aqui: `publicar()` chama os ouvintes na hora, na mesma
thread de quem publicou. Quem precisar cruzar de thread usa sinal do Qt,
como já acontece nos workers.

Um ouvinte que levanta exceção não derruba a publicação nem os outros
ouvintes. O barramento é um canal de aviso, não um caminho crítico.
"""


# Os nomes são os da especificação, em maiúsculas, para que apareçam
# iguais em qualquer log futuro.

TAREFA_CRIADA = "TASK_CREATED"
TAREFA_INICIADA = "TASK_STARTED"
TAREFA_PROGRESSO = "TASK_PROGRESS"
TAREFA_CONCLUIDA = "TASK_COMPLETED"
TAREFA_FALHOU = "TASK_FAILED"
TAREFA_CANCELADA = "TASK_CANCELLED"

VOZ_OUVINDO = "VOICE_LISTENING"
VOZ_RECONHECIDA = "VOICE_RECOGNIZED"

CLAUDE_INICIOU = "CLAUDE_STARTED"
CLAUDE_PENSANDO = "CLAUDE_THINKING"
CLAUDE_RESPONDEU = "CLAUDE_RESPONSE"
CLAUDE_ERRO = "CLAUDE_ERROR"

MILK_PARADA = "MILK_IDLE"
MILK_OUVINDO = "MILK_LISTENING"
MILK_TRABALHANDO = "MILK_WORKING"
MILK_FALANDO = "MILK_SPEAKING"
MILK_FELIZ = "MILK_HAPPY"
MILK_ERRO = "MILK_ERROR"


class Barramento:
    """Assinaturas por nome de evento.

    O mesmo ouvinte pode assinar vários eventos, e o mesmo evento pode
    ter vários ouvintes. A ordem de chamada é a ordem de assinatura."""

    def __init__(self):
        self.ouvintes = {}

    def assinar(self, evento, ouvinte):
        """Passa a receber esse evento. Devolve o próprio ouvinte."""

        fila = self.ouvintes.setdefault(evento, [])

        if ouvinte not in fila:
            fila.append(ouvinte)

        return ouvinte

    def desassinar(self, evento, ouvinte):
        """Para de receber. Desassinar duas vezes não é erro."""

        fila = self.ouvintes.get(evento)

        if not fila:
            return False

        if ouvinte not in fila:
            return False

        fila.remove(ouvinte)

        return True

    def publicar(self, evento, **dados):
        """Avisa quem assinou. Devolve quantos ouvintes foram chamados.

        Ninguém escutando é o caso normal, não é problema."""

        chamados = 0

        for ouvinte in list(self.ouvintes.get(evento, ())):
            try:
                ouvinte(evento, dados)

            except Exception:
                # Ouvinte quebrado não interrompe os outros nem quem
                # publicou. O aviso é secundário ao trabalho.
                continue

            chamados += 1

        return chamados

    def limpar(self):
        """Esquece todas as assinaturas. Usado no fim dos testes."""

        self.ouvintes.clear()


# Um barramento por processo. Quem quiser isolar (teste) cria o seu.
barramento = Barramento()
