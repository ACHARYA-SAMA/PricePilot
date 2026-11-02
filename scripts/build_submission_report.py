"""Build the submission DOCX from the reviewed project report source."""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/submission/PricePilot_Project_Documentation.md"
OUT = ROOT / "output/submission"
ASSETS = OUT / "assets"
OUT.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)


def architecture():
    im = Image.new("RGB", (1800, 690), "white")
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 29)
    bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 31)
    boxes = [
        (40, 60, 550, 230, "React interface", "Inputs  |  State  |  Charts"),
        (645, 60, 1155, 230, "FastAPI service", "Contracts  |  Validation"),
        (1250, 60, 1760, 230, "Python numerical core", "Fit  |  Optimize  |  Diagnose"),
        (40, 415, 550, 590, "Data sources", "CSV upload or synthetic sample"),
        (645, 415, 1155, 590, "Analysis pipeline", "Validated observations and model"),
        (1250, 415, 1760, 590, "Results and exports", "Scenarios  |  PDF  |  CSV  |  JSON"),
    ]
    for x0, y0, x1, y1, title, sub in boxes:
        d.rounded_rectangle((x0, y0, x1, y1), radius=16, fill="#f3f5f7", outline="#4c5968", width=3)
        d.text(((x0+x1)/2, y0+44), title, font=bold, fill="black", anchor="mm")
        d.text(((x0+x1)/2, y0+105), sub, font=font, fill="#273441", anchor="mm")
    def arrow(a, b):
        d.line((*a, *b), fill="#4c5968", width=5)
        x,y=b
        if a[1] == y:
            d.polygon([(x,y),(x-17,y-10),(x-17,y+10)],fill="#4c5968")
        else:
            d.polygon([(x,y),(x-10,y-17),(x+10,y-17)],fill="#4c5968")
    arrow((550,145),(645,145)); arrow((1155,145),(1250,145))
    arrow((1505,230),(1505,415)); arrow((550,502),(645,502)); arrow((1155,502),(1250,502))
    d.text((900,333),"One backend implementation supplies the numerical results",font=font,fill="#273441",anchor="mm")
    im.save(ASSETS / "architecture.png")


def screenshot(source: Path):
    crops = {
        "desktop-dataset.png": (0, 0, 1440, 840),
        "extended-model-overlay.png": (270, 1350, 1400, 1750),
        "extended-convergence.png": (270, 670, 1400, 1355),
        "extended-diagnostics.png": (270, 880, 1400, 1300),
    }
    dest = ASSETS / source.name
    Image.open(source).crop(crops[source.name]).save(dest)
    return dest


def set_cell_shade(cell, fill):
    shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(shd)


def add_table(doc, rows, page_title):
    count = len(rows[0])
    t = doc.add_table(rows=1, cols=count)
    t.autofit = False
    available = 6.47
    widths = {
        "Scope": [1.35,5.12], "Architecture": [1.12,2.02,3.33],
        "Data Design": [1.90,.82,3.75], "Diagnostics": [1.05,2.30,3.12],
        "Revenue Model": [1.18,1.55,1.85,1.89], "Application Modules": [1.65,4.82],
        "API": [.72,2.40,3.35], "Results": [2.95,1.76,1.76],
        "Worked": [1.20,1.65,1.75,1.87], "Testing": [1.15,2.72,2.60],
        "User Guide": [1.70,4.77], "PricePilot": [3.45,3.02],
    }
    ws = next((v for k,v in widths.items() if k in page_title and len(v)==count),[available/count]*count)
    if "Data Design" in page_title and count==3 and rows[0][0]=="Dataset": ws=[2.0,.65,3.82]
    for c,w in zip(t.columns,ws): c.width=Inches(w)
    for i,row in enumerate(rows):
        cells = t.rows[0].cells if i==0 else t.add_row().cells
        for j,(cell,text) in enumerate(zip(cells,row)):
            cell.width=Inches(ws[j]); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text=text
            pr=cell._tc.get_or_add_tcPr()
            margins=OxmlElement("w:tcMar")
            for edge in ("top","left","bottom","right"):
                e=OxmlElement("w:"+edge);e.set(qn("w:w"),"75");e.set(qn("w:type"),"dxa");margins.append(e)
            pr.append(margins)
            for p in cell.paragraphs:
                p.paragraph_format.space_after=Pt(0)
                p.paragraph_format.line_spacing=1.04
                if j==0 and count>=3 and "Method" in rows[0]: p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name="Times New Roman"; run.font.size=Pt(10 if count<4 else 9.5)
                    if i==0: run.bold=True;run.font.color.rgb=RGBColor(255,255,255)
            set_cell_shade(cell,"243748" if i==0 else ("F2F5F7" if i%2==0 else "FFFFFF"))
        trpr=t.rows[i]._tr.get_or_add_trPr()
        if i==0:
            repeat=OxmlElement("w:tblHeader");trpr.append(repeat)
        no_split=OxmlElement("w:cantSplit");trpr.append(no_split)
    borders=OxmlElement("w:tblBorders")
    for edge in ("top","left","bottom","right","insideH","insideV"):
        e=OxmlElement("w:"+edge);e.set(qn("w:val"),"single");e.set(qn("w:sz"),"5");e.set(qn("w:color"),"D9D9D9");borders.append(e)
    t._tbl.tblPr.append(borders)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)


