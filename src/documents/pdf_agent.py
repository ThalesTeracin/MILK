from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import cm

class PdfAgent:
    def create(self, title, body, output_path):
        path=Path(output_path)
        path.parent.mkdir(parents=True,exist_ok=True)

        styles=getSampleStyleSheet()
        story=[]
        story.append(Paragraph(title or "Documento",styles["Title"]))
        story.append(Spacer(1,0.5*cm))

        for block in (body or "").split("\n\n"):
            block=block.strip()
            if block:
                story.append(Paragraph(block.replace("\n","<br/>"),styles["BodyText"]))
                story.append(Spacer(1,0.25*cm))

        doc=SimpleDocTemplate(str(path),pagesize=A4,
                              rightMargin=2*cm,leftMargin=2*cm,
                              topMargin=2*cm,bottomMargin=2*cm)
        doc.build(story)
        return str(path)
