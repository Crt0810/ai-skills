# -*- coding: utf-8 -*-
"""PDF 文献批量重命名 Skill 第 3 步: 主流程(期刊识别/年份/标题/SM/Crossref/冲突处理, 计划+执行双模式).

用法:
    python pdf_rename.py --meta1 <meta1.jsonl> --meta2 <meta2.jsonl> \
        --crossref <crossref.jsonl> --plan <计划csv> --skiplist <未处理csv> [--execute]

    - 不带 --execute: 计划模式, 只写 CSV + 打印统计与抽样, 不改任何文件。
    - 带 --execute: 真正改名。仍失败的文件保留旧名, 已在计划 CSV 中记录。
    - 环境变量 NO_DISK_CHECK=1: 生成计划时跳过"目标已存在"检查(用于重跑对账)。
"""
import os, re, json, sys, csv, unicodedata, argparse

ap = argparse.ArgumentParser()
ap.add_argument('--meta1', required=True)
ap.add_argument('--meta2', required=True)
ap.add_argument('--crossref', default='')
ap.add_argument('--plan', required=True)
ap.add_argument('--skiplist', required=True)
ap.add_argument('--execute', action='store_true')
_args = ap.parse_args()
META1, META2, CROSSREF, PLAN, SKIPLIST = _args.meta1, _args.meta2, _args.crossref, _args.plan, _args.skiplist

ABBR = {
    'Physical Review Letters': 'prl',
    'Physical Review A': 'pra',
    'Physical Review B': 'prb',
    'Physical Review C': 'prc',
    'Physical Review D': 'prd',
    'Physical Review E': 'pre',
    'Physical Review X': 'prx',
    'Physical Review Research': 'prr',
    'Physical Review Applied': 'prapplied',
    'Physical Review Materials': 'prm',
    'Physical Review (old)': 'pr',
    'PRX Quantum': 'prxquantum',
    'Reviews of Modern Physics': 'rmp',
    'Nature Physics': 'np',
    'Nature Communications': 'nc',
    'Nature Photonics': 'nphotonics',
    'Nature': 'nature',
    'Nature Nanotechnology': 'nnano',
    'Nature Reviews Physics': 'natrevphys',
    'npj Quantum Information': 'npjqi',
    'Communications Physics': 'commphys',
    'Science': 'science',
    'Science Advances': 'sciadv',
    'Scientific Reports': 'scirep',
    'Applied Physics Letters': 'apl',
    'Journal of Applied Physics': 'jap',
    'Journal of Chemical Physics': 'jcp',
    'Applied Physics Express': 'apex',
    'AIP Advances': 'aipadv',
    'AVS Quantum Science': 'avsqs',
    'Optica': 'optica',
    'Optics Express': 'oe',
    'Optics Letters': 'ol',
    'Photonics Research': 'photonres',
    'JOSA B': 'josab',
    'New Journal of Physics': 'njp',
    'Journal of Physics A': 'jpa',
    'Journal of Physics B': 'jpb',
    'J. Phys.: Condensed Matter': 'jpcm',
    'J. Phys.: Conf. Series': 'jpconf',
    'Chinese Physics Letters': 'cpl',
    'Chinese Physics B': 'cpb',
    'Communications in Theoretical Physics': 'ctp',
    'Quantum Science and Technology': 'qst',
    'Quantum': 'quantum',
    'Physica Scripta': 'physscr',
    'EPL': 'epl',
    'Annalen der Physik': 'annphys',
    'Physics Reports': 'physrep',
    'Comptes Rendus Physique': 'crphys',
    'Advanced Science': 'advs',
    'International Journal of Theoretical Physics': 'ijtp',
    'Journal of Fluid Mechanics': 'jfm',
    'Applied Magnetic Resonance': 'amr',
    'Contemporary Physics': 'contphys',
    'Laser & Photonics Reviews': 'lpr',
    'Laser & Optoelectronics Progress': 'lop',
    'J. Infrared Millim. Waves': 'jirfmw',
    'IEEE': 'ieee',
    'arXiv': 'arxiv',
    'Chaos': 'chaos',
    'National Science Review': 'nsr',
}

# 知名论文兜底: title-key -> (abbr, year)
KNOWN = {
    'quantum limits on noise in linear amplifiers': ('prd', '1982'),
    'on the measurement of a weak classical force coupled to a quantum mechanical oscillator i issues of principle': ('rmp', '1980'),
    'four golden lessons': ('nature', '2003'),
}

INV_ABBR = {v: k for k, v in ABBR.items()}

# 旧文件/拼写错误缩写 -> 规范缩写
OLD_ABBR_MAP = {
    'nphoton': 'nphotonics', 'nphotonic': 'nphotonics', 'naturephotonics': 'nphotonics',
    'prappliad': 'prapplied', 'prapliad': 'prapplied', 'prap': 'prapplied',
    'prxq': 'prxquantum', 'prxquantum': 'prxquantum',
    'arxivl': 'arxiv', 'arxivp': 'arxiv',
    'sciencereports': 'scirep', 'sciadv': 'sciadv',
    'physrevlett': 'prl', 'physreva': 'pra', 'physrevb': 'prb', 'physrevd': 'prd',
    'physrevx': 'prx', 'physrevapplied': 'prapplied', 'revmodphys': 'rmp',
    'naturecomms': 'nc', 'natcomms': 'nc', 'naturephys': 'np', 'naturephot': 'nphotonics',
    'opticsexpress': 'oe', 'optlett': 'ol', 'opticsletters': 'ol',
    'applphyslett': 'apl', 'japplphys': 'jap',
    'josab': 'josab', 'quantum': 'quantum', 'epl': 'epl', 'njp': 'njp',
    'ieeejstqe': 'ieee', 'ieee': 'ieee', 'jlt': 'ieee', 'jqe': 'ieee',
}

