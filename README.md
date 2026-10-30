# Mato Grosso do Sul: law history in git

The law of the State of Mato Grosso do Sul (Estado de Mato Grosso do Sul) (Brazil) as a git history: one file per Artigo, one paragraph per line, so `git blame`, `git log` and `git diff` work line by line. The text is Portuguese, the only official language.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law).

## What this repository holds

| Folder | Act | Versions |
| --- | --- | ---: |
| `constituicao/` | Constituição do Estado de Mato Grosso do Sul (5 October 1989), text in force, with the Ato das Disposições Constitucionais Gerais e Transitórias (`adt-*`) | 1 |
| `lc-<year>-<number>/` | the Leis Complementares in the state's legislation base, except those revoked as a whole (every article struck through) | 1 each |

An act the base shows no alteration for is given **as enacted**, credited to the act itself. An altered act is given **only as its text in force**, credited to the publisher as the oldest version available: the wordings in between are not reconstructed yet, so no earlier version is shown rather than a wrong one. Ordinary Leis, decrees and the Emendas Constitucionais as acts are not included yet.

## Source

[Consultar Legislação Governadoria](https://aacpdappls.net.ms.gov.br/appls/legislacao/secoge/govato.nsf), published by the Governo do Estado de Mato Grosso do Sul (Consultar Legislação, Governadoria). Each version names the page it was taken from and that page's sha256, in `data/versions.json`.

## Dates

An unaltered Lei Complementar is dated by its publication in the Diário Oficial as the page states it ("Publicada no Diário Oficial nº ..., de ..."). The text in force is dated by the latest date among the alterations the publisher's notes cite ("(redação dada pela EC nº ..., publicada no Diário Oficial ...)", "(acrescentado pela ...)", "(revogado pela ...)", "(declarado inconstitucional ...)"), up to the day it was retrieved: a change announced for later ("revogado a partir de 1º de janeiro de 2027", beside "OBS: Dispositivo vigente até 31 de dezembro de 2026") is not yet in the text and does not date it. "Vide" and "Obs" notes do not date a version. Commits are at noon in Campo Grande.

## How it is built

Lexifina reads the sources listed here and records each act's dated versions, and the laws that made each change, in one corpus file. `tools/build.py` writes this repository from that file, and the same corpus always gives the same commit hashes; `REPRODUCE.md` gives the details and the checks. A model (Claude) wrote Lexifina's code; it wrote no legal text, and no model runs when the history is built.

The page becomes one file per Art.; articles of the Ato das Disposições Constitucionais Gerais e Transitórias are `adt-*`. Headings of the Títulos, Capítulos and Seções stand above the first article under them; `000-titulo.md` holds the title, the ementa and the preamble. For the text in force, the earlier wordings the page strikes through, the alteration notes in parentheses and the publisher's remarks (in red, such as "Obs: O Plenário do Supremo Tribunal Federal ...") are left out, as are its notice that the texts are informative only and its line "Texto Constitucional promulgado em 5 de outubro de 1989, consolidado com as alterações adotadas pelas Emendas Constitucionais."

## How it is checked

Every version is read back from git on the day it took effect (`tools/check_repo.py`) and must match the corpus; an independent letters-and-digits comparison of every version against the source page must show no difference. Results are in `REPRODUCE.md`.

## What "author" means

The author of each commit is the law that made the text, or, for a consolidated text, the publisher, with an e-mail address that cannot exist; the committer is always Lexifina.

## Limits

Not a complete history: the Constituição starts at its text in force. The text is not the official version: only the Diário Oficial do Estado is authoritative. Text after the last article (place, date, signatures) stays in the last article's file.

## Licence

See [LICENSE](LICENSE): Brazilian law texts are not protected by copyright (Lei 9.610/1998, art. 8, IV). Fonte: Consultar Legislação Governadoria, Governo do Estado de Mato Grosso do Sul (Consultar Legislação, Governadoria).
