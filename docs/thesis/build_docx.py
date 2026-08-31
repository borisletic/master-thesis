"""Generiše master rad (.docx) u formatu FTN bachelor rada.

Pristup: kopira se originalni .docx (stilovi, tema, futeri, numeracija, sectPr),
a menja se samo `word/document.xml`. Time je formatiranje identično predlošku:
A4, TimesRoman 14pt, obostrano poravnanje, Heading1 automatski numerisan,
Heading2 plavi (ručno numerisan 1.1, 1.2...), futer sa brojevima strana.

Upotreba:
    python docs/thesis/build_docx.py --template <bsc.docx> --out <master.docx>
"""
from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

# Širina sadržaja: A4 (11907) - leva margina (1418) - desna (567)
CONTENT_W = 9922
BULLET_NUMID = 11          # postojeća bullet numeracija iz predloška
HEADING_NUMID = 2          # automatska numeracija za Heading1


def esc(t: str) -> str:
    return escape(str(t))


# --------------------------------------------------------------------------- blokovi

def p(text: str = "", style: str | None = None, bold=False, italic=False,
      size: int | None = None, align: str | None = None, mono=False) -> str:
    """Običan pasus."""
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    rpr = []
    if bold:
        rpr.append('<w:b/>')
    if italic:
        rpr.append('<w:i/>')
    if mono:
        rpr.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
    if size:
        rpr.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr_x = f'<w:rPr>{"".join(rpr)}</w:rPr>' if rpr else ''
    ppr_x = f'<w:pPr>{"".join(ppr)}{rpr_x}</w:pPr>' if ppr else ''
    return f'<w:p>{ppr_x}<w:r>{rpr_x}<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'


