# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Ferramentas externas da Milk.

Cada API vive no seu próprio módulo e devolve sempre um `Resultado`.
Nenhuma ferramenta levanta exceção para fora: falha de rede vira
`Resultado(ok=False)` com uma frase em português.

Aqui ficam só o contrato compartilhado e o erro comum. Quem decide qual
ferramenta usar é milk/intelligence/roteador.py.
"""


class ErroFerramenta(Exception):
    """Falha já traduzida para uma frase que a Milk pode falar."""

    def __init__(self, mensagem, codigo=None):
        super().__init__(mensagem)

        self.mensagem = mensagem
        self.codigo = codigo


class Resultado:
    """Resposta de uma ferramenta.

    ok     — deu certo?
    texto  — frase pronta para aparecer no chat e ser falada
    dados  — o conteúdo cru, para quem quiser usar depois
    """

    def __init__(self, ok, texto, dados=None):
        self.ok = ok
        self.texto = texto
        self.dados = dados or {}

    def __repr__(self):
        estado = "ok" if self.ok else "falhou"

        return f"<Resultado {estado}: {self.texto[:60]}>"


def certo(texto, dados=None):
    return Resultado(
        True,
        texto,
        dados
    )


def falhou(texto):
    return Resultado(
        False,
        texto
    )
