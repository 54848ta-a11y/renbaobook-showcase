s = open('index.html', encoding='utf-8').read()
print('已外借:', s.count('"st": "已外借"'))
print('在馆:', s.count('"st": "在馆"'))
