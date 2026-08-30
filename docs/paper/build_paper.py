# -*- coding: utf-8 -*-
"""Generiše rad za Zbornik radova Fakulteta tehničkih nauka (format 30BExx).

Dvokolonski A4, Times New Roman 10pt, zaglavlje + UDK/DOI, naslov SR i EN,
Kratak sadržaj / Ključne reči / Abstract / Keywords, numerisane sekcije,
Literatura i Kratka biografija.

Docx se pravi od nule (minimalan OOXML paket), jer je raspored bitno drugačiji
od master rada.

Upotreba:
    python docs/paper/build_paper.py --out docs/paper/Zbornik_BorisLetic.docx
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

# --- geometrija strane (twips) -------------------------------------------------
PW, PH = 11907, 16840          # A4
MARG = 1134                    # 2 cm
COL_GAP = 284                  # 0.5 cm
COL_W = (PW - 2 * MARG - COL_GAP) // 2      # ~4678


def esc(t) -> str:
    return escape(str(t))


# --- gradivni elementi ---------------------------------------------------------

def p(text="", *, bold=False, italic=False, size=20, align="both",
      space_before=0, space_after=60, caps=False, indent=0, border_top=False,
      font=None, keep=False) -> str:
    rpr = []
    if font:
        rpr.append(f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>')
    if bold:
        rpr.append('<w:b/>')
    if italic:
        rpr.append('<w:i/>')
    if caps:
        rpr.append('<w:caps/>')
    rpr.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr_x = f'<w:rPr>{"".join(rpr)}</w:rPr>'

    ppr = [f'<w:jc w:val="{align}"/>',
           f'<w:spacing w:before="{space_before}" w:after="{space_after}" w:line="240" w:lineRule="auto"/>']
    if indent:
        ppr.append(f'<w:ind w:left="{indent}" w:hanging="{indent}"/>')
    if border_top:
        ppr.append('<w:pBdr><w:top w:val="single" w:sz="4" w:space="4" w:color="auto"/></w:pBdr>')
    if keep:
        ppr.append('<w:keepNext/>')
    ppr.append(rpr_x)

    return (f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>'
            f'<w:r>{rpr_x}<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def lead(label: str, body: str, *, size=20) -> str:
    """Pasus koji pocinje boldovanom oznakom, npr. 'Kratak sadržaj – ...'."""
    rpr = f'<w:rPr><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
    rpr_b = f'<w:rPr><w:b/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
    return (f'<w:p><w:pPr><w:jc w:val="both"/>'
            f'<w:spacing w:before="0" w:after="120" w:line="240" w:lineRule="auto"/>{rpr}</w:pPr>'
            f'<w:r>{rpr_b}<w:t xml:space="preserve">{esc(label)}</w:t></w:r>'
            f'<w:r>{rpr}<w:t xml:space="preserve">{esc(body)}</w:t></w:r></w:p>')


def h(text: str) -> str:
    """Naslov sekcije: '1. UVOD'."""
    return p(text, bold=True, size=20, align="left", space_before=200, space_after=120, keep=True)


def hsub(text: str) -> str:
    """Podnaslov: '3.1. ...'."""
    return p(text, bold=True, size=20, align="left", space_before=140, space_after=80, keep=True)


def ref(text: str) -> str:
    """Stavka literature sa visecim uvlacenjem."""
    return p(text, size=18, align="both", space_after=60, indent=340)


def cap(text: str) -> str:
    """Naslov tabele (iznad tabele, kao u uzoru)."""
    return p(text, size=18, align="left", space_before=140, space_after=60, keep=True)


def _cell(text, w, *, bold=False, align="left", size=16, shade=None) -> str:
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ''
    b = '<w:b/>' if bold else ''
    return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}</w:tcPr>'
            f'<w:p><w:pPr><w:jc w:val="{align}"/>'
            f'<w:spacing w:before="10" w:after="10" w:line="240" w:lineRule="auto"/></w:pPr>'
            f'<w:r><w:rPr>{b}<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p></w:tc>')


def table(rows, widths, *, aligns=None, size=16) -> str:
    ncol = len(rows[0])
    if aligns is None:
        aligns = ["left"] + ["center"] * (ncol - 1)
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    borders = ('<w:tblBorders>' + ''.join(
        f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        for s in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders>')
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/>{borders}'
           f'<w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for i, row in enumerate(rows):
        hdr = i == 0
        cells = ''.join(
            _cell(c, widths[j], bold=hdr, size=size,
                  align="center" if hdr else aligns[j],
                  shade="E8E8E8" if hdr else None)
            for j, c in enumerate(row))
        out.append(f'<w:tr>{"<w:trPr><w:tblHeader/></w:trPr>" if hdr else ""}{cells}</w:tr>')
    out.append('</w:tbl>')
    out.append(p("", size=8, space_after=60))
    return ''.join(out)


def sect_single() -> str:
    """Kraj jednokolonske (naslovne) sekcije — ide u pPr poslednjeg pasusa."""
    return (f'<w:p><w:pPr><w:sectPr>'
            f'<w:pgSz w:w="{PW}" w:h="{PH}"/>'
            f'<w:pgMar w:top="{MARG}" w:right="{MARG}" w:bottom="{MARG}" w:left="{MARG}" '
            f'w:header="567" w:footer="567" w:gutter="0"/>'
            f'<w:cols w:space="{COL_GAP}"/><w:type w:val="continuous"/>'
            f'</w:sectPr></w:pPr></w:p>')


def sect_two() -> str:
    """Zavrsna dvokolonska sekcija."""
    return (f'<w:sectPr>'
            f'<w:pgSz w:w="{PW}" w:h="{PH}"/>'
            f'<w:pgMar w:top="{MARG}" w:right="{MARG}" w:bottom="{MARG}" w:left="{MARG}" '
            f'w:header="567" w:footer="567" w:gutter="0"/>'
            f'<w:cols w:num="2" w:space="{COL_GAP}" w:equalWidth="1"/>'
            f'<w:type w:val="continuous"/></w:sectPr>')


# --- pakovanje docx ------------------------------------------------------------

_CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''

_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

_DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

_STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
<w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:val="sr-Cyrl-RS"/>
</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="60" w:line="240" w:lineRule="auto"/>
<w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
</w:styles>'''

_DOC_HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
             '<w:body>')


def build(out: Path, body_xml: str) -> None:
    doc = _DOC_HEAD + body_xml + sect_two() + '</w:body></w:document>'
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', _CONTENT_TYPES)
        z.writestr('_rels/.rels', _RELS)
        z.writestr('word/document.xml', doc)
        z.writestr('word/styles.xml', _STYLES)
        z.writestr('word/_rels/document.xml.rels', _DOC_RELS)
    print(f"[ok] {out}  ({out.stat().st_size // 1024} KB)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    import build_paper as bp                 # kanonicka instanca modula
    from paper_content import BODY           # noqa: E402
    bp.build(Path(args.out), BODY)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
