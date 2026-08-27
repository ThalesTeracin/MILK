from memory.long_memory import LongMemory

class MemoryManager:
    def __init__(self):
        self.long = LongMemory()

    def user_message(self, text):
        self.long.add_message("user", text)

    def assistant_message(self, text):
        self.long.add_message("assistant", text)

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
        return key