def equation(doc,text):
    p=doc.add_paragraph()
    p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(5)
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    om=OxmlElement("m:oMath");r=OxmlElement("m:r");el=OxmlElement("m:t");el.text=text;r.append(el);om.append(r);p._p.append(om)
    return p


def build():
    architecture()
    doc=Document()
    sec=doc.sections[0]
    sec.page_width=Inches(8.2677);sec.page_height=Inches(11.6929)
    sec.top_margin=Inches(.80);sec.bottom_margin=Inches(.72)
    sec.left_margin=Inches(.90);sec.right_margin=Inches(.90)
    sec.header_distance=Inches(.30);sec.footer_distance=Inches(.32)
    sec.different_first_page_header_footer=True
    normal=doc.styles["Normal"]
    normal.font.name="Times New Roman";normal.font.size=Pt(11.5);normal.font.color.rgb=RGBColor(0,0,0)
    normal.paragraph_format.line_spacing=1.10
    normal.paragraph_format.space_after=Pt(7)
    normal.paragraph_format.widow_control=True
    for name,size in [("Title",32),("Subtitle",18),("Heading 1",18),("Heading 2",12.5),("Heading 3",11.5)]:
        st=doc.styles[name];st.font.name="Times New Roman";st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
        st.paragraph_format.space_before=Pt(10 if name=="Heading 2" else 0)
        st.paragraph_format.space_after=Pt(7)
        st.paragraph_format.keep_with_next=True
    doc.styles["Caption"].font.name="Times New Roman";doc.styles["Caption"].font.size=Pt(10)
    doc.styles["Caption"].font.color.rgb=RGBColor(0,0,0)
    for name in ["Title","Subtitle"]:
        st=doc.styles[name]
        st.font.italic=False
        for border in st.element.xpath(".//w:pBdr"):
            border.getparent().remove(border)
        fonts=st.element.get_or_add_rPr().find(qn("w:rFonts"))
        if fonts is not None:
            for attr in list(fonts.attrib):
                if "Theme" in attr:del fonts.attrib[attr]
    for name in ["TOC 1","TOC Heading"]:
        try:
            doc.styles[name].font.name="Times New Roman";doc.styles[name].font.size=Pt(11)
            doc.styles[name].font.color.rgb=RGBColor(0,0,0)
        except KeyError: pass
    head=sec.header.paragraphs[0];head.text="PricePilot    |    MLRIT"
    head.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    head.runs[0].font.size=Pt(9)
    foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=foot.add_run();fld=OxmlElement("w:fldSimple");fld.set(qn("w:instr"),"PAGE");run._r.addnext(fld)
    props=doc.core_properties
    props.title="PricePilot Project Documentation";props.subject="Numerical Methods Project Report"
    props.author="Arman Acharya; Manit Reddy; K.Aravind";props.keywords="PricePilot, MLRIT, least squares, Newton Raphson"
    props.comments=""
    chunks=SOURCE.read_text(encoding="utf-8").split("<!-- page -->")
    manifest=[]
    for page_index,chunk in enumerate(chunks):
        if page_index: doc.add_page_break()
        lines=chunk.strip().splitlines(); i=0; title=""
        while i<len(lines):
            line=lines[i].strip()
            if not line: i+=1;continue
            if line.startswith("# "):
                title=line[2:]
                if page_index==0:
                    p=doc.add_paragraph(title,"Title");p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before=Pt(65);p.paragraph_format.space_after=Pt(15)
                    borders=OxmlElement("w:pBdr")
                    for edge in ["top","left","bottom","right"]:
                        el=OxmlElement("w:"+edge);el.set(qn("w:val"),"nil");borders.append(el)
                    p._p.get_or_add_pPr().append(borders)
                elif title=="Contents":
                    p=doc.add_paragraph(title)
                    p.paragraph_format.space_after=Pt(10)
                    p.runs[0].bold=True;p.runs[0].font.size=Pt(18)
                else: doc.add_paragraph(title,"Heading 1")
                manifest.append({"section":title,"intended_page":page_index+1})
            elif line.startswith("## "):
                p=doc.add_paragraph(line[3:],"Subtitle" if page_index==0 else "Heading 2")
                if page_index==0:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                if title.startswith("Appendix"):
                    p.paragraph_format.space_before=Pt(6)
                    p.paragraph_format.space_after=Pt(4)
            elif line=="{{TOC}}":
                p=doc.add_paragraph();field=OxmlElement("w:fldSimple");field.set(qn("w:instr"),'TOC \\o "1-1" \\h \\z \\u')
                rr=OxmlElement("w:r");tt=OxmlElement("w:t");tt.text="Contents update when the document is opened in Word.";rr.append(tt);field.append(rr);p._p.append(field)
            elif line.startswith("| "):
                table_lines=[]
                while i<len(lines) and lines[i].strip().startswith("| "):
                    raw=lines[i].strip()
                    if not re.match(r"^\|[\s|:-]+\|$",raw):table_lines.append([c.strip() for c in raw.strip("|").split("|")])
                    i+=1
                add_table(doc,table_lines,title);continue
            elif line.startswith("```"):
                code=[];i+=1
                while i<len(lines) and not lines[i].startswith("```"):
                    code.append(lines[i]);i+=1
                for text in code:
                    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1.0
                    r=p.add_run(text);r.font.name="Consolas";r.font.size=Pt(8.4)
            elif line.startswith("!["):
                name,location=re.match(r"!\[(.*?)\]\((.*?)\)",line).groups()
                path=ASSETS/"architecture.png" if location=="architecture.png" else screenshot((SOURCE.parent/location).resolve())
                p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after=Pt(3);p.paragraph_format.keep_with_next=True
                r=p.add_run();r.add_picture(str(path),width=Inches(6.35))
                inline=r._r.xpath('.//wp:docPr')[0];inline.set("descr",name+" screenshot excerpt" if name!="Architecture" else "Frontend API and numerical core architecture")
            elif line.startswith("Figure "):
                p=doc.add_paragraph(line,"Caption");p.paragraph_format.space_after=Pt(9)
            elif line.startswith("> "):
                equation(doc,line[2:])
            else:
                numbered=re.match(r"^\d+\. (.*)",line)
                if line.startswith("- "):p=doc.add_paragraph(line[2:],"List Bullet")
                elif numbered:p=doc.add_paragraph(line)
                else:p=doc.add_paragraph(line)
                if page_index==0:
                    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_after=Pt(12)
                    if line in ["Submitted to MLRIT","Mr. Praveen Kumar","28 October 2026"]:
                        for r in p.runs:r.bold=True;r.font.size=Pt(14)
                elif not line.startswith(("http","- ")) and not numbered:
                    p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
                if title.startswith("Appendix"):
                    p.paragraph_format.space_after=Pt(5)
                    p.paragraph_format.line_spacing=1.04
                if line.startswith("http"):
                    for r in p.runs:r.font.size=Pt(9)
            i+=1
    settings=doc.settings.element
    update=OxmlElement("w:updateFields");update.set(qn("w:val"),"true");settings.append(update)
    dest=OUT/"PricePilot_Project_Documentation.docx"
    doc.save(dest)
    import json
    (OUT/"report_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Created {dest}; intended pages {len(chunks)}")


if __name__=="__main__":build()
