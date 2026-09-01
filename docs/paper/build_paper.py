# -*- coding: utf-8 -*-
"""Generiše rad za Zbornik radova Fakulteta tehničkih nauka.

Pristup: kopira se zvanični FTN predložak (.dotx) — stilovi, numeracija, tema,
fontovi i podešavanja — a menja se samo `word/document.xml`. Time su format,
fontovi, proredi i automatska numeracija poglavlja identični predlošku.

Stilovi iz predloška koji se koriste:
    9-         zaglavlje Zbornika (Arial Black 13pt)
    5-         UDK i DOI (TNR 10pt bold, desno)
    6-         naslov rada (TNR 14pt bold, centrirano)
    4-Autori   autori i institucija (TNR 12pt, centrirano)
    a          labele: Studijski program, Ključne reči (TNR 10pt bold)
    8-         napomena o mentorstvu (TNR 10pt)
    1-         poglavlje  — AUTOMATSKI numerisano (numId 7, lvl 0) -> "1."
    2-         potpoglavlje — AUTOMATSKI numerisano (numId 7, lvl 1) -> "1.1."
    0-         tekst rada (TNR 10pt, obostrano)
    Caption    natpisi tabela i slika (9pt, centrirano)

Zato se u paper_content.py naslovi pišu BEZ rednog broja.

Upotreba:
    python docs/paper/build_paper.py --out docs/paper/Zbornik_BorisLetic.docx
"""
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

# --- geometrija strane (twips), identična predlošku ----------------------------
PW, PH = 11906, 16838          # A4
MARG = 1134                    # 2 cm sve četiri margine
COL_GAP = 284                  # 0.5 cm razmak između stubaca
COL_W = (PW - 2 * MARG - COL_GAP) // 2

# delovi predloška koji se NE prenose (komentari recenzenata)
_DROP_PREFIXES = ('word/comments', 'word/people.xml')


def esc(t) -> str:
    return escape(str(t))


