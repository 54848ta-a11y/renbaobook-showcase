import json
from collections import defaultdict

# 未盘点（已外借）清单 第2轮_24册 —— 按书名匹配，每条只标 1 本
borrowed_titles = [
    "周易",
    "中共党史简明读本",
    "法哲学：价值与事实",
    "小白经济学",
    "公关生涯：从小白到国际公关人：small guard, big heart",
    "清单革命：如何持续、正确、安全地把事情做好：how to get things right",
    "有钱人想的和你不一样：3000位富豪亲述成为有钱人的“价值标准”",
    "周国平致家长：做不焦虑的父母",
    "努力，是为了不辜负自己",
    "人间失格",
    "被欺凌与被侮辱的",
    "简·爱",
    "控方证人",
    "一生",
    "飘．PART1",
    "飘．PART2",
    "有趣有料忘不掉的中国史",
    "士人走向民间：宋元变革与社会转型",
    "苏东坡传",
    "普通家庭投资理财组合：人人皆可财富自由",
    "南怀瑾的32堂国学课",
    "《流浪地球》的数理化",
    "极简量子大观",
    "文明的盛宴：典藏版",
]

with open('books.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

books = data['books']

# 1. 全部重置为「在馆」
for b in books:
    b['st'] = '在馆'

# 2. 建立书名索引
by_title = defaultdict(list)
for b in books:
    by_title[b['t']].append(b)

# 3. 按书名匹配，每条只标 1 本
marked = 0
not_found = []
for t in borrowed_titles:
    matches = by_title.get(t, [])
    if not matches:
        not_found.append(t)
        continue
    # 只标第一本（未标记的）
    target = None
    for m in matches:
        if m['st'] != '已外借':
            target = m
            break
    if target is None:
        target = matches[0]
    target['st'] = '已外借'
    marked += 1

print(f"按书名共标记 {marked} 本为「已外借」")
if not_found:
    print(f"未找到 {len(not_found)} 本：")
    for t in not_found:
        print(f"  {t}")

from collections import Counter
status_counts = Counter(b['st'] for b in books)
print(f"\n状态统计：{dict(status_counts)}")

with open('books.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

print("\nbooks.json 已更新")
