from pathlib import Path
from datetime import datetime
import os, mss, mss.tools, pyautogui
from dotenv import load_dotenv
load_dotenv()

class ScreenAgent:
    def __init__(self,ai):
        self.ai=ai
        self.dir=Path(os.getenv("MILK_SCREENSHOTS_DIR","screenshots"))
        self.dir.mkdir(parents=True,exist_ok=True)
        pyautogui.FAILSAFE=True; pyautogui.PAUSE=0.15

    def capture(self):
        path=self.dir/f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        with mss.mss() as sct:
            monitor=sct.monitors[0]
            img=sct.grab(monitor)
            mss.tools.to_png(img.rgb,img.size,output=str(path))
        return str(path)
