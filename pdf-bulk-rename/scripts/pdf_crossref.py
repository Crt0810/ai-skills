# -*- coding: utf-8 -*-
"""PDF 文献批量重命名 Skill 第 2 步(可选): 对计划模式中 SKIP 的真实论文按 DOI/标题查 Crossref 补全。

用法:
    python pdf_crossref.py --meta1 <meta1.jsonl> --meta2 <meta2.jsonl> --plan <计划csv> --out <crossref.jsonl>

说明:
    - 只查询计划 CSV 中状态为 SKIP 的文件(已识别的不查)。
    - DOI 优先 (api.crossref.org/works/<doi>), 其次按标题模糊查询 (query.bibliographic)。
    - 缓存可增量: 已有 --out 时续读, 已含 title 的条目跳过。
    - pick_best: 查询结果条目是作品本体(无 message 包裹), 需兼容两种形态。
"""
import os, re, json, csv, time, argparse, urllib.request, urllib.parse

MAILTO = 'doubao-research@example.com'

# 期刊名 -> 规范缩写 (按长度降序匹配)
ABBR = {
    'Physical Review Letters': 'prl', 'Physical Review A': 'pra', 'Physical Review B': 'prb',
    'Physical Review C': 'prc', 'Physical Review D': 'prd', 'Physical Review E': 'pre',
    'Physical Review X': 'prx', 'Physical Review Research': 'prr', 'Physical Review Applied': 'prapplied',
    'Physical Review Materials': 'prm', 'PRX Quantum': 'prxquantum', 'Reviews of Modern Physics': 'rmp',
    'Nature Physics': 'np', 'Nature Communications': 'nc', 'Nature Photonics': 'nphotonics',
    'Nature': 'nature', 'Nature Nanotechnology': 'nnano', 'Nature Reviews Physics': 'natrevphys',
    'npj Quantum Information': 'npjqi', 'Communications Physics': 'commphys', 'Science': 'science',
    'Science Advances': 'sciadv', 'Scientific Reports': 'scirep', 'Applied Physics Letters': 'apl',
    'Journal of Applied Physics': 'jap', 'Journal of Chemical Physics': 'jcp', 'Applied Physics Express': 'apex',
    'AIP Advances': 'aipadv', 'AVS Quantum Science': 'avsqs', 'Optica': 'optica', 'Optics Express': 'oe',
    'Optics Letters': 'ol', 'Photonics Research': 'photonres', 'JOSA B': 'josab', 'New Journal of Physics': 'njp',
    'Journal of Physics A': 'jpa', 'Journal of Physics B': 'jpb', 'Journal of Physics: Condensed Matter': 'jpcm',
    'Journal of Physics: Conference Series': 'jpconf', 'Chinese Physics Letters': 'cpl', 'Chinese Physics B': 'cpb',
    'Communications in Theoretical Physics': 'ctp', 'Quantum Science and Technology': 'qst', 'Quantum': 'quantum',
    'Physica Scripta': 'physscr', 'EPL': 'epl', 'Annalen der Physik': 'annphys', 'Physics Reports': 'physrep',
    'Comptes Rendus Physique': 'crphys', 'Advanced Science': 'advs', 'International Journal of Theoretical Physics': 'ijtp',
    'Journal of Fluid Mechanics': 'jfm', 'Applied Magnetic Resonance': 'amr', 'Contemporary Physics': 'contphys',
    'Laser & Photonics Reviews': 'lpr', 'Laser & Optoelectronics Progress': 'lop', 'J. Infrared Millim. Waves': 'jirfmw',
    'IEEE': 'ieee', 'arXiv': 'arxiv', 'Chaos': 'chaos', 'National Science Review': 'nsr',
    'Reports on Progress in Physics': 'rep_prog', 'Optics and Lasers in Engineering': 'ole',
    'npj Quantum Materials': None, 'Science China': None, 'Optica Publishing Group': 'optica',
}
NAMES = sorted([k for k in ABBR if k], key=len, reverse=True)


def norm_journal(ct):
    if not ct:
        return None
    ct = ct.strip().strip('[]"')
    low = ct.lower()
    for name in NAMES:
        if name.lower() in low:
            return name
    return None


def http_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'research-script/1.0 (mailto:%s)' % MAILTO})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def title_key(t):
    if not t:
        return ''
    return re.sub(r'[^a-z0-9]+', '', t.lower())


def pick_best(items, title):
    tk = title_key(title)
    best = None
    for it in items:
        m = it.get('message') or it
        t = (m.get('title') or [''])[0]
        if not t:
            continue
        k = title_key(t)
        score = 0
        if k == tk:
            score = 3
        elif k and (k in tk or tk in k):
            score = 2
        elif title and (title_key(t[:40]) in tk or tk[:40] in k):
            score = 1
        if score > 0 and (best is None or score > best[0]):
            best = (score, t, m)
    return best


