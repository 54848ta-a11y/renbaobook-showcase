# -*- coding: utf-8 -*-
"""合并构建：把 books.json + borrowed.json 内联进 template.html，产出单文件 index.html。

borrowed.json 可为 JSON 数组，或纯文本（每行一个书名）。
规则（与人工更新一致）：先全部重置为「在馆」，再按书名逐条标 1 本「已借出」，
标记数量严格等于清单条数；同名多副本只标一本（哪本无所谓）。
books.json 文件本身不会被改写，只读取。
"""
import os, json
from collections import defaultdict


def load_borrowed(path):
    if not os.path.exists(path):
        return []
    raw = open(path, encoding='utf-8').read().strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except Exception:
        pass
    return [l.strip() for l in raw.splitlines() if l.strip()]


def render_index(books_path, borrowed_path, template_path):
    tpl = open(template_path, encoding='utf-8').read()
    data = json.load(open(books_path, encoding='utf-8'))
    books = data['books']
    borrowed = load_borrowed(borrowed_path)

    by_title = defaultdict(list)
    for b in books:
        by_title[b['t']].append(b)
    # 1. 全部重置为「在馆」
    for b in books:
        b['st'] = '在馆'
    # 2. 按书名逐条标 1 本「已借出」
    marked = 0
    for t in borrowed:
        matches = by_title.get(t, [])
        target = None
        for m in matches:
            if m['st'] != '已借出':
                target = m
                break
        if target is None and matches:
            target = matches[0]
        if target:
            target['st'] = '已借出'
            marked += 1

    js = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    marker = '/*__BOOKS_DATA__*/{}'
    assert marker in tpl, '模板占位符未找到'
    return tpl.replace(marker, js, 1), marked


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    out, marked = render_index(
        os.path.join(here, 'books.json'),
        os.path.join(here, 'borrowed.json'),
        os.path.join(here, 'template.html'))
    dst = os.path.join(here, 'index.html')
    open(dst, 'w', encoding='utf-8').write(out)
    print(f'已生成 {dst} ({os.path.getsize(dst)//1024} KB)，标记已借出 {marked} 本')
