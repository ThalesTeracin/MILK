# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""O que a Milk lembra.

Dois arquivos, para não misturar coisas de vida útil diferente:

    milk_memoria.json   fatos e projetos — o que vale para sempre
    milk_conversa.json  as últimas falas — o que vale para hoje

O resumo que vai para o prompt é curto de propósito. Mandar tudo a cada
pedido gastaria contexto à toa e deixaria a resposta pior, não melhor.

**Segredo não entra.** Uma frase com senha, token ou chave é recusada
com uma explicação, e nada é gravado.
"""

import re
import datetime

from milk.core.arquivo import ler_json, gravar_json
from milk.core.config import CONVERSA_FILE, MEMORIA_FILE


# Quantas falas ficam guardadas da conversa.
FALAS_GUARDADAS = 40

# Quantas entram no resumo do prompt.
FALAS_NO_RESUMO = 6

FATOS_NO_RESUMO = 12


# Frase que carrega segredo não é memorizada.
SEGREDO = re.compile(
    r"\b(?:senha|password|token|api[\s_-]?key|chave\s+de\s+api|"
    r"chave\s+privada|credencial|cart[ãa]o\s+de\s+cr[ée]dito|"
    r"cvv|c[óo]digo\s+de\s+seguran[çc]a)\b",
    re.IGNORECASE
)


def agora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def agora_preciso():
    """Com microssegundos.

    Serve para ordenar coisas que acontecem no mesmo segundo, como
    anotar dois projetos seguidos."""

    return datetime.datetime.now().isoformat()


def hoje():
    return datetime.date.today().isoformat()


def tem_segredo(texto):
    return bool(
        SEGREDO.search(str(texto or ""))
    )


def normalizar(texto):
    return " ".join(
        str(texto or "").split()
    )


class Memoria:
    """As três camadas juntas, com o disco por trás.

    As funções de leitura e gravação entram pelo construtor, como no
    resto do projeto: nos testes a memória vive só na cabeça."""

    def __init__(
        self,
        *,
        ler=ler_json,
        gravar=gravar_json,
        arquivo_memoria=MEMORIA_FILE,
        arquivo_conversa=CONVERSA_FILE,
    ):
        self._ler = ler
        self._gravar = gravar

        self._arquivo_memoria = arquivo_memoria
        self._arquivo_conversa = arquivo_conversa

        guardado = self._ler(arquivo_memoria, None) or {}

        if not isinstance(guardado, dict):
            guardado = {}

        self.fatos = [
            fato
            for fato in guardado.get("fatos", [])
            if isinstance(fato, dict) and fato.get("texto")
        ]

        self.projetos = {
            nome: dados
            for nome, dados in (guardado.get("projetos") or {}).items()
            if isinstance(dados, dict)
        }

        conversa = self._ler(arquivo_conversa, None) or {}

        if not isinstance(conversa, dict):
            conversa = {}

        self.conversa = [
            fala
            for fala in conversa.get("falas", [])
            if isinstance(fala, dict) and fala.get("texto")
        ]

    # ========================================================
    # MEMÓRIA PERSISTENTE — FATOS
    # ========================================================

    def lembrar(self, texto, assunto=None, origem="conversa"):
        """Guarda um fato. Devolve o fato guardado, ou None se recusar."""

        limpo = normalizar(texto)

        if len(limpo) < 3:
            return None

        if tem_segredo(limpo):
            return None

        assunto = normalizar(assunto) or self.assunto_provavel(limpo)

        # Fato repetido não vira dois: o novo substitui o antigo.
        self.fatos = [
            fato
            for fato in self.fatos
            if normalizar(fato.get("texto")).lower() != limpo.lower()
        ]

        fato = {
            "assunto": assunto,
            "texto": limpo,
            "quando": agora(),
            "origem": origem,
        }

        self.fatos.append(fato)

        self._salvar_memoria()

        return fato

    def assunto_provavel(self, texto):
        """Um rótulo curto para o fato, tirado das primeiras palavras."""

        palavras = [
            palavra
            for palavra in normalizar(texto).split()
            if len(palavra) > 3
        ]

        return " ".join(palavras[:3]).lower() or "geral"

    def esquecer(self, termo):
        """Apaga os fatos que falam daquilo. Devolve quantos saíram."""

        alvo = normalizar(termo).lower()

        if not alvo:
            return 0

        antes = len(self.fatos)

        self.fatos = [
            fato
            for fato in self.fatos
            if alvo not in normalizar(fato.get("texto")).lower()
            and alvo not in normalizar(fato.get("assunto")).lower()
        ]

        quantos = antes - len(self.fatos)

        if quantos:
            self._salvar_memoria()

        return quantos

    def esquecer_tudo(self):
        quantos = len(self.fatos)

        self.fatos = []

        self._salvar_memoria()

        return quantos

    def buscar(self, termo):
        """Os fatos que falam daquele assunto."""

        alvo = normalizar(termo).lower()

        if not alvo:
            return []

        return [
            fato
            for fato in self.fatos
            if alvo in normalizar(fato.get("texto")).lower()
            or alvo in normalizar(fato.get("assunto")).lower()
        ]

    # ========================================================
    # MEMÓRIA DE PROJETOS
    # ========================================================

    def anotar_projeto(self, nome, nota=None, caminho=None):
        """Cria ou atualiza o que ela sabe de um projeto."""

        chave = normalizar(nome).lower()

        if not chave:
            return None

        projeto = self.projetos.get(chave) or {
            "nome": normalizar(nome),
            "notas": [],
            "caminho": "",
            "criado_em": agora(),
        }

        if nota and not tem_segredo(nota):
            projeto["notas"] = (projeto.get("notas") or [])[-9:] + [
                {
                    "texto": normalizar(nota),
                    "quando": agora(),
                }
            ]

        if caminho:
            projeto["caminho"] = str(caminho)

        projeto["ultima_vez"] = agora_preciso()

        self.projetos[chave] = projeto

        self._salvar_memoria()

        return projeto

    def projeto(self, nome):
        return self.projetos.get(
            normalizar(nome).lower()
        )

    def projeto_recente(self):
        """O último projeto tocado — é o 'aquele projeto de ontem'."""

        if not self.projetos:
            return None

        return max(
            self.projetos.values(),
            key=lambda dados: dados.get("ultima_vez", "")
        )

    # ========================================================
    # MEMÓRIA DE CURTO PRAZO — A CONVERSA
    # ========================================================

    def registrar_fala(self, papel, texto):
        """Guarda uma fala da conversa, cortando a lista no limite."""

        limpo = normalizar(texto)

        if not limpo:
            return None

        fala = {
            "papel": papel,
            "texto": limpo,
            "quando": agora(),
        }

        self.conversa.append(fala)

        if len(self.conversa) > FALAS_GUARDADAS:
            self.conversa = self.conversa[-FALAS_GUARDADAS:]

        self._salvar_conversa()

        return fala

    def ultimas_falas(self, quantas=FALAS_NO_RESUMO):
        return self.conversa[-quantas:]

    def falas_do_dia(self, dia=None):
        alvo = dia or hoje()

        return [
            fala
            for fala in self.conversa
            if str(fala.get("quando", "")).startswith(alvo)
        ]

    def limpar_conversa(self):
        quantas = len(self.conversa)

        self.conversa = []

        self._salvar_conversa()

        return quantas

    # ========================================================
    # O QUE VAI PARA O PROMPT
    # ========================================================

    def resumo(self):
        """Bloco curto de contexto. Vazio quando não há nada a dizer."""

        partes = []

        if self.fatos:
            linhas = [
                f"- {fato['texto']}"
                for fato in self.fatos[-FATOS_NO_RESUMO:]
            ]

            partes.append(
                "O QUE VOCÊ JÁ SABE:\n" + "\n".join(linhas)
            )

        recente = self.projeto_recente()

        if recente:
            linha = f"- Projeto mais recente: {recente['nome']}"

            if recente.get("caminho"):
                linha += f" (em {recente['caminho']})"

            notas = recente.get("notas") or []

            if notas:
                linha += f". Última anotação: {notas[-1]['texto']}"

            partes.append(
                "PROJETOS:\n" + linha
            )

        return "\n\n".join(partes)

    # ========================================================
    # INTERNO
    # ========================================================

    def _salvar_memoria(self):
        try:
            return self._gravar(
                self._arquivo_memoria,
                {
                    "fatos": self.fatos,
                    "projetos": self.projetos,
                },
            )

        except Exception:
            return False

    def _salvar_conversa(self):
        try:
            return self._gravar(
                self._arquivo_conversa,
                {
                    "falas": self.conversa,
                },
            )

        except Exception:
            return False


# Uma memória por processo, igual ao gerente de tarefas.
_memoria = None


def memoria():
    global _memoria

    if _memoria is None:
        _memoria = Memoria()

    return _memoria


def definir_memoria(nova):
    """Troca a memória do processo. Existe para os testes."""

    global _memoria

    _memoria = nova

    return _memoria
