"""
Fonte única da persona do assistente.

O system prompt era escrito à mão em cada ponto de chamada de
AIRouter.chat(), com texto diferente em cada um. A personalidade variava
conforme o usuário falasse pelo overlay, pelo orquestrador ou pelo script
de conversa. Este módulo centraliza o texto e permite editá-lo sem mexer
no código, via config/persona.txt.

Uso:
    from ai.persona import system_prompt, VOICE_HINT, CONTEXT_HINT

    reply = ai.chat(system_prompt(VOICE_HINT, CONTEXT_HINT), text, ...)

Tarefas que não são conversa não devem usar a persona: resumir e-mail ou
extrair JSON pedem obediência ao formato, não personalidade.
"""

from pathlib import Path

PERSONA_FILE = Path(__file__).resolve().parents[2] / "config" / "persona.txt"

# Usado quando config/persona.txt não existe ou não pode ser lido.
FALLBACK = (
    "Você é JARVIS, assistente pessoal em português brasileiro. "
    "Entenda a intenção por trás da fala, não apenas as palavras. "
    "Responda de forma natural, breve e útil, com personalidade e "
    "sem parecer robótico."
)

# Dicas de contexto, anexadas ao final da persona conforme o canal.
VOICE_HINT = (
    "O usuário está falando com você por voz: a resposta será lida em voz "
    "alta, então evite listas, markdown e frases longas."
)

CONTEXT_HINT = (
    "Use o contexto recente da conversa e não repita informações que o "
    "usuário já tem."
)

_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            _cache = PERSONA_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            _cache = FALLBACK
        if not _cache:
            _cache = FALLBACK
    return _cache


def system_prompt(*hints):
    """
    Retorna a persona completa, com dicas de contexto anexadas.

    hints: trechos extras (VOICE_HINT, CONTEXT_HINT ou texto livre).
    """
    parts = [_load()]
    parts.extend(h.strip() for h in hints if h and h.strip())
    return "\n\n".join(parts)


def reload():
    """Descarta o cache para reler config/persona.txt na próxima chamada."""
    global _cache
    _cache = None
