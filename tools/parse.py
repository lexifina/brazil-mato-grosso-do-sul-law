"""Builds corpus.d parts for Mato Grosso do Sul from the retrieved pages of the state's legislation base (no network).

    python -X utf8 parse.py --today YYYY-MM-DD

The base (aacpdappls.net.ms.gov.br, Governadoria, "Consultar Legislação") keeps each act consolidated: earlier
wordings struck through (<s>), each alteration noted in parentheses, usually as a link ("(redação dada pela EC nº 22,
de 3 de setembro de 2003, publicada no Diário Oficial nº 6.075, de 5 de setembro de 2003, página 1)", "(acrescentado
pela ...)", "(revogado pela ...)", "(declarado inconstitucional ...)"). An altered act is given only as its text in
force, credited to the publisher as the oldest version available, dated by the latest date its notes cite; an act
with no such note and nothing struck through is given as enacted, credited to the act itself.
"""
import argparse, html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from br_lib import lines_of, units_of, write_part, sha, norm  # noqa: E402

CACHE = HERE / '.cache'
BASE = 'https://aacpdappls.net.ms.gov.br/appls/legislacao/secoge/govato.nsf/'
CONST = BASE + '0a67c456bc566b8a04257e590063f1fd/dfde24a4767ddcbf04257e4b006c0233?OpenDocument'
BLOCK = {'p', 'div', 'br', 'tr', 'li', 'table', 'tbody', 'thead', 'ul', 'ol', 'center', 'blockquote', 'h1', 'h2', 'h3',
         'h4', 'h5', 'h6'}
VOID = {'br', 'img', 'meta', 'link', 'hr', 'input', 'col', 'area', 'base', 'wbr'}
NOTE = re.compile(r'\(\s*(?:Nova\s+reda|Reda[çc]|Acresc|Revogad|Inclu[íi]d|Alterad|Renumerad|Suprimid|Vide\b|Vig[êe]n|'
                  r'Regulamentad|Modificad|Declarad|Suspens|Ver\b|Efic[áa]cia|Derrogad|Transformad|Prorrogad|'
                  r'Obs\b|Express[ãa]o|Express[õo]es)(?:[^()]|\([^()]*\))*\)', re.I)
BOILER = re.compile(r'^(?:\(\*\) Os textos contidos nesta base de dados.*|Texto Constitucional promulgado em .* consolidado '
                    r'com as altera[çc][õo]es adotadas pelas Emendas Constitucionais\.?)$', re.I)


