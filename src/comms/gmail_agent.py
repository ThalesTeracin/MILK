from pathlib import Path
import base64
from email.message import EmailMessage

class GmailAgent:
    def __init__(self, token_path="data/google_token.json", credentials_path="config/google_credentials.json"):
        self.token_path=Path(token_path)
        self.credentials_path=Path(credentials_path)
        self.service=None

    def connect(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/calendar.readonly"
        ]

        creds=None
        if self.token_path.exists():
            creds=Credentials.from_authorized_user_file(str(self.token_path),scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError("config/google_credentials.json não encontrado.")
                flow=InstalledAppFlow.from_client_secrets_file(str(self.credentials_path),scopes)
                creds=flow.run_local_server(port=0)
            self.token_path.write_text(creds.to_json(),encoding="utf-8")

        self.service=build("gmail","v1",credentials=creds)
        return True

    def _ensure(self):
        if not self.service:
            self.connect()

    def search(self, query="in:inbox", limit=10):
        self._ensure()
        r=self.service.users().messages().list(userId="me",q=query,maxResults=limit).execute()
        out=[]
        for item in r.get("messages",[]):
            msg=self.service.users().messages().get(
                userId="me",id=item["id"],format="metadata",
                metadataHeaders=["From","Subject","Date"]
            ).execute()
            headers={h["name"]:h["value"] for h in msg.get("payload",{}).get("headers",[])}
            out.append({
                "id":item["id"],
                "from":headers.get("From",""),
                "subject":headers.get("Subject",""),
                "date":headers.get("Date",""),
                "snippet":msg.get("snippet","")
            })
        return out

    def create_draft(self,to,subject,body):
        self._ensure()
        m=EmailMessage()
        m["To"]=to
        m["Subject"]=subject
        m.set_content(body)
        raw=base64.urlsafe_b64encode(m.as_bytes()).decode()
        draft=self.service.users().drafts().create(
            userId="me",body={"message":{"raw":raw}}
        ).execute()
        return draft.get("id")
