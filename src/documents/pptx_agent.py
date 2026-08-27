from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt

class PptxAgent:
    def create(self, title, slides, output_path):
        path=Path(output_path)
        path.parent.mkdir(parents=True,exist_ok=True)

        prs=Presentation()

        # Title slide
        slide=prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text=title or "Apresentação"
        if len(slide.placeholders)>1:
            slide.placeholders[1].text="Gerado pela MILK"

        for item in slides or []:
            slide=prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text=item.get("title","Slide")
            tf=slide.placeholders[1].text_frame
            tf.clear()
            for i,line in enumerate(item.get("bullets",[])):
                p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
                p.text=str(line)
                p.font.size=Pt(20)

        prs.save(path)
        return str(path)
