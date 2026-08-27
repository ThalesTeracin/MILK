from comms.gmail_agent import GmailAgent
from comms.outlook_agent import OutlookAgent

class CommsManager:
    def __init__(self):
        self.gmail=GmailAgent()
        self.outlook=OutlookAgent()

    def summarize_gmail(self, ai, query="newer_than:1d", limit=8):
        msgs=self.gmail.search(query=query,limit=limit)
        if not msgs:
            return "Não encontrei mensagens."
        text="\n".join(
            f"De: {m['from']}\nAssunto: {m['subject']}\nTrecho: {m['snippet']}"
            for m in msgs
        )
        if ai and ai.enabled:
            return ai.chat(
                "Resuma estes emails em português brasileiro. Destaque urgentes e ações necessárias.",
                text,max_tokens=350
            )
        return text[:1800]

    def summarize_outlook(self, ai, limit=8):
        msgs=self.outlook.inbox(limit=limit)
        if not msgs:
            return "Não encontrei mensagens."
        text="\n".join(
            f"De: {m.get('from',{}).get('emailAddress',{}).get('address','')}\n"
            f"Assunto: {m.get('subject','')}\nTrecho: {m.get('bodyPreview','')}"
            for m in msgs
        )
        if ai and ai.enabled:
            return ai.chat(
                "Resuma estes emails em português brasileiro. Destaque urgentes e ações necessárias.",
                text,max_tokens=350
            )
        return text[:1800]
