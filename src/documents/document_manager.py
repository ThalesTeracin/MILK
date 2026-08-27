from pathlib import Path
import json, re, os
from documents.docx_agent import DocxAgent
from documents.pdf_agent import PdfAgent
from documents.spreadsheet_agent import SpreadsheetAgent
from documents.pptx_agent import PptxAgent

SYSTEM = """
Você é o Document Agent da MILK.
Entenda o pedido e retorne SOMENTE JSON válido.

Formato:
{
  "type":"docx|pdf|xlsx|pptx",
  "filename":"nome.ext",
  "title":"título",
  "body":"texto do documento ou null",
  "headers":["coluna1","coluna2"],
  "rows":[["a","b"],["c","d"]],
  "slides":[
    {"title":"Slide 1","bullets":["item 1","item 2"]}
  ]
}

Regras:
- gere conteúdo em português brasileiro;
- nome de arquivo simples;
- sem caminhos absolutos;
- para XLSX use headers e rows;
- para PPTX use slides;
- para DOCX/PDF use body;
- máximo 20 slides e máximo 200 linhas de planilha nesta fase.
"""

class DocumentManager:
    def __init__(self, ai, output_dir="output"):
        self.ai=ai
        self.output_dir=Path(output_dir)
        self.output_dir.mkdir(parents=True,exist_ok=True)
        self.docx=DocxAgent()
        self.pdf=PdfAgent()
        self.xlsx=SpreadsheetAgent()
        self.pptx=PptxAgent()

    def _safe_filename(self,name,ext):
        base=Path(name or f"documento.{ext}").name
        stem=re.sub(r"[^a-zA-Z0-9._ -]+","-",Path(base).stem).strip() or "documento"
        return f"{stem}.{ext}"

    def create_from_request(self, request):
        if not self.ai or not self.ai.enabled:
            return {"ok":False,"message":"AI Router não configurado."}

        spec=self.ai.ask_json(SYSTEM,request,max_tokens=1800)
        if not spec:
            return {"ok":False,"message":"Não consegui estruturar o documento."}

        typ=(spec.get("type") or "").lower()
        if typ not in {"docx","pdf","xlsx","pptx"}:
            return {"ok":False,"message":"Tipo de documento não suportado."}

        filename=self._safe_filename(spec.get("filename"),typ)
        path=self.output_dir/filename

        if typ=="docx":
            result=self.docx.create(spec.get("title"),spec.get("body"),path)
        elif typ=="pdf":
            result=self.pdf.create(spec.get("title"),spec.get("body"),path)
        elif typ=="xlsx":
            result=self.xlsx.create(
                spec.get("title"),
                spec.get("headers") or [],
                (spec.get("rows") or [])[:200],
                path
            )
        else:
            result=self.pptx.create(
                spec.get("title"),
                (spec.get("slides") or [])[:20],
                path
            )

        return {"ok":True,"type":typ,"path":result,"title":spec.get("title")}
