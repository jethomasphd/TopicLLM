from pathlib import Path
from urllib.parse import urljoin
import re,html
from lxml import html as LH
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,KeepTogether,Flowable,LongTable,TableStyle,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdfium2 as pdfium

repo=Path(__file__).resolve().parents[1];base=repo/'build-qa'
base.mkdir(exist_ok=True)
out=repo/'docs/preprints/TopicLLM_Methods_2026-11-19.pdf'
for name,file in [('Text','times.ttf'),('TextBold','timesbd.ttf'),('TextItalic','timesi.ttf'),('TextBI','timesbi.ttf'),('UI','arial.ttf')]:
    fontfile=Path('C:/Windows/Fonts')/file
    if fontfile.exists():
        pdfmetrics.registerFont(TTFont(name,str(fontfile)))
    else:
        standard={'Text':'Times-Roman','TextBold':'Times-Bold','TextItalic':'Times-Italic','TextBI':'Times-BoldItalic','UI':'Helvetica'}
        pdfmetrics.registerFont(pdfmetrics.Font(name,standard[name],'WinAnsiEncoding'))
pdfmetrics.registerFontFamily('Text',normal='Text',bold='TextBold',italic='TextItalic',boldItalic='TextBI')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('Body',fontName='Text',fontSize=11,leading=14.5,spaceAfter=8,allowWidows=0,allowOrphans=0))
styles.add(ParagraphStyle('Subtitle',fontName='TextItalic',fontSize=14,leading=18,spaceAfter=16))
styles.add(ParagraphStyle('Caption',fontName='TextBold',fontSize=9,leading=12,spaceAfter=8,keepWithNext=True))
styles.add(ParagraphStyle('Title2',fontName='TextBold',fontSize=22,leading=26,spaceAfter=16,keepWithNext=True))
styles.add(ParagraphStyle('Section',fontName='TextBold',fontSize=16,leading=20,spaceBefore=16,spaceAfter=8,keepWithNext=True))
styles.add(ParagraphStyle('Sub',fontName='TextBold',fontSize=12,leading=16,spaceBefore=12,spaceAfter=6,keepWithNext=True))
styles.add(ParagraphStyle('Small2',fontName='Text',fontSize=9,leading=12,spaceAfter=8))
styles.add(ParagraphStyle('Prompt2',fontName='UI',fontSize=9,leading=13,spaceAfter=12,leftIndent=12,rightIndent=12))
styles.add(ParagraphStyle('Formula',fontName='Text',fontSize=11,leading=22,spaceBefore=5,spaceAfter=14,leftIndent=12,rightIndent=12))
styles.add(ParagraphStyle('Reference',fontName='Text',fontSize=9,leading=12,spaceAfter=5,leftIndent=18,firstLineIndent=-18))
def clean(text):
    return re.sub(r'\s+',' ',text).strip().replace('\u00a0',' ')
def markup(el):
    # Keep scientific emphasis; navigation links stay readable in the PDF.
    value=html.escape(el.text or '')
    for child in el:
        if child.tag in ['style','script']:continue
        inside=markup(child)
        tag={'strong':'b','em':'i','code':'font','sub':'sub','sup':'super','b':'b','i':'i'}.get(child.tag)
        if child.tag=='br':value+='<br/>'
        elif tag=='font':value+=f'<font name="UI">{inside}</font>'
        elif child.tag=='a' and child.get('href'):
            target=html.escape(urljoin('https://topicllm.dev/paper/',child.get('href')),quote=True)
            value+=f'<link href="{target}">{inside}</link>'
        elif tag:value+=f'<{tag}>{inside}</{tag}>'
        else:value+=inside
        value+=html.escape(child.tail or '')
    return value