def extract(msg):
    t = (msg.get('title') or [''])[0]
    y = None
    issued = msg.get('issued', {}) or {}
    dp = issued.get('date-parts') or [[None]]
    if dp and dp[0] and dp[0][0]:
        y = str(dp[0][0])
    ct = (msg.get('container-title') or [''])[0]
    j = norm_journal(ct)
    return t, y, j


def looks_title(t):
    if not t:
        return False
    t = t.strip()
    if len(t) < 8:
        return False
    if re.match(r'^(fig|figure|response|reply|cover|index|目录|作业|讲义|图|表|实验|报告|答辩|简历|cv|表\d|图\d)', t, re.I):
        return False
    if not re.search(r'[A-Za-z]{4}', t):
        return False
    return True


def candidates_for(r, fn):
    p1 = r.get('p1', '') or ''
    stem = os.path.splitext(fn)[0]
    cands = []
    # 1) 文件名 (最可靠: 用户通常用标题命名)
    fs = re.sub(r'^(?:SM[_-]?|supplement(?:ary)?[_-]?)?(?:[_-]*)(.*)$', r'\1', stem, flags=re.I)
    fs = re.sub(r'[_-]+', ' ', fs)
    if looks_title(fs):
        cands.append(fs)
    # 2) 元数据标题
    t = r.get('title', '') or ''
    if t and looks_title(t):
        cands.append(t)
    # 3) 首页首行
    if p1:
        first = p1.strip().split('\n')[0].strip()
        if len(first) >= 10 and not re.match(r'^(this is the|downloaded|view|wiley|copyright|©|arxiv)', first, re.I):
            if looks_title(first):
                cands.append(first)
    return list(dict.fromkeys(cands))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--meta1', required=True)
    ap.add_argument('--meta2', required=True)
    ap.add_argument('--plan', required=True, help='计划CSV(读SKIP行)')
    ap.add_argument('--out', required=True, help='crossref 缓存 jsonl')
    args = ap.parse_args()

    recs = {}
    for mp in (args.meta1, args.meta2):
        with open(mp, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    recs.setdefault(r['file'], {}).update(r)

    targets = {}
    with open(args.plan, encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if row[0] == '旧文件全路径':
                continue
            if row[3] != 'SKIP':
                continue
            r = recs.get(row[0], {})
            if r.get('err'):
                continue
            targets[row[0]] = r
    print('候选文件数:', len(targets))

    results = {}
    already = set()
    if os.path.exists(args.out):
        with open(args.out, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    already.add(r['file'])
                    if r.get('title'):
                        results[r['file']] = r
    print('已有缓存:', len(already), '含标题:', len(results))

    n = 0
    for fpath, r in targets.items():
        if fpath in results and results[fpath].get('title'):
            continue
        p1 = r.get('p1', '') or ''
        p2 = r.get('p2', '') or ''
        fn = os.path.basename(fpath)
        stem = os.path.splitext(fn)[0]
        out = {'file': fpath}
        doi = None
        m = re.search(r'10\.\d{4,9}/[^\s\)\]"\']+', (p1 + p2)[:4000])
        if m:
            doi = m.group(0).rstrip('.,;')
        if not doi:
            s2 = re.sub(r'-(?:accepted|final|published|submitted|v\d+)$', '', stem, flags=re.I)
            m = re.match(r'^(s\d{5}-\d{2,3}-\d{5}-\d)$', s2, re.I)
            if m:
                doi = '10.1038/' + m.group(1)
            else:
                m = re.match(r'^PhysRev([A-Za-z]+)\.\d+\.\d+$', s2)
                if m:
                    doi = '10.1103/PhysRev' + m.group(1) + '.' + s2.split('.', 2)[2]
        try:
            if doi:
                msg = http_json('https://api.crossref.org/works/' + urllib.parse.quote(doi, safe='') + '?mailto=' + MAILTO).get('message')
                if msg:
                    t, y, j = extract(msg)
                    out.update({'doi': doi, 'title': t or '', 'year': y, 'journal': j, 'err': ''})
            else:
                cands = candidates_for(r, fn)
                found = False
                for title in cands:
                    q = urllib.parse.quote(title)
                    data = http_json('https://api.crossref.org/works?query.bibliographic=' + q + '&rows=4&select=title,container-title,issued&mailto=' + MAILTO)
                    items = data.get('message', {}).get('items', [])
                    b = pick_best(items, title)
                    if b:
                        t, y, j = extract(b[2])
                        out.update({'doi': '', 'title': t, 'year': y, 'journal': j, 'err': ''})
                        found = True
                        if b[0] >= 2:
                            break
                if not found:
                    out['err'] = 'no-match'
        except Exception as e:
            out['err'] = str(e)[:80]
        results[fpath] = out
        with open(args.out, 'a', encoding='utf-8') as f:
            f.write(json.dumps(out, ensure_ascii=False) + '\n')
        n += 1
        if n % 40 == 0:
            print('queried', n, flush=True)
        time.sleep(0.12)
    print('DONE queried=%d total=%d' % (n, len(results)))


if __name__ == '__main__':
    main()
