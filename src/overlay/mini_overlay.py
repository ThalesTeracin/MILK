import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
from avatar.runtime_state import read_state

ASSET=Path("assets/milk_avatar.png")

class MilkMiniOverlay:
    def __init__(self):
        self.root=tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost",True)
        self.root.configure(bg="#010203")

        try:
            self.root.wm_attributes("-transparentcolor","#010203")
        except Exception:
            pass

        w,h=220,280
        sw=self.root.winfo_screenwidth()
        sh=self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{sw-w-20}+{sh-h-70}")

        self.canvas=tk.Canvas(self.root,width=w,height=h,bg="#010203",highlightthickness=0)
        self.canvas.pack(fill="both",expand=True)

        self.photo=None
        if ASSET.exists():
            img=Image.open(ASSET).convert("RGBA")
            iw,ih=img.size
            img=img.crop((int(iw*.29),int(ih*.10),int(iw*.71),int(ih*.78)))
            img.thumbnail((205,240),Image.Resampling.LANCZOS)
            self.photo=ImageTk.PhotoImage(img)

        self.root.bind("<Button-1>", self._drag_start)
        self.root.bind("<B1-Motion>", self._drag)
        self.root.bind("<Double-Button-1>", lambda e:self.root.withdraw())

        self._tick()

    def _drag_start(self,e):
        self._x=e.x
        self._y=e.y

    def _drag(self,e):
        x=self.root.winfo_x()+e.x-self._x
        y=self.root.winfo_y()+e.y-self._y
        self.root.geometry(f"+{x}+{y}")

    def _tick(self):
        self.canvas.delete("all")
        if self.photo:
            self.canvas.create_image(110,135,image=self.photo)

        s=read_state()
        label="FALANDO" if s.get("speaking") else "OUVINDO" if s.get("listening") else "PENSANDO" if s.get("thinking") else "PRONTA"
        self.canvas.create_text(110,18,text=f"MILK · {label}",fill="#67e8ff",font=("Segoe UI",10,"bold"))
        self.root.after(150,self._tick)

    def run(self):
        self.root.mainloop()

if __name__=="__main__":
    MilkMiniOverlay().run()
