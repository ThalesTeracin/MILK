from datetime import datetime
from devops.devops_manager import DevOpsManager
from voice.listener import NaturalVoiceListener
from voice.speaker import NaturalSpeaker
from agents.windows_agent import WindowsAgent
from ai.router import AIRouter
from ai.persona import system_prompt, VOICE_HINT, CONTEXT_HINT
from core.nlu import NaturalLanguageInterpreter
from browser.browser_agent import BrowserAgent
from vision.screen_agent import ScreenAgent
from coding.coding_agent_v2 import CodingAgentV2
from memory.memory_manager import MemoryManager
from security.permission_manager import PermissionManager
from knowledge.knowledge_base import KnowledgeBase

# Alvos de open_app considerados sensíveis, mapeados para ações do perfil
# de permissão em config/permission_profiles.json. "prompt de comando" e
# "powershell" abrem um shell interativo (equivalente a arbitrary_shell,
# negado por padrão em todos os perfis); "serviços" abre um console MMC
# administrativo (open_admin).
SENSITIVE_OPEN_TARGETS = {
    "prompt de comando": "arbitrary_shell",
    "powershell": "arbitrary_shell",
    "serviços": "open_admin",
    "servicos": "open_admin",
}

class MilkCore:
    def __init__(self):
        self.state="sleep"
        self.running=True
        self.devops = DevOpsManager()
        self.voice=NaturalVoiceListener()
        self.speaker=NaturalSpeaker()
        self.windows=WindowsAgent()
        self.ai=AIRouter()
        self.nlu=NaturalLanguageInterpreter(self.ai)
        self.browser=BrowserAgent()
        self.screen=ScreenAgent(self.ai)
        self.coder=CodingAgentV2(self.ai,max_repair_loops=2)
        self.memory=MemoryManager()
        # Base de conhecimento local (data/knowledge/milk_knowledge.db),
        # alimentada por Importar_Conhecimento.py. Existia desde a Fase 28
        # mas nunca era consultada nas respostas reais da MILK (Fase 6,
        # item 5) -- só em scripts de teste avulsos.
        self.knowledge=KnowledgeBase()
        # Perfil padrão "balanced": mantém o comportamento atual (a maioria
        # das ações roda direto), mas passa a negar de verdade arbitrary_shell
        # e a exigir confirmação para ações marcadas em config/permission_profiles.json.
        self.permissions=PermissionManager(profile="balanced")
        # Ação adiada aguardando confirmação verbal ("confirmar"). Pode vir
        # do navegador ou de um gate de permissão (open_app, coding_task, etc.).
        self._pending_confirmation=None
        # Estado fino de atividade (Fase 6, item 4), consumido pelo overlay
        # em src/presence/unified_app.py para animação reativa
        # (ouvindo/pensando/falando). "listening"/"thinking" são setados
        # pelo loop de escuta do UnifiedApp; "speaking"/"idle" aqui em say().
        self.activity="idle"

    def say(self,text):
        self.activity="speaking"
        try:
            self.speaker.say(text)
        finally:
            self.activity="idle" if self.state=="sleep" else "listening"
        try:
            self.memory.assistant_message(text)
        except Exception:
            pass

    def _system_with_knowledge(self,prompt_base,query):
        """
        Acrescenta trechos relevantes de data/knowledge (RAG local via
        KnowledgeBase.build_context) ao prompt de sistema, quando existir
        algum documento com pontuação de relevância > 0 para a pergunta.
        Silenciosamente ignora falhas (banco vazio/corrompido não deve
        derrubar uma resposta de chat).

        O parâmetro não se chama system_prompt para não sombrear a função
        de mesmo nome importada de ai.persona.
        """
        try:
            ctx=self.knowledge.build_context(query,top_k=3)
        except Exception:
            return prompt_base
        if not ctx.get("context"):
            return prompt_base
        return (
            prompt_base
            + "\n\nUse as informações a seguir se forem relevantes para "
            "responder. Não mencione que vieram de uma base de dados, "
            "apenas responda naturalmente:\n" + ctx["context"]
        )

    def handle(self,text):
        if not text:
            return

        print("Você disse:",text)

        try:
            self.memory.user_message(text)
        except Exception:
            pass

        low=text.lower().strip()

        if self.state=="sleep":
            if "milk" in low:
                self.state="ready"
                rest=low.replace("milk","",1).strip(" ,.-")
                if not rest:
                    self.say("Estou ouvindo.")
                    return
                text=rest
            else:
                return

        # comandos locais de memória
        if "quais projetos" in low or "meus projetos" in low:
            projects=self.memory.long.list_projects(limit=8)
            if not projects:
                self.say("Ainda não tenho projetos registrados na memória longa.")
            else:
                names=", ".join(p["name"] for p in projects)
                self.say(f"Os projetos mais recentes são: {names}.")
            return

        if "status da memória" in low or "status da memoria" in low:
            st=self.memory.long.stats()
            self.say(
                f"Tenho {st['conversations']} mensagens, "
                f"{st['projects']} projetos, "
                f"{st['decisions']} decisões e "
                f"{st['errors']} erros registrados."
            )
            return

        # confirmação de ação adiada (navegador ou gate de permissão)
        if low in ["confirmar","confirmo","pode enviar","confirmar envio"]:
            pending=self._pending_confirmation
            if pending:
                self._pending_confirmation=None
                try:
                    pending["run"]()
                except Exception as e:
                    self.say(f"Não consegui concluir a ação confirmada. {e}")
                return

        result=self.nlu.interpret(text)
        intent=result.get("intent","unknown")

        if intent=="sleep":
            self.state="sleep"
            self.say("Tudo bem. Vou ficar em espera.")
            return

        if intent=="exit":
            try:
                self.browser.close()
            except Exception:
                pass
            self.say("Certo. Encerrando por agora.")
            self.running=False
            return

        if intent=="open_app":
            target=result.get("target")
            action=SENSITIVE_OPEN_TARGETS.get((target or "").lower().strip())
            if action:
                check=self.permissions.check(action)
                if not check["allowed"]:
                    self.say(f"Não posso fazer isso. {check['reason']}")
                    return
                if check["confirm"]:
                    self._pending_confirmation={"run": lambda t=target: self.say(self.windows.open_target(t))}
                    self.say(f"Isso requer confirmação. Diga confirmar para continuar.")
                    return
            self.say(self.windows.open_target(target))
            return

        if intent=="system_status":
            self.say(self.windows.system_status())
            return

        if intent=="top_processes":
            self.say(self.windows.top_processes())
            return

        if intent=="coding_task":
            task=result.get("task") or text

            def _run_coding_task():
                self.say("Vou criar, validar e tentar corrigir automaticamente.")
                build=self.coder.build_and_repair(task)
                print("[CODING V2]",build)

                if build.get("project"):
                    try:
                        self.memory.remember_project_from_build(build)
                    except Exception:
                        pass

                if build.get("ok"):
                    self.say(f"Projeto pronto em {build.get('project')}. Os testes e a validação passaram.")
                else:
                    if build.get("project"):
                        self.say(f"Criei o projeto em {build.get('project')}, mas ainda restaram erros para revisar.")
                    else:
                        self.say(build.get("message","Não consegui concluir o projeto."))

            check=self.permissions.check("write_file")
            if not check["allowed"]:
                self.say(f"Não posso criar ou alterar arquivos agora. {check['reason']}")
                return
            if check["confirm"]:
                self._pending_confirmation={"run": _run_coding_task}
                self.say("Essa ação vai criar ou alterar arquivos em disco. Diga confirmar para continuar.")
                return
            _run_coding_task()
            return

        if intent=="browser_open":
            url=result.get("url") or result.get("target")
            if not url:
                self.say("Qual site você quer abrir?")
                return
            self.say(self.browser.open_url(url))
            return

        if intent=="browser_search":
            query=result.get("query") or result.get("task") or result.get("text")
            self.say(self.browser.search(query))
            return

        if intent=="browser_click_text":
            self.say(self.browser.click_text(result.get("text") or result.get("target")))
            return

        if intent=="browser_fill":
            self.say(self.browser.fill(
                result.get("field") or "campo",
                result.get("value") or result.get("text") or ""
            ))
            return

        if intent=="browser_submit":
            self._pending_confirmation={"run": lambda: self.say(self.browser.submit())}
            self.say("Essa ação pode enviar dados. Diga confirmar para continuar.")
            return

        if intent=="browser_read":
            body=self.browser.read_page()
            if self.ai.enabled:
                summary=self.ai.chat(
                    "Resuma esta página em português brasileiro, no máximo 5 frases.",
                    body,
                    history=self.memory.context_for_ai(),
                    max_tokens=220
                )
                self.say(summary or body[:700])
            else:
                self.say(body[:700])
            return

        if intent=="browser_back":
            self.say(self.browser.back())
            return

        if intent=="browser_close":
            self.say(self.browser.close())
            return

        if intent=="chat":
            reply=result.get("reply")
            if not reply and self.ai.enabled:
                system=self._system_with_knowledge(
                    system_prompt(VOICE_HINT, CONTEXT_HINT),
                    text
                )
                reply=self.ai.chat(
                    system,
                    text,
                    history=self.memory.context_for_ai(),
                    max_tokens=320
                )
            self.say(reply or "Não consegui responder agora.")
            return

        if self.ai.enabled:
            system=self._system_with_knowledge(
                system_prompt(VOICE_HINT, CONTEXT_HINT),
                text
            )
            reply=self.ai.chat(
                system,
                text,
                history=self.memory.context_for_ai(),
                max_tokens=320
            )
            self.say(reply or "Não consegui interpretar esse pedido agora.")
        else:
            self.say("O roteador de inteligência artificial ainda não está configurado.")

    def start(self):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] MILK Fase 16 iniciado.")
        print("Memória longa SQLite + contexto compacto.")
        print("Provedores:",self.ai.status())
        print("Diga MILK uma vez. Depois fale normalmente.")
        try:
            while self.running:
                heard=self.voice.listen()
                if heard:
                    self.handle(heard)
        except KeyboardInterrupt:
            try:
                self.browser.close()
            except Exception:
                pass
            try:
                self.memory.long.close()
            except Exception:
                pass
            print("\nMILK encerrado.")