def _rpr(bold=False, italic=False, size=None, font=None) -> str:
    r = []
    if font:
        r.append(f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>')
    if bold:
        r.append('<w:b/>')
    if italic:
        r.append('<w:i/>')
    if size:
        r.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    return f'<w:rPr>{"".join(r)}</w:rPr>' if r else ''


def _run(text, **kw) -> str:
    return f'<w:r>{_rpr(**kw)}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def styled(style: str, *runs: str, align=None, space_before=None,
           space_after=None, indent=None, keep=False, border_top=False) -> str:
    """Pasus sa imenovanim stilom iz predloška i opcionim doterivanjem."""
    ppr = [f'<w:pStyle w:val="{style}"/>']
    if border_top:
        ppr.append('<w:pBdr><w:top w:val="single" w:sz="4" w:space="4" w:color="auto"/></w:pBdr>')
    sp = ''
    if space_before is not None:
        sp += f' w:before="{space_before}"'
    if space_after is not None:
        sp += f' w:after="{space_after}"'
    if sp:
        ppr.append(f'<w:spacing{sp}/>')
    if indent:
        ppr.append(f'<w:ind w:left="{indent}" w:hanging="{indent}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    if keep:
        ppr.append('<w:keepNext/>')
    return f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>{"".join(runs)}</w:p>'


# --- gradivni elementi po predlošku --------------------------------------------

def zaglavlje(text) -> str:
    return styled('9-', _run(text))


# Zaglavlje Zbornika je u predlošku tabela sa logotipom FTN-a. Preuzima se
# doslovno, da bi logo i raspored ostali identični predlošku (i da ga rebuild
# ne bi obrisao). Jedina izmena je razmak u "НовиСад".
_HEADER_TBL: str | None = None


def zaglavlje_tabela(template: Path) -> str:
    global _HEADER_TBL
    if _HEADER_TBL is None:
        x = zipfile.ZipFile(template).read('word/document.xml').decode('utf-8')
        m = re.search(r'<w:tbl>.*?</w:tbl>', x, re.S)
        if not m:
            raise SystemExit('[error] predložak nema tabelu zaglavlja')
        _HEADER_TBL = m.group().replace('НовиСад', 'Нови Сад')
    return _HEADER_TBL


def prazan(style='0-') -> str:
    """Prazan pasus kao razmak (predložak ih koristi oko naslova)."""
    return styled(style)


def udk(text) -> str:
    return styled('5-', _run(text))


def naslov(text, *, italic=False) -> str:
    return styled('6-', _run(text, italic=italic))


def autori(imena, institucija) -> str:
    return styled('4-Autori', _run(imena + ', '), _run(institucija))


def labela(label, body, *, italic_body=False) -> str:
    """Stil 'a' — Studijski program, Ključne reči."""
    return styled('a', _run(label), _run(body, italic=italic_body))


def sazetak(label, body, *, italic_body=False) -> str:
    """Normal stil sa boldovanom oznakom — Kratak sadržaj / Abstract / Keywords."""
    return styled('0-', _run(label, bold=True), _run(body, italic=italic_body),
                  space_after=120)


def napomena(text) -> str:
    return styled('8-', _run(text, bold=True))


def crta() -> str:
    return styled('8-', _run('__________________________________________'))


def h(text) -> str:
    """Poglavlje — BEZ rednog broja, numeraciju dodaje stil 1-."""
    return styled('1-', _run(text), keep=True)


def hsub(text) -> str:
    """Potpoglavlje — BEZ rednog broja, numeraciju dodaje stil 2-."""
    return styled('2-', _run(text), keep=True)


def para(*texts) -> str:
    return ''.join(styled('0-', _run(t)) for t in texts)


def p(text='', *, bold=False, italic=False, size=None, align=None,
      space_before=None, space_after=None, indent=None, border_top=False,
      style='0-') -> str:
    return styled(style, _run(text, bold=bold, italic=italic, size=size),
                  align=align, space_before=space_before, space_after=space_after,
                  indent=indent, border_top=border_top)


def cap(text) -> str:
    """Natpis tabele — iznad tabele, kao što upútstvo traži."""
    return styled('Caption', _run(text), keep=True)


def slika_cap(text) -> str:
    """Natpis slike — ispod slike."""
    return styled('Caption', _run(text))


def ref(text) -> str:
    return styled('0-', _run(text), indent=284, space_after=0)


def _cell(text, w, *, bold=False, align='left', size=16, shade=None) -> str:
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ''
    return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}</w:tcPr>'
            f'<w:p><w:pPr><w:pStyle w:val="0-"/><w:jc w:val="{align}"/>'
            f'<w:spacing w:before="10" w:after="10"/></w:pPr>'
            f'{_run(text, bold=bold, size=size)}</w:p></w:tc>')


