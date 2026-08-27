class Conclave:
    def __init__(self, ai_router):
        self.ai=ai_router
    def review(self, task, proposed_plan):
        if not self.ai or not self.ai.enabled:
            return {"approved":True,"summary":"Conclave local: sem IA externa."}
        system="""Você é um conclave com 3 papéis: crítico, advogado e sintetizador.
Revise o plano de modo curto. Retorne SOMENTE JSON:
{"approved":true/false,"risk":"baixo|medio|alto","summary":"texto curto"}"""
        return self.ai.ask_json(system, f"Tarefa: {task}\nPlano: {proposed_plan}") or {
            "approved":False,"risk":"medio","summary":"Sem resposta segura do conclave."
        }