def h1(text: str) -> str:
    """Poglavlje — automatski numerisano (1., 2., ...), uvek na novoj strani."""
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:pageBreakBefore/>'
            f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{HEADING_NUMID}"/></w:numPr>'
            f'</w:pPr><w:r><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def h1_nonum(text: str) -> str:
    """Poglavlje bez numeracije (Literatura, Biografija), na novoj strani."""
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:pageBreakBefore/>'
            f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
            f'</w:pPr><w:r><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def h2(text: str) -> str:
    """Potpoglavlje — ručno numerisano, npr. '1.1 Motivacija'."""
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def sub(text: str) -> str:
    """Podnaslov unutar potpoglavlja (bold, bez numeracije) — kao u predlošku."""
    return (f'<w:p><w:pPr><w:spacing w:before="160" w:after="60"/></w:pPr>'
            f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def bullet(text: str) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="ListParagraph"/>'
            f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{BULLET_NUMID}"/></w:numPr>'
            f'<w:spacing w:after="60"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def code(text: str) -> str:
    """Blok koda / komandne linije."""
    return (f'<w:p><w:pPr><w:spacing w:before="40" w:after="40"/><w:ind w:left="284"/>'
            f'<w:jc w:val="left"/></w:pPr><w:r>'
            f'<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="20"/></w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


def caption(text: str) -> str:
    """Naslov tabele/slike — centriran, manji font, kao u predlošku."""
    return (f'<w:p><w:pPr><w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/></w:pPr>'
            f'<w:r><w:rPr><w:sz w:val="22"/></w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')


_FIG_COUNTER = {"n": 0}
_FIG_REG: dict[str, int] = {}
_IMAGES: list[dict] = []          # {path, rid, target}
_FIRST_FREE_RID = 900             # daleko iznad rId iz predloska (max 35)

# A4 sirina sadrzaja u EMU (1 twip = 635 EMU): 9922 twips
_CONTENT_EMU = 9922 * 635


def figure(path: str, caption_text: str, key: str | None = None,
           width_frac: float = 1.0) -> str:
    """Ubacuje PNG kao inline sliku, sa naslovom ispod (kao u predlosku).

    Odnos stranica se cita iz same datoteke, pa se visina racuna automatski.
    """
    import struct
    data = Path(path).read_bytes()
    PNG_MAGIC = bytes([137, 80, 78, 71, 13, 10, 26, 10])
    if data[:8] != PNG_MAGIC:
        raise ValueError(f"ocekivan PNG: {path}")
    w_px, h_px = struct.unpack('>II', data[16:24])

    _FIG_COUNTER["n"] += 1
    n = _FIG_COUNTER["n"]
    if key:
        if key in _FIG_REG:
            raise ValueError(f"duplikat kljuca slike: {key!r}")
        _FIG_REG[key] = n

    rid = _FIRST_FREE_RID + len(_IMAGES)
    target = f"media/orr_fig{n}.png"
    _IMAGES.append({"path": path, "rid": rid, "target": target})

    cx = int(_CONTENT_EMU * width_frac)
    cy = int(cx * h_px / w_px)
    name = f"figure{n}"

    drawing = (
        f'<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="160" w:after="40"/></w:pPr>'
        f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{1000+n}" name="{name}"/>'
        f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{1000+n}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="rId{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    )
    return drawing + caption(f"Слика {n} – {caption_text}")


def fref(key: str) -> str:
    """Placeholder za poziv na sliku u tekstu; razresava se u build()."""
    return "{{F:" + key + "}}"


_TBL_COUNTER = {"n": 0}
_TBL_REG: dict[str, int] = {}


def tcap(text: str, key: str | None = None) -> str:
    """Naslov tabele sa automatskom numeracijom.

    `key` registruje broj tabele pod simbolickim imenom, pa se u tekstu poziva
    kao `{{T:key}}` bez obzira na redosled pisanja. Zamena se radi u build().
    """
    _TBL_COUNTER["n"] += 1
    if key:
        if key in _TBL_REG:
            raise ValueError(f"duplikat kljuca tabele: {key!r}")
        _TBL_REG[key] = _TBL_COUNTER["n"]
    return caption(f"Табела {_TBL_COUNTER['n']} – {text}")


def resolve_refs(xml: str) -> str:
    """Zamenjuje {{T:key}} stvarnim brojevima tabela; puca ako kljuc ne postoji."""
    missing = set(re.findall(r'\{\{T:([^}]+)\}\}', xml)) - set(_TBL_REG)
    if missing:
        raise KeyError(f"nepoznate reference na tabele: {sorted(missing)}")
    missing_f = set(re.findall(r'\{\{F:([^}]+)\}\}', xml)) - set(_FIG_REG)
    if missing_f:
        raise KeyError(f"nepoznate reference na slike: {sorted(missing_f)}")
    xml = re.sub(r'\{\{T:([^}]+)\}\}', lambda m: str(_TBL_REG[m.group(1)]), xml)
    return re.sub(r'\{\{F:([^}]+)\}\}', lambda m: str(_FIG_REG[m.group(1)]), xml)


def _cell(text: str, w: int, bold=False, shade: str | None = None, align="left") -> str:
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ''
    rpr = '<w:b/>' if bold else ''
    return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}'
            f'<w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:before="20" w:after="20"/><w:jc w:val="{align}"/></w:pPr>'
            f'<w:r><w:rPr>{rpr}<w:sz w:val="20"/></w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p></w:tc>')


def table(rows: list[list[str]], widths: list[int] | None = None,
          header=True, aligns: list[str] | None = None) -> str:
    """Tabela sa zaglavljem; širine u DXA moraju da sabiraju CONTENT_W."""
    ncol = len(rows[0])
    if widths is None:
        base = CONTENT_W // ncol
        widths = [base] * ncol
        widths[0] += CONTENT_W - base * ncol
    if aligns is None:
        aligns = ["left"] + ["center"] * (ncol - 1)
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    borders = ('<w:tblBorders>' + ''.join(
        f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
        for s in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders>')
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{CONTENT_W}" w:type="dxa"/>{borders}'
           f'<w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for i, row in enumerate(rows):
        hdr = header and i == 0
        trpr = '<w:trPr><w:tblHeader/></w:trPr>' if hdr else ''
        cells = ''.join(
            _cell(c, widths[j], bold=hdr, shade="D9E2F3" if hdr else None,
                  align="center" if hdr else aligns[j])
            for j, c in enumerate(row))
        out.append(f'<w:tr>{trpr}{cells}</w:tr>')
    out.append('</w:tbl>')
    # prazan pasus posle tabele (Word zahteva razdvajanje uzastopnih tabela)
    out.append('<w:p><w:pPr><w:spacing w:after="60"/></w:pPr></w:p>')
    return ''.join(out)


def pagebreak() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def toc() -> str:
    """Automatsko generisanje sadržaja (Word: F9 za ažuriranje)."""
    return (
        '<w:p><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr>'
        '<w:r><w:t>САДРЖАЈ</w:t></w:r></w:p>'
        '<w:p><w:pPr><w:pStyle w:val="TOC1"/><w:tabs>'
        f'<w:tab w:val="right" w:leader="dot" w:pos="{CONTENT_W}"/></w:tabs></w:pPr>'
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:rPr><w:i/><w:sz w:val="22"/></w:rPr>'
        '<w:t>[Десни клик → Update Field за генерисање садржаја]</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    )


# --------------------------------------------------------------------------- build

def build(template: Path, out: Path, body_xml: str) -> None:
    src = zipfile.ZipFile(template)
    doc = src.read('word/document.xml').decode('utf-8')

    # zadrži originalni sectPr (futeri, margine, veličina strane)
    m = re.search(r'<w:sectPr.*?</w:sectPr>', doc, re.S)
    sectpr = m.group() if m else ''
    sectpr = sectpr.replace('<w:titlePg/>', '')  # nema naslovne strane u ovom fajlu

    head = doc[:doc.index('<w:body>') + len('<w:body>')]
    new_doc = head + resolve_refs(body_xml) + sectpr + '</w:body></w:document>'

    # Slike iz predloška koje novi document.xml više ne referiše treba odbaciti.
    # Bitno kad se kao predložak koristi ranije izgrađen (i u Word-u presnimljen)
    # .docx: Word preimenuje media u image*.png, pa bi se uz naše orr_fig*.png
    # svaka slika našla u fajlu dvaput.
    rels_xml = src.read('word/_rels/document.xml.rels').decode('utf-8')
    used_rids = set(re.findall(r'r:(?:embed|id|link)="(rId\d+)"', new_doc))
    orphan_media = {
        target for rid, target in re.findall(
            r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_xml)
        if target.startswith('media/') and rid not in used_rids
    }
    drop_files = {'word/' + t for t in orphan_media}

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename in drop_files:
                continue
            if item.filename == 'word/document.xml':
                dst.writestr(item, new_doc.encode('utf-8'))
            elif item.filename == 'word/_rels/document.xml.rels':
                rels = rels_xml
                for t in orphan_media:
                    rels = re.sub(
                        r'<Relationship[^>]*Target="' + re.escape(t) + r'"[^>]*/>', '', rels)
                if _IMAGES:
                    extra = ''.join(
                        f'<Relationship Id="rId{im["rid"]}" '
                        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                        f'relationships/image" Target="{im["target"]}"/>'
                        for im in _IMAGES)
                    rels = rels.replace('</Relationships>', extra + '</Relationships>')
                dst.writestr(item, rels)
            else:
                dst.writestr(item, src.read(item.filename))
        for im in _IMAGES:
            dst.writestr('word/' + im['target'], Path(im['path']).read_bytes())
    src.close()
    if orphan_media:
        print(f"[clean] dropped {len(orphan_media)} unreferenced template image(s)")
    print(f"[ok] {out}  ({out.stat().st_size // 1024} KB)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    # content.py radi `from build_docx import ...`, sto ucitava OVAJ fajl kao poseban
    # modul (`build_docx`), razlicit od `__main__`. Registar tabela se puni tamo, pa
    # se i build/resolve_refs moraju pozvati iz te instance modula.
    import build_docx as bd           # noqa: E402
    from content import BODY          # noqa: E402
    bd.build(Path(args.template), Path(args.out), BODY)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
