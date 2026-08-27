from pathlib import Path
import json, datetime, requests

class CalendarAgent:
    def google_upcoming(self, credentials_path="config/google_credentials.json", token_path="data/google_token.json", limit=10):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        token=Path(token_path)
        creds=None

        if token.exists():
            creds=Credentials.from_authorized_user_file(str(token),scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow=InstalledAppFlow.from_client_secrets_file(credentials_path,scopes)
                creds=flow.run_local_server(port=0)
            token.write_text(creds.to_json(),encoding="utf-8")

        service=build("calendar","v3",credentials=creds)
        now=datetime.datetime.utcnow().isoformat()+"Z"
        events=service.events().list(
            calendarId="primary",timeMin=now,maxResults=limit,
            singleEvents=True,orderBy="startTime"
        ).execute().get("items",[])
        return events

    def outlook_upcoming(self, access_token, limit=10):
        start=datetime.datetime.utcnow().isoformat()+"Z"
        end=(datetime.datetime.utcnow()+datetime.timedelta(days=7)).isoformat()+"Z"
        url="https://graph.microsoft.com/v1.0/me/calendarView"
        params={"startDateTime":start,"endDateTime":end,"$top":limit,"$orderby":"start/dateTime"}
        headers={"Authorization":f"Bearer {access_token}"}
        r=requests.get(url,params=params,headers=headers,timeout=30)
        r.raise_for_status()
        return r.json().get("value",[])
