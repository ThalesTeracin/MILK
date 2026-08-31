class IntentParser:
    def detect(self,text):
        t=text.lower().strip()
        if any(x in t for x in ["dormir","modo sleep","va dormir"]): return {"intent":"sleep"}
        if any(x in t for x in ["encerrar","fechar milk","sair do milk"]): return {"intent":"exit"}
        if "status" in t and "sistema" in t: return {"intent":"system_status"}
        if "process" in t and any(x in t for x in ["memoria","pesad","consum"]): return {"intent":"top_processes"}
        apps={
            "calculadora":"calculadora","bloco de notas":"bloco de notas",
            "explorador":"explorador","gerenciador de tarefas":"gerenciador de tarefas",
            "configuracoes":"configurações","navegador":"navegador","paint":"paint"
        }
        if any(v in t for v in ["abrir","abra","iniciar","inicie"]):
            for key,target in apps.items():
                if key in t: return {"intent":"open_app","target":target}
        if any(v in t for v in ["crie","construa","desenvolva","planeje","analise","pesquise"]):
            return {"intent":"orchestrate","task":text}
        return {"intent":"unknown","text":text}
