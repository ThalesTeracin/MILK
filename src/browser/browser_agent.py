import os, re
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv
load_dotenv()

class BrowserAgent:
    def __init__(self):
        self.profile=Path(os.getenv("MILK_BROWSER_PROFILE","browser_profile"))
        self.profile.mkdir(parents=True,exist_ok=True)
        self.headless=os.getenv("MILK_BROWSER_HEADLESS","false").lower()=="true"
        self.playwright=None
        self.context=None
        self.page=None

    def start(self):
        if self.page:
            return
        from playwright.sync_api import sync_playwright
        self.playwright=sync_playwright().start()
        self.context=self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile),
            headless=self.headless,
            viewport={"width":1366,"height":768}
        )
        self.page=self.context.pages[0] if self.context.pages else self.context.new_page()

    def _ensure(self):
        if not self.page:
            self.start()

    def normalize_url(self,url):
        if not url:
            return None
        url=url.strip()
        if not re.match(r"^https?://",url,re.I):
            url="https://"+url
        return url

    def open_url(self,url):
        self._ensure()
        url=self.normalize_url(url)
        self.page.goto(url,wait_until="domcontentloaded",timeout=45000)
        return f"Abri {self.page.title() or url}."

    def search(self,query):
        self._ensure()
        url="https://www.google.com/search?q="+quote_plus(query or "")
        self.page.goto(url,wait_until="domcontentloaded",timeout=45000)
        return f"Pesquisei por {query}."

    def click_text(self,text):
        self._ensure()
        candidates=[
            self.page.get_by_role("button",name=text,exact=False),
            self.page.get_by_role("link",name=text,exact=False),
            self.page.get_by_text(text,exact=False)
        ]
        for loc in candidates:
            try:
                if loc.count() > 0:
                    loc.first.click(timeout=5000)
                    return f"Cliquei em {text}."
            except Exception:
                continue
        return f"Não encontrei {text} na página."

    def fill(self,field,value):
        self._ensure()
        names=[field, field.capitalize(), field.upper()]
        for name in names:
            for getter in [
                lambda: self.page.get_by_label(name,exact=False),
                lambda: self.page.get_by_placeholder(name,exact=False),
                lambda: self.page.get_by_role("textbox",name=name,exact=False)
            ]:
                try:
                    loc=getter()
                    if loc.count() > 0:
                        loc.first.fill(value)
                        return f"Preenchi {field}."
                except Exception:
                    continue
        # fallback first textbox
        try:
            tb=self.page.get_by_role("textbox")
            if tb.count() > 0:
                tb.first.fill(value)
                return f"Preenchi o campo de texto."
        except Exception:
            pass
        return f"Não encontrei o campo {field}."

    def submit(self):
        self._ensure()
        for name in ["Enviar","Entrar","Continuar","Submit","Login","Confirmar"]:
            try:
                btn=self.page.get_by_role("button",name=name,exact=False)
                if btn.count() > 0:
                    btn.first.click(timeout=5000)
                    return f"Acionei {name}."
            except Exception:
                continue
        try:
            self.page.keyboard.press("Enter")
            return "Enviei usando Enter."
        except Exception:
            return "Não consegui enviar."

    def read_page(self,limit=3500):
        self._ensure()
        try:
            text=self.page.locator("body").inner_text(timeout=7000)
            text=" ".join(text.split())
            return text[:limit]
        except Exception:
            return "Não consegui ler a página."

    def back(self):
        self._ensure()
        self.page.go_back(wait_until="domcontentloaded",timeout=30000)
        return "Voltei para a página anterior."

    def current_url(self):
        self._ensure()
        return self.page.url

    def close(self):
        if self.context:
            try: self.context.close()
            except Exception: pass
        if self.playwright:
            try: self.playwright.stop()
            except Exception: pass
        self.page=None; self.context=None; self.playwright=None
        return "Navegador fechado."
