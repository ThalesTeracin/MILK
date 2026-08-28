from memory.long_memory import LongMemory

class MemoryManager:
    def __init__(self):
        self.long = LongMemory()
        self.active_project_key = None

    def user_message(self, text):
        self.long.add_message("user", text, project_key=self.active_project_key)

    def assistant_message(self, text):
        self.long.add_message("assistant", text, project_key=self.active_project_key)

    def context_for_ai(self):
        return self.long.recent_messages(limit=8)

    def remember_project_from_build(self, build):
        if not build or not build.get("project"):
            return None
        path = build.get("project")
        name = path.replace("\\","/").rstrip("/").split("/")[-1]
        key = self.long.remember_project(
            name=name,
            path=path,
            status="active",
            summary=build.get("summary")
        )
        self.long.add_project_event(
            key,
            "build",
            "Projeto criado/atualizado pelo Coding Agent."
        )
        # Passa a marcar as próximas mensagens como pertencentes a este projeto.
        self.active_project_key = key
        return key
