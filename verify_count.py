s = open('index.html', encoding='utf-8').read()
print('已借出:', s.count('"st": "已借出"'))
print('在馆:', s.count('"st": "在馆"'))