class Concept(Flowable):
    def __init__(self): Flowable.__init__(self);self.width=468;self.height=112
    def draw(self):
        c=self.canv
        for row,labels in enumerate([['Campaign posts','Topics + names','Human codebook'],['Presidential posts','Validate + classify','Overall prevalence']]):
            y=70-row*48
            for i,label in enumerate(labels):
                x=i*160
                c.setStrokeColor(colors.HexColor('#9cb8b3'));c.roundRect(x,y,148,30,4,stroke=1,fill=0)
                c.setFont('UI',9);c.setFillColor(colors.HexColor('#173b39'));c.drawCentredString(x+74,y+11,label)
                if i<2:c.drawString(x+151,y+11,'>')
        c.setDash(2,2);c.line(394,70,234,52);c.setDash()

doc=LH.fromstring((repo/'docs/paper/index.html').read_text(encoding='utf-8'))
page=doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," page ")]')[0]
story=[]
for el in page:
    cls=el.get('class','')
    if el.tag=='style' or cls=='banner':continue
    if el.tag=='h1':story.append(Paragraph(markup(el),styles['Title2']));continue
    if cls=='subtitle':story.append(Paragraph(markup(el),styles['Subtitle']));continue
    if cls=='formula':
        formula=[Paragraph(markup(el),styles['Formula'])]
        if story and isinstance(story[-1],Paragraph):formula.insert(0,story.pop())
        story.append(KeepTogether(formula));continue
    if cls in ['authors','affil']:
        story.append(Paragraph(markup(el),styles['Small2']));continue
    if cls=='abstract':
        story.extend([Spacer(1,10),Paragraph('Working manuscript | 19 November 2026 | Held-out evaluation complete',styles['Small2'])])
        for c in el:story.append(Paragraph(markup(c),styles['Sub' if c.tag=='h2' else 'Body']))
    elif cls=='prompt':story.append(KeepTogether([Paragraph(markup(el),styles['Prompt2'])]))
    elif cls=='tablewrap':
        table=el.find('table')
        caption=Paragraph(markup(table.find('caption')),styles['Caption'])
        rows=[[Paragraph(markup(c),styles['Small2']) for c in r] for r in table.xpath('.//tr')]
        widths={2:[280,188],3:[126,190,152],4:[270,66,66,66]}.get(len(rows[0]),[468/len(rows[0])]*len(rows[0]))
        if table.find('caption').text_content().startswith('Table 4.'):widths=[66,402]
        tab=LongTable(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),('GRID',(0,0),(-1,-1),.5,colors.HexColor('#cccccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        group=[caption,tab]
        if story and isinstance(story[-1],Paragraph) and story[-1].style.name in ['Section','Sub']:
            group.insert(0,story.pop())
        story.extend([KeepTogether(group),Spacer(1,12)])
    elif cls=='refs':
        for c in el:story.append(KeepTogether([Paragraph(markup(c),styles['Reference'])]))
    elif el.tag=='figure':story.append(KeepTogether([Concept(),Paragraph(markup(el.find('figcaption')),styles['Small2'])]))
    elif el.tag in ['h2','h3','p']:
        story.append(Paragraph(markup(el),styles[{'h2':'Section','h3':'Sub','p':'Body'}[el.tag]]))
def footer(canvas,doc):
    canvas.saveState();canvas.setFont('UI',8);canvas.setFillColor(colors.HexColor('#666666'))
    canvas.drawString(72,36,'TopicLLM | Working manuscript | 19 November 2026');canvas.drawRightString(540,36,str(doc.page));canvas.restoreState()
SimpleDocTemplate(str(out),pagesize=(612,792),leftMargin=72,rightMargin=72,topMargin=54,bottomMargin=58,title=page.find('h1').text_content(),author='Jacob E. Thomas').build(story,onFirstPage=footer,onLaterPages=footer)
qa=base/'methods_pdf_qa';qa.mkdir(exist_ok=True)
pdf=pdfium.PdfDocument(str(out))
for i in range(len(pdf)):
    pdf[i].render(scale=1.5).to_pil().save(qa/f'page-{i+1}.png')
print(f'Wrote revised PDF and rendered {len(pdf)} pages for review.')
