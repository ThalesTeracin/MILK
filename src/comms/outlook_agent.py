from pathlib import Path
import json, requests
import msal

class OutlookAgent:
    def __init__(self, config_path="config/microsoft_oauth.json", cache_path="data/msal_cache.bin"):
        self.config_path=Path(config_path)
        self.cache_path=Path(cache_path)
        self.access_token=None

    def connect(self):
        if not self.config_path.exists():
            raise FileNotFoundError("config/microsoft_oauth.json não encontrado.")

        cfg=json.loads(self.config_path.read_text(encoding="utf-8"))
        cache=msal.SerializableTokenCache()
        if self.cache_path.exists():
            cache.deserialize(self.cache_path.read_text(encoding="utf-8"))

        app=msal.PublicClientApplication(
            cfg["client_id"],
            authority=cfg.get("authority","https://login.microsoftonline.com/common"),
            token_cache=cache
        )
        scopes=["Mail.Read","Mail.ReadWrite","Mail.Send","Calendars.Read","offline_access"]
        accounts=app.get_accounts()
        result=None
        if accounts:
            result=app.acquire_token_silent(scopes,account=accounts[0])
        if not result:
            flow=app.initiate_device_flow(scopes=scopes)
            if "user_code" not in flow:
                raise RuntimeError("Falha ao iniciar device flow.")
            print(flow["message"])
            result=app.acquire_token_by_device_flow(flow)

        self.cache_path.write_text(cache.serialize(),encoding="utf-8")

        if "access_token" not in result:
            raise RuntimeError(result.get("error_description","Falha no login Microsoft."))

        self.access_token=result["access_token"]
        return True

    def _headers(self):
        if not self.access_token:
            self.connect()
        return {"Authorization":f"Bearer {self.access_token}","Content-Type":"application/json"}

    def inbox(self, limit=10):
        url=f"https://graph.microsoft.com/v1.0/me/messages?$top={limit}&$orderby=receivedDateTime desc&$select=id,subject,from,receivedDateTime,bodyPreview"
        r=requests.get(url,headers=self._headers(),timeout=30)
        r.raise_for_status()
        return r.json().get("value",[])

    def create_draft(self,to,subject,body):
        payload={
            "subject":subject,
            "body":{"contentType":"Text","content":body},
            "toRecipients":[{"emailAddress":{"address":to}}]
        }
        r=requests.post(
            "https://graph.microsoft.com/v1.0/me/messages",
            headers=self._headers(),json=payload,timeout=30
        )
        r.raise_for_status()
        return r.json().get("id")
