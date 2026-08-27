# INTEGRAÇÃO PARA O ORCHESTRATOR ATUAL
#
# 1) Importar:
# from documents.document_manager import DocumentManager
#
# 2) No __init__:
# self.documents = DocumentManager(self.ai)
#
# 3) Dentro de handle(), após obter intent/result:
#
# if intent=="document_create":
#     task=result.get("task") or text
#     self.say("Vou criar o arquivo.")
#     out=self.documents.create_from_request(task)
#     if out.get("ok"):
#         self.say(f"Arquivo criado em {out.get('path')}.")
#     else:
#         self.say(out.get("message","Não consegui criar o arquivo."))
#     return