def table(rows, widths, *, aligns=None, size=16) -> str:
    ncol = len(rows[0])
    if aligns is None:
        aligns = ['left'] + ['center'] * (ncol - 1)
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    borders = ('<w:tblBorders>' + ''.join(
        f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')) + '</w:tblBorders>')
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/>{borders}'
           f'<w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for i, row in enumerate(rows):
        hdr = i == 0
        cells = ''.join(
            _cell(c, widths[j], bold=hdr, size=size,
                  align='center' if hdr else aligns[j],
                  shade='E8E8E8' if hdr else None)
            for j, c in enumerate(row))
        out.append(f'<w:tr>{"<w:trPr><w:tblHeader/></w:trPr>" if hdr else ""}{cells}</w:tr>')
    out.append('</w:tbl>')
    out.append(styled('0-', space_after=60))
    return ''.join(out)


# --- sekcije --------------------------------------------------------------------

_PG = (f'<w:pgSz w:w="{PW}" w:h="{PH}"/>'
       f'<w:pgMar w:top="{MARG}" w:right="{MARG}" w:bottom="{MARG}" w:left="{MARG}" '
       f'w:header="708" w:footer="708" w:gutter="0"/>')


def sect_single() -> str:
    """Zatvara jednokolonsku (naslovnu) sekciju."""
    return (f'<w:p><w:pPr><w:sectPr>{_PG}'
            f'<w:cols w:space="{COL_GAP}"/><w:type w:val="continuous"/>'
            f'</w:sectPr></w:pPr></w:p>')


def sect_two() -> str:
    """Završna dvokolonska sekcija (telo rada)."""
    return (f'<w:sectPr>{_PG}'
            f'<w:cols w:num="2" w:space="{COL_GAP}" w:equalWidth="1"/>'
            f'<w:type w:val="continuous"/></w:sectPr>')


# --- pakovanje docx iz predloška ------------------------------------------------

def _default_template(script_dir: Path) -> Path:
    # ~$... su Wordovi privremeni zaključavajući fajlovi, nisu predlošci
    cand = sorted(p for p in list(script_dir.glob('*.dotx')) + list(script_dir.glob('*.dotm'))
                  if not p.name.startswith('~$'))
    if not cand:
        raise SystemExit(f"[error] nema .dotx predloška u {script_dir}")
    return cand[0]


def build(template: Path, out: Path, body_xml: str) -> None:
    src = zipfile.ZipFile(template)
    doc = src.read('word/document.xml').decode('utf-8')
    head = doc[:doc.index('<w:body>') + len('<w:body>')]
    new_doc = head + body_xml + sect_two() + '</w:body></w:document>'

    drop = {n for n in src.namelist() if n.startswith(_DROP_PREFIXES)}

    # Zadrži samo one slike predloška koje novi document.xml stvarno referiše
    # (logo zaglavlja da, primeri slika iz upútstva ne).
    rels_xml = src.read('word/_rels/document.xml.rels').decode('utf-8')
    used_rids = set(re.findall(r'r:(?:embed|id|link)="(rId\d+)"', new_doc))
    orphan_media = {t for rid, t in re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_xml)
                    if t.startswith('media/') and rid not in used_rids}
    drop |= {'word/' + t for t in orphan_media}
    dropped = sorted(drop)

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename in drop:
                continue
            if item.filename == 'word/document.xml':
                dst.writestr(item, new_doc.encode('utf-8'))
            elif item.filename == '[Content_Types].xml':
                ct = src.read(item.filename).decode('utf-8')
                for n in drop:
                    ct = re.sub(r'<Override[^>]*PartName="/' + re.escape(n) + r'"[^>]*/>', '', ct)
                # .dotx glavni deo je "template.main+xml"; u .docx mora biti
                # "document.main+xml", inače Word prijavljuje oštećen fajl.
                ct = ct.replace('wordprocessingml.template.main+xml',
                                'wordprocessingml.document.main+xml')
                dst.writestr(item, ct)
            elif item.filename == 'word/_rels/document.xml.rels':
                rels = src.read(item.filename).decode('utf-8')
                for n in drop:
                    tgt = n[len('word/'):]
                    rels = re.sub(
                        r'<Relationship[^>]*Target="' + re.escape(tgt) + r'"[^>]*/>', '', rels)
                dst.writestr(item, rels)
            else:
                dst.writestr(item, src.read(item.filename))
    src.close()
    print(f"[template] {template.name}")
    if dropped:
        print(f"[clean] izostavljeno {len(dropped)} delova predloška (komентари/примери слика)")
    print(f"[ok] {out}  ({out.stat().st_size // 1024} KB)")


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--template', default=None,
                    help='FTN .dotx predložak (podrazumevano: .dotx iz istog direktorijuma)')
    args = ap.parse_args()
    tpl = Path(args.template) if args.template else _default_template(here)
    import build_paper as bp                 # kanonička instanca modula
    from paper_content import BODY           # noqa: E402
    bp.build(tpl, Path(args.out), BODY)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
