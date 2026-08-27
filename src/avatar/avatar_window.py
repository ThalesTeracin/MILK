import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk, ImageEnhance
from .runtime_state import read_state

ASSET=Path("assets/milk_avatar.png")

class AnimatedMilkAvatar:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title("MILK Avatar")
        self.root.geometry("540x720")
        self.root.configure(bg="#010203")
        self.root.attributes("-topmost", True)
        try:
            self.root.wm_attributes("-transparentcolor","#010203")
        except Exception:
            pass

        self.canvas=tk.Canvas(self.root,width=540,height=720,bg="#010203",highlightthickness=0)
        self.canvas.pack(fill="both",expand=True)

        self.base=None
        self.photo=None
        self.phase=0
        self._load()
        self._tick()

    def _load(self):
        if not ASSET.exists():
            return
        img=Image.open(ASSET).convert("RGBA")
        w,h=img.size
        crop=img.crop((int(w*.25),int(h*.08),int(w*.75),int(h*.88)))
        crop.thumbnail((500,650),Image.Resampling.LANCZOS)
        self.base=crop

    def _tick(self):
        self.phase=(self.phase+1)%80
        state=read_state()

        if self.base:
            brightness=0.96+0.06*(1-abs(40-self.phase)/40)
            if state.get("speaking"):
                brightness += 0.08
            if state.get("thinking"):
                brightness += 0.03

            img=ImageEnhance.Brightness(self.base).enhance(brightness)
            self.photo=ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(270,350,image=self.photo)

            # Visual lip-sync proxy: mouth glow pulses while TTS speaks.
            if state.get("speaking"):
                pulse=8 + (self.phase % 10)
                self.canvas.create_oval(
                    240-pulse, 370-pulse//3,
                    300+pulse, 385+pulse//3,
                    outline="#58eaff", width=2
                )

            label="FALANDO" if state.get("speaking") else "OUVINDO" if state.get("listening") else "PENSANDO" if state.get("thinking") else "PRONTA"
            self.canvas.create_text(
                270,35,text=f"MILK · {label}",
                fill="#67e8ff",font=("Segoe UI",16,"bold")
            )

        self.root.after(100,self._tick)

    def run(self):
        self.root.mainloop()

if __name__=="__main__":
    AnimatedMilkAvatar().run()
