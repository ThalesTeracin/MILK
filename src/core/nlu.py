import re
import unicodedata

class HybridNLU:
    def __init__(self, ai=None):
        self.ai=ai

    def _norm(self,text):
        t=unicodedata.normalize("NFD",str(text).lower())
        t="".join(c for c in t if unicodedata.category(c)!="Mn")
        t=re.sub(r"[^\w\s]"," ",t)
        return re.sub(r"\s+"," ",t).strip()

    def interpret(self,text):
        original=str(text)
        t=self._norm(original)

        # Local commands remain fast and token-free
        if "boa tarde" in t:
            return {"intent":"chat","reply":"Boa tarde! Estou aqui com você."}
        if "bom dia" in t:
            return {"intent":"chat","reply":"Bom dia! Pode falar comigo."}
        if "boa noite" in t:
            return {"intent":"chat","reply":"Boa noite! Estou ouvindo."}

        if "calcul" in t or "fazer conta" in t or "fazer contas" in t:
            return {"intent":"open_app","target":"calculadora"}

        if "bloco de notas" in t or "notepad" in t:
            return {"intent":"open_app","target":"bloco de notas"}

        if "painel de controle" in t:
            return {"intent":"open_app","target":"painel de controle"}

        if "gerenciador de tarefas" in t or "task manager" in t:
            return {"intent":"open_app","target":"gerenciador de tarefas"}

        if "configuracoes" in t or "configuracao do windows" in t:
            return {"intent":"open_app","target":"configurações"}

        if "explorador" in t or "meus arquivos" in t or "minhas pastas" in t:
            return {"intent":"open_app","target":"explorador"}

        if any(x in t for x in [
            "como esta meu computador","status do sistema",
            "computador pesado","pc pesado","computador lento"
        ]):
            return {"intent":"system_status"}

        if any(x in t for x in [
            "tchau milk","encerrar milk","parar por hoje","fechar milk"
        ]):
            return {"intent":"exit"}

        # Anything else goes to AI when available
        if self.ai and getattr(self.ai,"enabled",False):
            system = """
Você interpreta pedidos naturais para a MILK.
Retorne JSON:
{
 "intent":"open_app|system_status|top_processes|web_search|chat|unknown",
 "target":"calculadora|bloco de notas|explorador|gerenciador de tarefas|configurações|navegador|paint|painel de controle|serviços|powershell|prompt de comando|null",
 "query":"texto ou null",
 "reply":"resposta curta ou null"
}
Se o usuário estiver apenas conversando ou perguntando algo, use "chat".
"""
            out=self.ai.ask_json(system, original, max_tokens=220)
            if out:
                return out

            # Provider exists but the request failed: do not lie that it is "not configured"
            return {
                "intent":"chat",
                "reply":None,
                "_ai_failed":True
            }

        return {
            "intent":"chat",
            "reply":"Meu cérebro de inteligência artificial ainda não está configurado."
        }

# Bug pré-existente encontrado durante a Fase 2: core/orchestrator.py importa
# "NaturalLanguageInterpreter" deste módulo, mas apenas HybridNLU estava
# definida aqui -- MilkCore nunca conseguia ser instanciado (ImportError).
# Alias mínimo para destravar; não altera nenhum comportamento de NLU.
NaturalLanguageInterpreter = HybridNLU
