"""Independent letters-and-digits check of every version against its Mato Grosso do Sul legislation page (regex
tokenizer, no HTML parser).

    python -X utf8 check_letters.py [part.json ...]

For each version: the page body (no head, styles, scripts or comments) with every text run under a strike-through (s,
strike, del, or a line-through style) or in red (the publisher's remarks) left out, the notes in parentheses ("(redação dada pela ...)", "(acrescentado
pela ...)", "(declarado inconstitucional ...)", ...) left out, and the publisher's lines left out (the notice "(*) Os
textos contidos nesta base de dados ...", its "OBS:" remarks and the line "Texto Constitucional promulgado em ...
consolidado com as alterações ..."), reduced to letters and digits, must equal the version's unit files reduced the
same way, each unit found at its place in document order.
"""
import hashlib, html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from br_lib import letters_check  # noqa: E402

TOKEN = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:[^>"\']|"[^"]*"|\'[^\']*\')*)>|([^<]+)', re.S)
VOIDS = ('br', 'img', 'meta', 'link', 'hr', 'input', 'col', 'area', 'base', 'wbr')
BREAKS = ('p', 'div', 'br', 'tr', 'li', 'table', 'tbody', 'thead', 'ul', 'ol', 'center', 'blockquote', 'h1', 'h2', 'h3',
          'h4', 'h5', 'h6')
NOTES = re.compile(r'\(\s*(?:Nova\s+reda|Reda[çc]|Acresc|Revogad|Inclu[íi]d|Alterad|Renumerad|Suprimid|Vide\b|Vig[êe]n|'
                   r'Regulamentad|Modificad|Declarad|Suspens|Ver\b|Efic[áa]cia|Derrogad|Transformad|Prorrogad|'
                   r'Obs\b|Express[ãa]o|Express[õo]es)(?:[^()]|\([^()]*\))*\)', re.I)
LINES = re.compile(r'(?im)^\s*(?:\(\*\) Os textos contidos nesta base de dados.*|OBS\s*[:.].*|Texto Constitucional '
                   r'promulgado em .* consolidado com as altera[çc][õo]es adotadas pelas Emendas Constitucionais\.?)\s*$')


def page_text(b):
    s = b.decode('cp1252', 'replace')
    s = re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->|<head\b.*?</head>', '', s)
    i = s.lower().find('<body')
    s = s[s.index('>', i) + 1:] if i >= 0 else s
    open_, out = [], []
    for t in TOKEN.finditer(s):
        close, tag, a, text = t.group(1), (t.group(2) or '').lower(), t.group(3) or '', t.group(4)
        if text is not None:
            color = ([o[2] for o in open_ if o[2]] or [''])[-1]
            struck = any(o[1] for o in open_) and html.unescape(text).strip() not in ('º', '°', 'ª')  # "n<s>º</s>"
            if not struck and color not in ('#ff0000', 'red'):
                out.append(re.sub(r'\s+', ' ', html.unescape(text)))
            continue
        if tag in BREAKS:
            out.append('\n')
        if close:
            for k in range(len(open_) - 1, -1, -1):
                if open_[k][0] == tag:
                    del open_[k:]
                    break
        elif tag not in VOIDS:
            m = re.search(r'(?i)\bcolor\s*=\s*"?([#\w]+)', a) or re.search(r'(?i)[;"\s]color\s*:\s*([#\w]+)', a)
            open_.append((tag, tag in ('s', 'strike', 'del') or 'line-through' in a.lower(), m.group(1).lower() if m else ''))
    text = '\n'.join(NOTES.sub(' ', l).strip() for l in ''.join(out).split('\n'))
    return LINES.sub('', text)


def main(paths):
    vs = []
    for p in paths:
        for a in json.load(open(p, encoding='utf-8'))['acts']:
            for v in a['versions']:
                raw = (HERE / '.cache' / 'raw' / hashlib.sha256(v['source_url'].encode()).hexdigest()).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == v['sha256'], (a['slug'], 'sha256')
                vs.append((f"{a['slug']} {v['from']}", v['units'], page_text(raw)))
    bad = letters_check(vs, None)
    for b in bad:
        print(b)
    print(f'{len(vs)} versions checked, {len(bad)} mismatches')
    return len(bad)


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1:] or sorted(str(p) for p in (HERE / 'corpus.d').glob('*.json'))) else 0)
