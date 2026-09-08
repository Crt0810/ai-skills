# -*- coding: utf-8 -*-
"""PDF 文献批量重命名 Skill 第 1 步: 抽取全部 PDF 的首页/次页文本与元数据。

用法:
    python pdf_extract.py --root <文献根目录> --meta1 <文本jsonl> --meta2 <元数据jsonl>

输出:
    meta1.jsonl  每行 {file, p1(首页前4000字符), p2(次页前2000字符), err}
    meta2.jsonl  每行 {file, title, author, cdate, npages, err}
"""
import os, json, warnings, logging, re, argparse
from pypdf import PdfReader

warnings.filterwarnings('ignore')
logging.getLogger('pypdf').setLevel(logging.CRITICAL)
for name in list(logging.root.manager.loggerDict):
    logging.getLogger(name).setLevel(logging.CRITICAL)


def clean(s):
    if s is None:
        return ''
    if not isinstance(s, str):
        s = str(s)  # creation_date 可能是 datetime 对象
    s = re.sub(r'[\ud800-\udfff]', '', s)  # Unicode 代理对会破坏 JSON
    return s.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='文献根目录(递归扫描)')
    ap.add_argument('--meta1', required=True, help='文本 jsonl 输出路径')
    ap.add_argument('--meta2', required=True, help='元数据 jsonl 输出路径')
    args = ap.parse_args()

    rows1, rows2, count = [], [], 0
    for dirpath, dirs, files in os.walk(args.root):
        for fn in files:
            if not fn.lower().endswith('.pdf'):
                continue
            full = os.path.join(dirpath, fn)
            count += 1
            r1 = {'file': full}
            r2 = {'file': full}
            try:
                r = PdfReader(full, strict=False)
                try:
                    r1['p1'] = clean((r.pages[0].extract_text() or ''))[:4000]
                except Exception:
                    r1['p1'] = ''
                if len(r.pages) > 1:
                    try:
                        r1['p2'] = clean((r.pages[1].extract_text() or ''))[:2000]
                    except Exception:
                        r1['p2'] = ''
                md = r.metadata
                if md:
                    try:
                        r2['title'] = clean(md.title or '')
                    except Exception:
                        r2['title'] = ''
                    try:
                        r2['author'] = clean(md.author or '')
                    except Exception:
                        r2['author'] = ''
                    try:
                        cd = md.creation_date
                        r2['cdate'] = clean(cd) if cd is not None else ''
                    except Exception:
                        r2['cdate'] = ''
                try:
                    r2['npages'] = len(r.pages)
                except Exception:
                    r2['npages'] = ''
            except Exception as e:
                err = str(e)[:200]
                r1['err'] = err
                r2['err'] = err
            rows1.append(r1)
            rows2.append(r2)
            if count % 300 == 0:
                print('progress', count, flush=True)

    with open(args.meta1, 'w', encoding='utf-8') as f:
        for rec in rows1:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    with open(args.meta2, 'w', encoding='utf-8') as f:
        for rec in rows2:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('DONE total=%d meta1=%s meta2=%s' % (len(rows1), args.meta1, args.meta2), flush=True)


if __name__ == '__main__':
    main()