# ---------- 加载 ----------
recs = {}
with open(META1, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            r = json.loads(line)
            recs[r['file']] = r
meta2 = {}
with open(META2, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            r = json.loads(line)
            meta2[r['file']] = r
for k in recs:
    if k in meta2:
        recs[k].update(meta2[k])

xref = {}
if os.path.exists(CROSSREF):
    with open(CROSSREF, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                if r.get('title'):
                    xref[r['file']] = r
print('Crossref缓存:', len(xref))

# ---------- 期刊检测 ----------
HEAD = []
def head(patterns, journal):
    for p in patterns:
        HEAD.append((re.compile(p), journal))

head([r'PHYSICAL\s+REVIEW\s+APPLIED', r'Phys\.\s*Rev\.\s*Applied'], 'Physical Review Applied')
head([r'PHYSICAL\s+REVIEW\s+RESEARCH', r'Phys\.\s*Rev\.\s*Research'], 'Physical Review Research')
head([r'PHYSICAL\s+REVIEW\s+MATERIALS', r'Phys\.\s*Rev\.\s*Materials'], 'Physical Review Materials')
head([r'PHYSICAL\s+REVIEW\s+X\s+QUANTUM', r'PRX\s+QUANTUM', r'PRX\s+Quantum'], 'PRX Quantum')
head([r'PHYSICAL\s+REVIEW\s+X', r'Phys\.\s*Rev\.\s*X'], 'Physical Review X')
head([r'PHYSICAL\s+REVIEW\s+LETTERS', r'Phys\.\s*Rev\.\s*Lett\.'], 'Physical Review Letters')
head([r'PHYSICAL\s+REVIEW\s+[A-E]\s+\d'], 'Physical Review ABCDE')
head([r'PHYSICAL\s+REVIEW\s+[A-Z]'], 'Physical Review (old)')
head([r'REVIEWS\s+OF\s+MODERN\s+PHYSICS', r'Rev\.\s*Mod\.\s*Phys\.'], 'Reviews of Modern Physics')
head([r'Nature\s+Physics', r'NATURE\s+PHYSICS'], 'Nature Physics')
head([r'Nature\s+Communications', r'NATURE\s+COMMUNICATIONS'], 'Nature Communications')
head([r'npj\s+Quantum\s+Information', r'NPJ\s+QUANTUM\s+INFORMATION'], 'npj Quantum Information')
head([r'Communications\s+Physics', r'COMMUNICATIONS\s+PHYSICS', r'communications\s+physics'], 'Communications Physics')
head([r'Nature\s+Photonics', r'NATURE\s+PHOTONICS'], 'Nature Photonics')
head([r'Nature\s+Nanotechnology', r'NATURE\s+NANOTECHNOLOGY'], 'Nature Nanotechnology')
head([r'Nature\s+Materials', r'NATURE\s+MATERIALS'], 'Nature Materials')
head([r'Nature\s+Reviews?\s+Physics', r'NATURE\s+REVIEWS?\s+PHYSICS'], 'Nature Reviews Physics')
head([r'npj\s+Quantum\s+Materials'], 'npj Quantum Materials')
head([r'Science\s+Advances', r'SCIENCE\s+ADVANCES'], 'Science Advances')
head([r'Applied\s+Physics\s+Letters', r'APPLIED\s+PHYSICS\s+LETTERS', r'Appl\.\s*Phys\.\s*Lett\.'], 'Applied Physics Letters')
head([r'Journal\s+of\s+Applied\s+Physics', r'J\.\s*Appl\.\s*Phys\.'], 'Journal of Applied Physics')
head([r'Journal\s+of\s+Chemical\s+Physics', r'J\.\s*Chem\.\s*Phys\.'], 'Journal of Chemical Physics')
head([r'AVS\s+Quantum\s+Science'], 'AVS Quantum Science')
head([r'\bOptica\b'], 'Optica')
head([r'Optics\s+Express', r'Opt\.\s*Express'], 'Optics Express')
head([r'Optics\s+Letters', r'Opt\.\s*Lett\.'], 'Optics Letters')
head([r'Photonics\s+Research'], 'Photonics Research')
head([r'JOSA\s+B', r'J\.\s*Opt\.\s*Soc\.\s*Am\.\s*B'], 'JOSA B')
head([r'New\s+Journal\s+of\s+Physics', r'New\s+J\.\s*Phys\.'], 'New Journal of Physics')
head([r'Journal\s+of\s+Physics\s*:\s*B', r'J\.\s*Phys\.\s*B'], 'Journal of Physics B')
head([r'Journal\s+of\s+Physics\s*:\s*A', r'J\.\s*Phys\.\s*A'], 'Journal of Physics A')
head([r'Journal\s+of\s+Physics\s*:\s*Condensed\s+Matter', r'J\.\s*Phys\.\s*:\s*Condens\.\s*Matter'], 'J. Phys.: Condensed Matter')
head([r'Journal\s+of\s+Physics\s*:\s*Conference\s+Series', r'J\.\s*Phys\.\s*:\s*Conf\.\s*Ser\.'], 'J. Phys.: Conf. Series')
head([r'Chinese\s+Physics\s+Letters', r'Chin\.\s*Phys\.\s*Lett\.'], 'Chinese Physics Letters')
head([r'Chinese\s+Physics\s*B', r'Chin\.\s*Phys\.\s*B'], 'Chinese Physics B')
head([r'Quantum\s+Science\s+and\s+Technology', r'Quantum\s+Sci\.\s*Technol\.'], 'Quantum Science and Technology')
head([r'Communications\s+in\s+Theoretical\s+Physics', r'Commun\.\s*Theor\.\s*Phys\.'], 'Communications in Theoretical Physics')
head([r'Physica\s+Scripta', r'Phys\.\s*Scr\.'], 'Physica Scripta')
head([r'Europhysics\s+Letters', r'EPL\s*,\s*\d'], 'EPL')
head([r'Annalen\s+der\s+Physik'], 'Annalen der Physik')
head([r'Physics\s+Reports', r'Phys\.\s*Rep\.'], 'Physics Reports')
head([r'Applied\s+Physics\s+Express', r'Appl\.\s*Phys\.\s*Express'], 'Applied Physics Express')
head([r'Comptes\s+Rendus\s+Physique'], 'Comptes Rendus Physique')
head([r'Scientific\s+Reports', r'Scientific\s+RepoRtS', r'Sci\.\s*Rep\.'], 'Scientific Reports')
head([r'AIP\s+Advances', r'AIP\s+Adv\.'], 'AIP Advances')
head([r'Advanced\s+Science', r'Adv\.\s*Sci\.'], 'Advanced Science')
head([r'Journal\s+of\s+Fluid\s+Mechanics', r'J\.\s*Fluid\s*Mech\.'], 'Journal of Fluid Mechanics')
head([r'International\s+Journal\s+of\s+Theoretical\s+Physics', r'Int\.\s*J\.\s*Theor\.\s*Phys\.'], 'International Journal of Theoretical Physics')
head([r'红外\s*与\s*毫米波\s*学报', r'J\.\s*Infrared\s*Millim\.\s*Waves'], 'J. Infrared Millim. Waves')
head([r'激光\s*与\s*光电子学\s*进展', r'Laser\s*&\s*Optoelectronics\s*Progress'], 'Laser & Optoelectronics Progress')
head([r'Laser\s*&\s*Photonics\s*Reviews', r'Laser\s+Photonics\s+Reviews', r'lpr-journal'], 'Laser & Photonics Reviews')
head([r'Contemporary\s+Physics'], 'Contemporary Physics')
head([r'Applied\s+Magnetic\s+Resonance', r'Appl\.\s*Magn\.\s*Reson\.'], 'Applied Magnetic Resonance')
head([r'Science\s+Magazine', r'www\.sciencemag\.org', r'VOL\s+\d+\s*,\s*\d+\s*\|\s*Science'], 'Science')
head([r'\bNature\s*VOL', r'\bNature\s*\|\s*'], 'Nature')
head([r'arXiv\s*:?\s*\d{4}\.\d{3,5}', r'arXiv\s*[a-z\-]+/\d{7}', r'10\.48550/arXiv'], 'arXiv')
head([r'Quantum\s+\d{1,3},\s*\d+\s*\(\d{4}\)'], 'Quantum')
head([r'Reports\s+on\s+Progress\s+in\s+Physics', r'Rep\.\s*Prog\.\s*Phys\.'], 'Reports on Progress in Physics')
head([r'Science\s+China'], 'Science China')
head([r'Optics\s+and\s+Lasers?\s+in\s+Engineering'], 'Optics and Lasers in Engineering')

DOI_MAP = [
    (r'10\.1103/PhysRevLett', 'Physical Review Letters'),
    (r'10\.1103/PhysRevApplied', 'Physical Review Applied'),
    (r'10\.1103/PhysRevResearch', 'Physical Review Research'),
    (r'10\.1103/PhysRevMaterials', 'Physical Review Materials'),
    (r'10\.1103/PhysRevX', 'Physical Review X'),
    (r'10\.1103/PhysRevA', 'Physical Review A'),
    (r'10\.1103/PhysRevB', 'Physical Review B'),
    (r'10\.1103/PhysRevC', 'Physical Review C'),
    (r'10\.1103/PhysRevD', 'Physical Review D'),
    (r'10\.1103/PhysRevE', 'Physical Review E'),
    (r'10\.1103/RevModPhys', 'Reviews of Modern Physics'),
    (r'10\.1103/PRXQuantum', 'PRX Quantum'),
    (r'10\.1038/s41567', 'Nature Physics'),
    (r'10\.1038/s41467', 'Nature Communications'),
    (r'10\.1038/s41534', 'npj Quantum Information'),
    (r'10\.1038/s41586', 'Nature'),
    (r'10\.1038/s42005', 'Communications Physics'),
    (r'10\.1038/s41566', 'Nature Photonics'),
    (r'10\.1038/s41578', 'Nature Reviews Physics'),
    (r'10\.1038/s41563', 'Nature Materials'),
    (r'10\.1038/s41565', 'Nature Nanotechnology'),
    (r'10\.1038/nphys', 'Nature Physics'),
    (r'10\.1038/ncomms', 'Nature Communications'),
    (r'10\.1038/s41598', 'Scientific Reports'),
    (r'10\.1126/sciadv', 'Science Advances'),
    (r'10\.1126/science', 'Science'),
    (r'10\.1364/OPTICA', 'Optica'),
    (r'10\.1364/OE', 'Optics Express'),
    (r'10\.1364/OL', 'Optics Letters'),
    (r'10\.1088/1367-2630', 'New Journal of Physics'),
    (r'10\.1088/0953-4075', 'Journal of Physics B'),
    (r'10\.1088/0256-307X', 'Chinese Physics Letters'),
    (r'10\.1088/1674-1056', 'Chinese Physics B'),
    (r'10\.1088/2058-9565', 'Quantum Science and Technology'),
    (r'10\.1088/0953-8984', 'J. Phys.: Condensed Matter'),
    (r'10\.1209/', 'EPL'),
    (r'10\.22331/q', 'Quantum'),
    (r'10\.48550/arXiv', 'arXiv'),
    (r'10\.1109/', 'IEEE'),
    (r'10\.1002/advs', 'Advanced Science'),
    (r'10\.1002/lpor', 'Laser & Photonics Reviews'),
    (r'10\.1016/j\.physrep', 'Physics Reports'),
    (r'10\.1007/s10773', 'International Journal of Theoretical Physics'),
    (r'10\.1017/jfm', 'Journal of Fluid Mechanics'),
    (r'10\.1088/0034-4885', 'Reports on Progress in Physics'),
]

# 全文本补充匹配（用于 DOI 命中但刊名不明确的 AIP/IEEE 等）
TEXT_FULL = [
    (r'Applied\s+Physics\s+Letters|Appl\.\s*Phys\.\s*Lett\.', 'Applied Physics Letters'),
    (r'Journal\s+of\s+Applied\s+Physics|J\.\s*Appl\.\s*Phys\.', 'Journal of Applied Physics'),
    (r'Journal\s+of\s+Chemical\s+Physics|J\.\s*Chem\.\s*Phys\.', 'Journal of Chemical Physics'),
    (r'AIP\s+Advances|AIP\s+Adv\.', 'AIP Advances'),
    (r'Applied\s+Physics\s+Express|Appl\.\s*Phys\.\s*Express', 'Applied Physics Express'),
    (r'AVS\s+Quantum\s+Science', 'AVS Quantum Science'),
]

AFFIL = re.compile(r'(department|university|universit|institute|institut|center\s+for|centre\s+for|school\s+of|laboratory|academy|faculty|college|key\s+laboratory|atominstitut|national\s+physical|theoretical\s+astrophysics|univ\.|inst\.)', re.I)

def detect_journal(rec):
    p1 = rec.get('p1', '') or ''
    p2 = rec.get('p2', '') or ''
    # 排除单位/机构行, 避免 "Center for Quantum Science and Technology" 之类误判
    head_lines = [l for l in p1.split('\n') if not AFFIL.search(l)]
    head_text = '\n'.join(head_lines)[:1000]
    for rx, j in HEAD:
        if rx.search(head_text):
            return j
    full = p1 + '\n' + p2
    # DOI: 取最早出现者（论文自身 DOI 通常在首页，参考文献 DOI 在后）
    best = None
    for doi_rx, j in DOI_MAP:
        for m in re.finditer(doi_rx, full[:3200], re.IGNORECASE):
            if best is None or m.start() < best[0]:
                best = (m.start(), j)
    if best:
        return best[1]
    # DOI 10.1063 -> 文本判定
    if re.search(r'10\.1063/', full[:3200], re.IGNORECASE):
        for t_rx, tj in TEXT_FULL:
            if re.search(t_rx, full, re.IGNORECASE):
                return tj
        return None
    return None

def split_pr_letter(rec):
    p1 = rec.get('p1', '') or ''
    m = re.search(r'PHYSICAL\s+REVIEW\s+([A-E])\s+\d', p1[:1000])
    if m:
        return 'Physical Review ' + m.group(1)
    return None

# ---------- 年份 ----------
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')

def extract_year(rec, journal):
    p1 = rec.get('p1', '') or ''
    p2 = rec.get('p2', '') or ''
    t = p1[:1200]
    # APS 页眉 (2026)
    m = re.search(r'PHYSICAL\s+REVIEW\s+[A-Z]+\s+\d+\s*,\s*\d+\s*\((\d{4})\)', t)
    if m:
        return m.group(1)
    m = re.search(r'PHYSICAL\s+REVIEW\s+[A-Z]+\s+\d+\s*,\s*\d+\s*\((\d{4})\)', p1[:4000])
    if m:
        return m.group(1)
    # 其他页眉 "Opt. Express 30, 12345 (2022)" (仅 Abstract/Received 之前的文本块, 排除 Phys Rev 引文)
    head_block = ''
    for _l in p1.split('\n'):
        if re.match(r'^(abstract|\(received|©|received)', _l.strip(), re.I):
            break
        head_block += _l + '\n'
    m = re.search(r'(?!Phys\.?\s*Rev\.?)[A-Z][\w\.\s&]{3,40}?\s+\d+\s*,\s*\d+\s*\((\d{4})\)', head_block[:1200])
    if m:
        return m.group(1)
    # arXiv ID (YYMM 前缀: 2505.06155 -> 2025)
    m = re.search(r'arXiv\s*:?\s*(\d{2})\d{2}\.\d{3,5}', t + p2[:300])
    if m:
        yy = m.group(1)
        return '20' + yy if int(yy) <= 50 else '19' + yy
    # DOI 年份 (Nature DOI 内嵌年份, 如 s41467-026-xxx -> 2026)
    m = re.search(r'10\.1038/(?:s\d{5}|[a-z]+)-(\d{2,3})-', t + p2[:800])
    if m:
        y = m.group(1)
        if len(y) == 2:
            return '20' + y
        return '20' + y[1:]
    # published / accepted / received
    for kw in (r'published', r'accepted', r'received', r'published on', r'online'):
        m = re.search(kw + r'\s+[^;()]*?((?:19|20)\d{2})', p1[:2000] + p2[:600], re.IGNORECASE)
        if m:
            return m.group(1)
    # (Received 29 May 2020)
    m = re.search(r'\(Received[^)]*?((?:19|20)\d{2})', p1[:2000] + p2[:600], re.IGNORECASE)
    if m:
        return m.group(1)
    # Dated:
    m = re.search(r'Dated:\s*[^,]*?,?\s*((?:19|20)\d{2})', p1[:1000], re.IGNORECASE)
    if m:
        return m.group(1)
    # © 年份
    m = re.search(r'[©©]\s*((?:19|20)\d{2})', p1[:2000] + p2[:600])
    if m:
        return m.group(1)
    # 通用兜底: 首页前1000字符内第一个不寻常的4位年份
    bad_ctx = re.compile(r'et al|rev\.|doi|10\.\d|references?|cited|citation|vol\.?\s*\d|issue|pages?', re.I)
    for line in p1.split('\n')[:12]:
        line = line.strip()
        if not line or bad_ctx.search(line):
            continue
        m = re.search(r'\b((?:19|20)\d{2})\b', line)
        if m and 1950 <= int(m.group(1)) <= 2030:
            return m.group(1)
    return None

# ---------- SM 检测 ----------
SM_NAME = re.compile(r'^(SM[_-]?|supp\w*|supporting|supplementary|supplement)', re.I)

def is_sm(rec):
    fn = os.path.basename(rec['file'])
    if SM_NAME.search(fn):
        return True
    p1 = (rec.get('p1', '') or '').strip()
    head = p1[:200]
    if re.search(r'^Supplement(al|ary|ary Material|ary Notes?|ary Information)|^Supporting Information|^Supplementary', head, re.IGNORECASE):
        return True
    return False

SM_PRE = re.compile(
    r'^(Supplement(al|ary)\s+Material[s]?\s*(for|for:|:|$)|Supplementary\s+(Information|Material[s]?|Notes?|Information\s+for|Material\s+for)\s*(for|for:|:|$)|'
    r'Supporting\s+Information\s*(for|for:|:|$)|Supplemental\s+Notes?\s*(for|:|$)|Supplementary\s*for|'
    r'Supplemental\s+Information\s+for|SM-|S\.M\.\s*for)', re.IGNORECASE)

def strip_sm_title(title):
    if not title:
        return title
    t = title.strip().strip('"“”\'')
    patterns = [
        re.compile(r'^(?:Supplemental\s+Material[s]?\s*|Supplementary\s+(?:Information|Material[s]?|Notes?)\s*|Supporting\s+Information\s*|Supplemental\s+(?:Information|Notes?)\s*|Supplementary\s*)\s*[:fF]or\s*["“\']?(.*?)["”\']?$', re.I),
        re.compile(r'^(?:Supplemental\s+Material[s]?\s*|Supplementary\s+(?:Information|Material[s]?|Notes?)\s*|Supporting\s+Information\s*|Supplemental\s+(?:Information|Notes?)\s*)\s*[:–—-]\s*(.*)$', re.I),
    ]
    for rx in patterns:
        m = rx.match(t)
        if m and m.group(1) and len(m.group(1).strip()) >= 5:
            return m.group(1).strip()
    return t

# ---------- 标题 ----------
# 标题尾部作者名后缀: "First Last et al" / "Wang, Lai, Yuan et al"
AUTH_SUFFIX = re.compile(
    r'\s+(?:[A-Z][A-Za-z.\-]+(?:\s+[A-Z][A-Za-z.\-]*)*(?:\s*,\s*[A-Z][A-Za-z.\-]+(?:\s+[A-Z][A-Za-z.\-]*)*)*)\s+et\s+al\.?\s*$')

def clean_title(t):
    if not t:
        return ''
    t = re.sub(r'[\ud800-\udfff]', '', t)
    t = t.replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
    t = re.sub(r'[\x00-\x1f\x7f]', ' ', t)
    t = re.sub(r'[\\/:*?"<>|]', ' ', t)  # Windows 非法字符 -> 空格
    t = re.sub(r'\s*[«»].*$', '', t)
    t = AUTH_SUFFIX.sub('', t)
    # 引用行前缀: "Giazotto, F. et al. Coherent ..." / "Zhang, L. et al. Quantum ..."
    m = re.match(r'^.*?\bet\s+al\.\s+', t)
    if m and len(t[m.end():]) >= 8:
        t = t[m.end():]
    # 整段 URL 当标题
    t = re.sub(r'^(?:https?|doi|www)\S*(?:\s+\S+)*', '', t)
    # 尾部 URL/DOI 残留 (先剥)
    t = re.sub(r'\s+(?:https?|doi|www)\S*(?:\s+\S+)*\s*$', '', t)
    # 尾部期刊+年份: "... effect. Nat Commun (2026)."
    t = re.sub(r'\.\s+[A-Z][\w\.\s&]{2,40}?\s*\((?:19|20)\d{2}\)\.?\s*$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = t.strip(' ._')
    return t

def title_key(t):
    if not t:
        return ''
    t = t.lower()
    t = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '', t)
    return t

BAD_META = re.compile(r'untitled|created by|microsoft|adobe|word document|pdf created|mupdf|wps|fontforge|scribus|view online|view the article|downloaded|full text|table of contents|homepage|article pdf|^article$|^download|^cite this article|^title$|^[a-z]{2,10}\d{3,6}\s+\d|^arxiv\s*\d', re.I)

def extract_title(rec):
    # 1) 元数据
    mt = rec.get('title', '') or ''
    mt = clean_title(mt)
    if 4 <= len(mt) <= 300 and not BAD_META.search(mt):
        return mt
    # 2) 文本启发式
    p1 = (rec.get('p1', '') or '').strip()
    if not p1:
        return ''
    lines = [re.sub(r'\s+', ' ', l).strip() for l in p1.split('\n')]
    lines = [re.sub(r'[\ue000-\uf8ff\u200b-\u200f\ufeff]', '', l) for l in lines]
    lines = [l.replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"') for l in lines]
    lines = [l for l in lines if l]

    SKIP_START = re.compile(
        r'^(physical\s+review|phys\.\s*rev\.|reviews\s+of\s+modern|nature|npj|communications\s+physics|communications\s+in\s+theoretical|'
        r'new\s+journal|journal\s+of\s+physics|j\.\s*phys\.|quantum\s+science|quantum\s+information|science\s+advances|scientific\s+reports|'
        r'optics|optica|applied\s+physics|appl\.\s*phys\.|aip|advanced\s+science|comptes\s+rendus|laser\s+photonics|laser\s*&\s*photonics|'
        r'contemporary\s+physics|physics\s+reports|phys\.\s*rep\.|europhysics|epl|annalen|chinese\s+physics|physica\s+scripta|'
        r'international\s+journal|j\.\s*fluid|appl\.\s*magn\.|prx\s+quantum|红外\s*与\s*毫米波\s*学报|激光\s*与\s*光电子学\s*进展|j\.\s*infrared|IEEE|journal\s+homepage|'
        r'volume\s+|vol\.\s*\d+|third\s+series|particles\s+and\s+fields|contents\s+lists|view\s+the\s+article|you\s+may\s+also\s+like|'
        r'research\s+article|review\s+article|review\s+of\s+scientific|rapid\s+communications|editors?\xe2\x80\x99\s*suggestion|editors?\x27\s*suggestion|'
        r'open\s+access|a\s+nature\s+portfolio\s+journal|check\s+for\s+updates|article|letter|letters|report|review|'
        r'received|accepted|published|submitted|dated:|corresponding|doi|https?://|www\.|[©©]|copyright|'
        r'abstract|contents|introduction|^\d{4}\s*年|\d+\s*卷|supplement|^arxiv\b|arxiv\s*[:.]?\s*\d{4}|quant-ph|'
        r'^view(\s+online)?$|^online$|^export(\s+citation)?$|^citation$|^crossmark|^download|^to\s+cite\s+this\s+article|^cite\s+this\s+article|'
        r'^view\s+the\s+article\s+online|^for\s+updates\s+and\s+enhancements|^open\s+the\s+article|^research\s+(article|letter|paper))\b', re.IGNORECASE)

    AUTHOR_LINE = re.compile(
        r'(department\s+of|university|universit|college|laboratory|laboratory|institute|institut|school\s+of|faculty|'
        r'key\s+laboratory|center\s+for|centre\s+for|academy|national\s+physical|theoretical\s+astrophysics|'
        r'moe\s+key|received|accepted|published|submitted|dated:|corresponding\s+author|\bemail|@|'
        r'[†‡§¶]|'
        r'^\s*;|'
        r',\s+(?:and|&)\s+[A-Z]|'
        r'\b[A-Z]\.\s*[A-Z]\.|'
        r'\b\d\s*[,，]\s*(?:and|&|[,\d†‡§¶*])|'
        r'[A-Za-z\u00c0-\u024f\'\-]+\s+[A-Za-z\u00c0-\u024f\'\-]+\s*;\s*[A-Z]|'
        r';\s*[A-Z][A-Za-z]|'
        r'\b[A-Z][a-z\-\']+\s*\d+\s*$|'
        r'^\s*[A-Z]\s*\.\s*[A-Za-z]|'
        r'(?:,\s*[A-Z][A-Za-z\u00c0-\u024f\.\-\' ]{2,40}){2,}\s*,|'
        r'^\s*[A-Z][A-Za-z.\-\u00c0-\u024f]*\s+(?:[A-Z][A-Za-z.\-\u00c0-\u024f]*\s+){0,3}[A-Z][A-Za-z.\-\u00c0-\u024f]*\s*[,，]\s*[1-9]|'
        r'^\s*[A-Z][A-Za-z.\-\u00c0-\u024f]*\s*[,，]\s*[1-9]|'
        r'^\s*[A-Za-z\u00c0-\u024f\'\-\.]+\s+[A-Za-z\u00c0-\u024f\'\-\.]+\s*[,，]\s*[1-9]|'
        r'[,，]\s*[†‡§¶*∗#]\s*$|'
        r'[,，]\s*\d{1,2}\s*$)', re.IGNORECASE)

    ABSTRACT_OPENER = re.compile(
        r'^(abstract|this (article|paper|work|letter|review)|here we|we (present|study|investigate|report|demonstrate|show|propose|introduce|develop|examine|analyze|discuss|review|derive|consider)|in this (article|paper|work)|the (paper|article|present|review)|a (major|general|brief|fundamental|powerful|simple|key|novel))', re.I)

    CATEGORY = {'optoelectronics', 'physics', 'materials science', 'research', 'report', 'reports', 'article', 'letters', 'letter', 'review', 'quantum electronics', 'nanotechnology', 'photonics', 'applied physics', 'chemistry', 'medicine', 'ecology'}

    cand = []
    for i, l in enumerate(lines[:30]):
        ll = l.strip()
        if len(ll) < 3:
            continue
        if re.fullmatch(r'[\d\s\.,:;\-\(\)\[\]\|/\\]+', ll):
            continue
        low = ll.lower()
        if SKIP_START.match(low):
            continue
        if AUTHOR_LINE.search(l):
            # 论文开头是机构行(学位论文/报告), 前3行允许跳过
            if i < 3 and re.match(r'^(university|department|college|institute|school|faculty|key\s+laboratory|center|centre|academy|national|laboratory|state\s+key|moe)', low):
                continue
            break
        if low in CATEGORY and len(ll) < 30 and i < 8:
            continue
        if re.fullmatch(r'[A-Z\s]{2,40}', ll) and i < 8 and len(ll.split()) <= 3:
            continue
        cand.append((i, ll))
        if len(cand) >= 1:
            break
    if not cand:
        return ''
    idx, t0 = cand[0]
    title = t0
    # 合并后续标题行
    for j in range(idx + 1, min(idx + 4, len(lines))):
        ll = lines[j].strip()
        if len(ll) < 3:
            break
        if AUTHOR_LINE.search(ll):
            break
        # 两词大写姓名行(+脚注标记) + 下一行是机构 -> 作者行
        if re.fullmatch(r'[A-Z][a-z]+\s+[A-Z][a-z]+\s*[*†‡§¶]?', ll) and j + 1 < len(lines) and AUTHOR_LINE.search(lines[j + 1]):
            break
        if j + 1 < len(lines) and re.match(r'^\s*;', lines[j + 1]):
            break  # 下一行是分号开头的作者名单
        if ABSTRACT_OPENER.match(ll) and len(title) >= 15:
            break
        if SKIP_START.match(ll.lower()) and not re.match(r'^[a-z0-9\u4e00-\u9fff]', ll):
            break
        if re.fullmatch(r'[\d\s\.,:;\-\(\)\[\]\|/\\]+', ll):
            break
        if len(title) + 1 + len(ll) > 220:
            break
        title += ' ' + ll
    title = clean_title(title)
    if len(title) < 5:
        return ''
    return title

# ---------- 旧文件名解析 ----------
def norm_abbr(a):
    a = a.lower().replace('_', '').replace('-', '')
    if a in INV_ABBR:
        return a
    if a in OLD_ABBR_MAP:
        return OLD_ABBR_MAP[a]
    # 去掉分隔符再比
    for k, v in OLD_ABBR_MAP.items():
        if a == k.replace('_', '').replace('-', ''):
            return v
    return None

OLD_NAME = re.compile(r'^(SM[_-])?([a-z0-9]+)[_-](\d{2,4})[_-](.+)$', re.I)

def old_year(y):
    y = y.strip()
    if len(y) == 2:
        n = int(y)
        return str(1900 + n) if n >= 80 else str(2000 + n)
    return y

def parse_old_name(fn):
    stem = os.path.splitext(fn)[0]
    m = OLD_NAME.match(stem)
    if not m:
        return None
    abbr = norm_abbr(m.group(2))
    if not abbr:
        return None
    year = old_year(m.group(3))
    title = m.group(4).strip()
    return (abbr, year, title)

def filename_year(fn):
    """文件名中形如 '-2016-标题' / '2016-arxiv-标题' 的年份兜底(旧式命名)."""
    stem = os.path.splitext(fn)[0]
    m = re.search(r'-((?:19|20)\d{2})-(.+)', stem)
    if m and m.group(2).strip():
        return m.group(1)
    m = re.match(r'^((?:19|20)\d{2})[-_](.+)$', stem)
    if m and m.group(2).strip():
        return m.group(1)
    return None

DOI_FN = [
    (re.compile(r'^(s\d{5}-\d{2,3}-\d{5}-\d)$', re.I), lambda m: '10.1038/' + m.group(1)),
    (re.compile(r'^PhysRev[A-Za-z]+\.\d+\.\d+$'), lambda m: '10.1103/' + m.group(0)),
    (re.compile(r'^PhysRevLett\.\d+\.\d+$'), lambda m: '10.1103/' + m.group(0)),
    (re.compile(r'^(10\.\d{4,9}/[^\s]+)$'), lambda m: m.group(1)),
]

def doi_from_filename(fn):
    stem = re.sub(r'-(?:accepted|final|published|submitted|v\d+)$', '', os.path.splitext(fn)[0], flags=re.I)
    for rx, mk in DOI_FN:
        m = rx.match(stem)
        if m:
            return mk(m)
    return None

# ---------- 主流程 ----------
def main(do_rename):
    rows = []  # file, abbr, year, title, is_sm, status, reason
    papers = {}  # file -> parsed
    order = sorted(recs.keys())

    for f in order:
        rec = recs[f]
        fn = os.path.basename(f)
        sm = is_sm(rec)
        reason = ''
        abbr = year = title = None

        # 读取失败 / 无文本
        if rec.get('err'):
            reason = 'PDF读取失败: ' + rec['err'][:80]
        else:
            journal = detect_journal(rec)
            if journal == 'Physical Review ABCDE':
                journal = split_pr_letter(rec) or journal
            if journal == 'Physical Review ABCDE':
                journal = None
            if journal and journal not in ABBR:
                journal = None
            # 知名论文兜底（先按文本标题）
            if not journal:
                ttl = extract_title(rec)
                if ttl:
                    k = title_key(ttl)
                    if k in KNOWN:
                        abbr, year = KNOWN[k]
                        title = ttl
            if journal:
                abbr = ABBR[journal]
                year = extract_year(rec, journal)
            # 标题
            ttl = extract_title(rec)
            if sm:
                ttl = strip_sm_title(ttl)
            if title is None:
                title = ttl
            if not abbr:
                # 旧文件名兜底
                old = parse_old_name(fn)
                if old:
                    abbr, year, old_title = old
                    if title is None or len(title) < 5:
                        title = old_title
                else:
                    # arXiv 编号文件名兜底, 如 "2404.13190.pdf" -> arxiv-2024
                    m = re.match(r'^(\d{4})\.\d{4,5}(v\d+)?$', os.path.splitext(fn)[0])
                    if m:
                        abbr, year = 'arxiv', m.group(1)
                    # 知名论文文件名兜底
                    elif title and title_key(title) in KNOWN:
                        abbr, year = KNOWN[title_key(title)]
                    else:
                        k = title_key(os.path.splitext(fn)[0])
                        if k in KNOWN:
                            abbr, year = KNOWN[k]
                            title = clean_title(os.path.splitext(fn)[0])
            # Crossref 兜底(论文缺期刊/年份/标题时, 或提取标题被污染时)
            if not sm:
                x = xref.get(f)
                if x:
                    xt = x.get('title')
                    if xt:
                        xk = title_key(xt)
                        tk = title_key(title)
                        if not tk or len(title) < 5 or (xk and xk in tk):
                            title = clean_title(xt)
                    if not abbr and x.get('journal') and x['journal'] in ABBR:
                        abbr = ABBR[x['journal']]
                    if not year and x.get('year') and re.fullmatch(r'(19|20)\d{2}', x['year'] or ''):
                        year = x['year']
            # 文件名年份兜底(旧式命名 peng-et-al-2016-...)
            if not year:
                fy = filename_year(fn)
                if fy:
                    year = fy
            if not year:
                reason = reason or '未识别年份'
            if not title or len(title) < 5:
                reason = reason or '未识别标题'
            if not abbr:
                reason = reason or '未识别期刊'

        papers[f] = {'sm': sm, 'abbr': abbr, 'year': year, 'title': title, 'reason': reason, 'file': f, 'fn': fn}

    # 建主论文 title-key -> (abbr, year, file)
    main_index = {}
    for f, p in papers.items():
        if p['sm'] or p['reason']:
            continue
        if p['abbr'] and p['year'] and p['title']:
            k = title_key(p['title'])
            if k:
                main_index.setdefault(k, (p['abbr'], p['year']))

    # SM 继承主论文缩写/年份 (标题来自提取结果或文件名)
    for f, p in papers.items():
        if p['sm'] and (p['reason'] or not p['abbr'] or not p['year']):
            cands = []
            if p['title']:
                cands.append(title_key(p['title']))
            fs = re.sub(r'^(SM[_-]?|supplement(ary)?[_-]?)', '', os.path.splitext(p['fn'])[0], flags=re.I)
            fs = re.sub(r'[_-]+', ' ', fs)
            cands.append(title_key(fs))
            for k in cands:
                if k and k in main_index:
                    p['abbr'], p['year'] = main_index[k]
                    p['reason'] = ''
                    if not p['title'] or len(p['title']) < 5:
                        p['title'] = re.sub(r'[_-]+', ' ', fs)
                    break

    # 生成目标名
    dir_used = {}
    results = []
    for f, p in papers.items():
        fn = p['fn']
        d = os.path.dirname(f)
        if p['reason'] or not (p['abbr'] and p['year'] and p['title']):
            results.append((f, fn, '', 'SKIP', p['reason'] or '无法识别'))
            continue
        t = clean_title(p['title'])
        if not t:
            results.append((f, fn, '', 'SKIP', '标题清洗后为空'))
            continue
        new_name = ('SM-' if p['sm'] else '') + p['abbr'] + '-' + p['year'] + '-' + t + '.pdf'
        if len(new_name) > 180:
            base = ('SM-' if p['sm'] else '') + p['abbr'] + '-' + p['year'] + '-'
            new_name = base + t[:180 - len(base) - 8].rstrip() + '.pdf'
        key = new_name.lower()
        used = dir_used.setdefault(d, set())
        n = 2
        base_wo_ext = new_name[:-4]
        while key in used or (not os.environ.get('NO_DISK_CHECK') and os.path.normcase(new_name) != os.path.normcase(fn) and os.path.exists(os.path.join(d, new_name))):
            new_name = base_wo_ext + '-' + str(n) + '.pdf'
            key = new_name.lower()
            n += 1
        used.add(key)
        if new_name.lower() == fn.lower():
            results.append((f, fn, new_name, '不变', ''))
        else:
            results.append((f, fn, new_name, 'RENAME', ''))

    # 写计划/清单
    with open(PLAN, 'w', encoding='utf-8-sig', newline='') as fcsv:
        w = csv.writer(fcsv)
        w.writerow(['旧文件全路径', '旧文件名', '新文件名', '状态', '备注'])
        for r in results:
            w.writerow(list(r))
    skipped = [r for r in results if r[3] == 'SKIP']
    with open(SKIPLIST, 'w', encoding='utf-8-sig', newline='') as fcsv:
        w = csv.writer(fcsv)
        w.writerow(['文件全路径', '原因', '文件名'])
        for f, fn, _, _, reason in skipped:
            w.writerow([f, reason, fn])

    from collections import Counter
    st = Counter(r[3] for r in results)
    print('计划: 总数=%d RENAME=%d 不变=%d SKIP=%d' % (len(results), st['RENAME'], st['不变'], st['SKIP']))

    if not do_rename:
        print('--- 抽样新名(前20) ---')
        for r in [x for x in results if x[3] == 'RENAME'][:20]:
            print(' ', os.path.basename(r[0]), '  =>  ', r[2])
        return results

    # 执行重命名（依赖顺序）
    todo = [(f, os.path.join(os.path.dirname(f), n)) for f, fn, n, s, _ in results if s == 'RENAME']
    ok = fail = 0
    failures = []
    while todo:
        moved = []
        for f, new in todo:
            try:
                if os.path.exists(new) and os.path.normcase(new) != os.path.normcase(f):
                    continue  # 目标被其他文件占用，下一轮再试
                os.rename(f, new)
                ok += 1
                moved.append((f, new))
            except Exception as e:
                failures.append((f, new, str(e)))
        if not moved:
            break  # 死循环保护
        done = set(id(f) for f, _ in moved)
        todo = [(f, n) for f, n in todo if id(f) not in done]
    print('执行: 成功=%d 失败=%d' % (ok, len(failures)))
    for f, n, e in failures[:30]:
        print('  FAIL', f, '->', n, e)
    print('未处理清单已写入:', SKIPLIST)
    print('重命名记录已写入:', PLAN)
    if failures:
        print('提示: 失败多为文件被其他程序占用(WinError 32), 关闭阅读器后重跑 --execute 即可补改。')

if __name__ == '__main__':
    main(_args.execute)