class Split(HTMLParser):
    """The page split into the text as shown without struck-through runs, and the struck runs (a strike-through
    applies to everything inside it). Red text (nearest colour set above it) is the publisher's remarks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.kept, self.old, self.remarks = [], [], [], []

    def handle_starttag(self, tag, attrs):
        if tag in BLOCK:
            self.kept.append('<br>')
        if tag not in VOID:
            st = (dict(attrs).get('style') or '').lower()
            a = dict(attrs)
            cs = re.findall(r'(?<![-\w])color\s*:\s*([^;]+)', st) or ([a['color']] if a.get('color') else [])
            self.stack.append((tag, tag in ('s', 'strike', 'del') or 'line-through' in st,
                               cs[-1].strip().lower() if cs else None))

    def handle_endtag(self, tag):
        if tag in BLOCK:
            self.kept.append('<br>')
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, d):
        color = next((e[2] for e in reversed(self.stack) if e[2]), '')
        if any(e[1] for e in self.stack) and d.strip() not in ('º', '°', 'ª'):  # "n<s>º</s>": typography, kept
            self.old.append(d)
        elif color in ('#ff0000', 'red'):
            self.remarks.append(d)  # the publisher's remarks ("Obs: O Plenário do Supremo Tribunal Federal ...")
        else:
            self.kept.append(html.escape(d, quote=False))


def body(h):
    h = re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->|<head\b.*?</head>', '', h)
    i = h.lower().find('<body')
    return h[h.index('>', i) + 1:] if i >= 0 else h


def split(h):
    p = Split()
    p.feed(body(h))
    p.close()
    lines, notes = [], []
    for kind, l in lines_of(''.join(p.kept)):
        notes += NOTE.findall(l)
        l = norm(NOTE.sub(' ', l))
        if re.match(r'(?i)OBS\s*[:.]', l):
            notes.append(l)  # the publisher's remark, such as "OBS: Dispositivo vigente até 31 de dezembro de 2026."
            continue
        if not l or not re.search(r'\w', l) or BOILER.match(l):
            continue
        lines.append((kind, l))
    return lines, notes, norm(''.join(p.old))


DMY = re.compile(r'\b(\d{1,2})[º°]?\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{4}|\d{2})\b')
MONTHS = {m: i + 1 for i, m in enumerate(['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
                                           'setembro', 'outubro', 'novembro', 'dezembro'])}
LONG = re.compile(r'\b(\d{1,2})[º°o]?\s+de\s+(' + '|'.join(MONTHS) + r')\s+de\s+(\d{4})', re.I)


def year(y):
    y = int(y)
    return y if y > 99 else (2000 + y if y <= 40 else 1900 + y)


def dates(s):
    out = [f'{year(y):04d}-{int(mo):02d}-{int(d):02d}' for d, mo, y in DMY.findall(s) if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31]
    out += [f'{int(y):04d}-{MONTHS[mo.lower()]:02d}-{int(d):02d}' for d, mo, y in LONG.findall(s)]
    return out


def is_alteration(n):
    return not re.match(r'^\(\s*(Vide|Ver\b|Regulamentad|Vig[êe]n|Obs\b)', n, re.I)


COUNTRY = {
    'code': 'BR-MS', 'name': 'Mato Grosso do Sul', 'slug': 'brazil-mato-grosso-do-sul', 'lang': 'pt',
    'tz': 'America/Campo_Grande', 'future_branch': 'futuro',
    'publisher': {'name': 'Governo do Estado de Mato Grosso do Sul (Consultar Legislação, Governadoria)',
                  'email': 'legislacao@ms.gov.br.invalid'},
    'default_in_force_rule': {
        'text': 'Decreto-Lei 4.657/1942 (LINDB) art. 1: unless it says otherwise, a law takes effect 45 days after its '
                'official publication. Mato Grosso do Sul laws almost always say "Esta Lei entra em vigor na data de '
                'sua publicação"; this record dates each act as enacted by its publication in the Diário Oficial (the '
                'Constituição by its promulgation, 5 October 1989).',
        'source': 'https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm'},
    'licence_note': 'Texts: Governo do Estado de Mato Grosso do Sul, Consultar Legislação (Governadoria), '
                    'aacpdappls.net.ms.gov.br. Lei 9.610/1998 art. 8 IV: the texts of laws and other official acts are '
                    'not protected by copyright. Non-official text ("Os textos contidos nesta base de dados têm caráter '
                    'meramente informativo"): only the Diário Oficial is authoritative.',
}
DECISIONS = [
    'An altered act is given only as its text in force, credited to the publisher as the oldest version available and '
    'dated by the latest date its alteration notes cite (for an amendment, usually its publication in the Diário '
    'Oficial; for a ruling, the date of the decision or of its publication). The wordings in between are not '
    'reconstructed yet, so no earlier version is given rather than a wrong one. An act with no alteration note and '
    'nothing struck through is given as enacted, credited to the act itself.',
    'The text in force leaves out what the page strikes through (earlier wordings, and notes of superseded '
    'alterations) and the notes in parentheses ("(redação dada pela ...)", "(acrescentado pela ...)", "(revogado pela '
    '...)", "(declarado inconstitucional ...)", "(expressão declarada inconstitucional ...)", "(Obs...)"); "Vide" and '
    '"Obs" notes do not date a version, nor does a date after the retrieval day (a change announced for later, such as '
    '"(revogado a partir de 1º de janeiro de 2027 pela EC nº 97 ...)" beside "OBS: Dispositivo vigente até 31 de dezembro '
    'de 2026.": the text shown is still in force). The publisher\'s "OBS:" remarks are left out. Words the page shows '
    'in italics (new wordings) are kept as text. The notice '
    '"(*) Os textos contidos nesta base de dados têm caráter meramente informativo..." and the line "Texto '
    'Constitucional promulgado em 5 de outubro de 1989, consolidado com as alterações adotadas pelas Emendas '
    'Constitucionais." are left out.',
    'A struck-through ordinal sign on its own ("n<s>º</s>") is the page\'s typography, not an earlier wording, and is '
    'kept. A Lei Complementar whose every article is struck through has been revoked as a whole and is left out, as is '
    'an altered one whose notes cite no date. "(VETADO)" is part of the enacted text and is kept.',
    'One file per Art. (articles of the Ato das Disposições Constitucionais Gerais e Transitórias as adt-*); headings of the '
    'Títulos, Capítulos and Seções stand above the first article under them; "000-titulo" holds the title, the ementa '
    'and the preamble. Text after the last article (place, date, signatures) stays with the last article.',
]
AI = ["Claude Code (claude-opus-5-5) wrote Lexifina's code and chose the sources. No model output is used as legal "
      "text or dates: every word comes from the Mato Grosso do Sul legislation base."]


def raw(url):
    p = CACHE / 'raw' / sha(url.encode())
    return p.read_bytes() if p.exists() else None


def constitution(today):
    b = raw(CONST)
    lines, notes, old = split(b.decode('cp1252', 'replace'))
    first = '1989-10-05'
    # A date after the retrieval day announces a change the text does not show yet ("revogado a partir de 1º de
    # janeiro de 2027", next to "OBS: Dispositivo vigente até 31 de dezembro de 2026"): it does not date the text.
    alter = sorted(d for x in notes if is_alteration(x) for d in dates(x) if first < d <= today)
    units = units_of(lines, adt=True)
    law = 'constituicao-1989'
    laws = {law: {'label': 'Constituição do Estado de Mato Grosso do Sul', 'title': 'Constituição do Estado de Mato Grosso '
                  'do Sul de 1989', 'kind': 'law', 'enacted': first, 'published': None, 'url': CONST,
                  'temporary_until': None, 'restores': None, 'note': None}}
    v = {'from': alter[-1], 'source_url': CONST, 'sha256': sha(b), 'units': units,
         'note': f'Text in force as consolidated by the Governo do Estado de Mato Grosso do Sul; the Constituição was '
                 f'altered on {len(set(alter))} date(s) its notes cite, the latest {alter[-1]}.'}
    act = {'slug': 'constituicao', 'short': 'CE-MS', 'title': 'Constituição do Estado de Mato Grosso do Sul', 'url': CONST,
           'first_law': None, 'earlier_laws': [law], 'versions': [v]}
    return act, laws


def hidden(s, name):
    m = re.search(r'<input name="' + name + r'" type="hidden" value="([^"]*)"', s)
    return norm(html.unescape(m.group(1))) if m else ''


def lc_of(url, today):
    b = raw(url)
    if b is None:
        return None, {}, 'not fetched'
    s = b.decode('cp1252', 'replace')
    head = hidden(s, 'Ato_DspNum')
    m = re.search(r'(?i)LEI\s+COMPLEMENTAR\s+N[º°o.]*\s*(\d+)', head)
    ds = dates(head)
    if not m or not ds:
        return None, {}, 'no number or date'
    n, enacted = int(m.group(1)), ds[0]
    pub = dates(hidden(s, 'Ato_DspNumDO'))
    published = pub[0] if pub and pub[0] >= enacted else None
    lines, notes, old = split(s)
    units = units_of(lines, adt=False)
    if not any(k.startswith('art-') for k in units):
        return None, {}, 'no article left (wholly revoked: every article struck through)'
    first = published or enacted
    alts = [x for x in notes if is_alteration(x)]
    alter = sorted(d for x in alts for d in dates(x) if first < d <= today)
    if alts and not alter:
        return None, {}, 'altered, no dated note'
    y = enacted[:4]
    slug = law = f'lc-{y}-{n:03d}'
    label = f'Lei Complementar nº {n}, de {enacted[8:10]}/{enacted[5:7]}/{y}'
    ementa = hidden(s, 'Ato_DspEmenta')
    laws = {law: {'label': label, 'title': ementa or label, 'kind': 'law', 'enacted': enacted, 'published': published,
                  'url': url, 'temporary_until': None, 'restores': None, 'note': None}}
    v = {'from': alter[-1] if alter else first, 'source_url': url, 'sha256': sha(b), 'units': units}
    if alter:
        v['note'] = (f'Text in force as consolidated by the Governo do Estado de Mato Grosso do Sul; {label} was altered '
                     f'on {len(set(alter))} date(s) its notes cite, the latest {alter[-1]}.')
    act = {'slug': slug, 'short': f'LC {n}/{y}', 'title': label + (f' ({ementa})' if ementa and len(ementa) < 160 else ''),
           'url': url, 'first_law': None if alter else law, 'earlier_laws': [law] if alter else [], 'versions': [v]}
    return act, laws, 'ok'


def part(name, acts, laws, today):
    c = {'country': COUNTRY,
         'sources': [{'name': 'Governo do Estado de Mato Grosso do Sul, Consultar Legislação (Governadoria): the page of '
                              'each act', 'url': BASE, 'retrieved': today, 'licence': COUNTRY['licence_note'],
                      'notes': f'{len(acts)} acts in this part.'}],
         'laws': laws, 'acts': acts, 'applies': [], 'decisions': DECISIONS, 'ai_use': AI}
    return write_part(HERE / 'corpus.d', name, c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--today', required=True)
    ap.add_argument('--part-size', type=int, default=50)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    act, laws = constitution(a.today)
    print(part('10-constituicao', [act], laws, a.today), act['versions'][0]['from'], len(act['versions'][0]['units']))
    idx = CACHE / 'lc-index.json'
    if not idx.exists() or not (CACHE / 'fetch-done').exists():
        return
    acts, why = {}, {}
    for r in json.loads(idx.read_text(encoding='utf-8')):
        act, l, w = lc_of(r['url'], a.today)
        why[w] = why.get(w, 0) + 1
        if act and act['slug'] not in acts:
            acts[act['slug']] = (act, l)
    print(why)
    order = sorted(acts.values(), key=lambda x: (next(iter(x[1].values()))['enacted'], x[0]['slug']))
    for i in range(0, len(order), a.part_size):
        if a.dry:
            break
        chunk = order[i:i + a.part_size]
        laws = {}
        for _, l in chunk:
            laws.update(l)
        print(part(f'20-lc-{i // a.part_size + 1:02d}', [x[0] for x in chunk], laws, a.today), len(chunk))


if __name__ == '__main__':
    main()
