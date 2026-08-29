"""
Movimento do avatar: o que faz a MILK parecer alguem ali, e nao uma foto.

Ate a fase 33 o avatar era uma PNG parada com o brilho oscilando. Nenhum
deslocamento, nenhuma mudanca de tamanho -- uma foto acesa e apagada.

O movimento sai de funcoes puras do tempo. Sem estado nenhum: o mesmo
instante da sempre o mesmo quadro. Isso importa porque o laco de desenho
pode perder um quadro (o Tk esta ocupado, a maquina engasgou) e, com
estado acumulado, a animacao pularia de fase e daria um tranco na tela.
Puro, um quadro perdido some sem deixar rastro.

Tres movimentos somados, todos suaves:

- Respiracao: a escala sobe e desce devagar, e o corpo acompanha com um
  deslocamento vertical pequeno. E o movimento que carrega a sensacao de
  estar vivo; o resto so tira a impressao de laco.
- Balanco: deriva horizontal lenta, como peso mudando de pe.
- Tremor: soma de senos de amplitude minima, so para nunca haver dois
  instantes exatamente iguais.

Os periodos sao incomensuraveis de proposito. Se fossem multiplos, o
conjunto voltaria ao mesmo ponto o tempo todo e o olho reconheceria o
laco em segundos -- que e justamente o que se quer evitar.
"""

import math

# (periodo da respiracao, amplitude da escala, amplitude do balanco, brilho)
#
# Parada respira devagar e fundo, como alguem em repouso. Ouvindo fica um
# pouco mais atenta. Pensando quase segura o folego. Falando e a mais
# ativa: e quando a pessoa do outro lado esta olhando de verdade.
PERFIS = {
    "idle":      (5.1, 0.010, 3.4, 0.055),
    "listening": (4.3, 0.012, 2.8, 0.070),
    "thinking":  (3.3, 0.008, 1.9, 0.045),
    "speaking":  (2.3, 0.020, 2.2, 0.110),
}
PERFIL_PADRAO = PERFIS["idle"]
ATIVIDADES_CONHECIDAS = frozenset(PERFIS) | {"desconhecida"}

# Periodos do balanco e da deriva, em segundos. Primos entre si em
# relacao ao da respiracao para o conjunto nao fechar ciclo.
PERIODO_BALANCO = 11.3
PERIODO_DERIVA = 7.9

# O tremor e tao pequeno que nao se ve sozinho; ele so impede que dois
# instantes coincidam.
TREMOR = ((0.37, 0.21), (0.91, 0.13), (2.17, 0.07))


def _respiracao(t, periodo):
    """0 a 1, com a subida mais lenta que a descida, como o folego."""
    fase = (t / periodo) % 1.0
    return 0.5 - 0.5 * math.cos(2 * math.pi * fase)


def _tremor(t, semente):
    return sum(a * math.sin(2 * math.pi * f * t + semente) for f, a in TREMOR)


def quadro(t, atividade):
    """
    Estado do desenho no instante `t`, em segundos.

    Devolve escala (multiplicador do tamanho), dx e dy (deslocamento em
    pixels a partir da posicao de repouso) e brilho (multiplicador).
    """
    periodo, amplitude, balanco, brilho = PERFIS.get(atividade, PERFIL_PADRAO)

    folego = _respiracao(t, periodo)

    # Inspirar cresce e sobe junto: o peito enche e o corpo acompanha.
    escala = 1.0 + amplitude * folego
    dy = -1.9 * amplitude / 0.012 * folego

    dx = balanco * math.sin(2 * math.pi * t / PERIODO_BALANCO)
    dy += 1.5 * math.sin(2 * math.pi * t / PERIODO_DERIVA)

    dx += _tremor(t, 0.0)
    dy += _tremor(t, 1.7)

    return {
        "escala": float(escala),
        "dx": float(dx),
        "dy": float(dy),
        "brilho": float(0.965 + brilho * folego),
    }
