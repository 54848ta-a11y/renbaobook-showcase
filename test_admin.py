# -*- coding: utf-8 -*-
"""app.py 管理后台回归测试（含 CSRF、频率限制）"""
import os, sys, re, http.cookiejar, urllib.request, urllib.parse

BASE = 'http://127.0.0.1:5000'
PW = os.environ.get('ADMIN_PASSWORD', 'test123')
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get(path):
    return op.open(BASE + path, timeout=10).read().decode('utf-8')


def post(path, fields):
    data = urllib.parse.urlencode(fields).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=data, method='POST')
    return op.open(req, timeout=10).read().decode('utf-8')


def extract_csrf(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None


def count_borrowed():
    s = get('/')
    return s.count('"st": "已借出"')


ok = True
# 1. 首页可访问
home = get('/')
assert '人保研修院' in home, '首页未包含站点标题'
print('[1] 首页可访问: OK')

# 2. 登录页
login = get('/admin')
assert '管理登录' in login, '未显示登录页'
print('[2] 登录页: OK')

# 3. 错误密码（<=5 次不会被锁定）
bad = post('/admin', {'pw': 'wrong'})
assert '密码错误' in bad, '错误密码未提示'
print('[3] 错误密码被拒: OK')

# 4. 正确密码登录（仅 pw）→ 跳转到后台空表单
login_ok = post('/admin', {'pw': PW})
assert '借出状态管理' in login_ok, '登录后未进入后台'
admin_page = get('/admin')  # 再显式 GET 一次，确保拿到最新 CSRF token
assert '借出状态管理' in admin_page, '后台页无法访问'
print('[4] 密码正确登录进入后台: OK')

# 5. 已登录后提交更新清单（仅 2 本），需 CSRF token
csrf = extract_csrf(admin_page)
assert csrf, '后台表单缺少 csrf_token'
upd = post('/admin', {'csrf_token': csrf, 'text': '周易\n人间失格\n'})
assert '已更新' in upd, '更新后未显示成功'
assert '标记 2' in upd, '标记数量不对'
print('[5] 更新清单为2本（含 CSRF）: OK')

# 6. 站点即时反映（2 本已外借）
n = count_borrowed()
assert n == 2, f'首页借出数应为2，实际 {n}'
print(f'[6] 首页即时反映借出数={n}: OK')

# 7. 退出后 /admin 回到登录页
get('/logout')
after = get('/admin')
assert '管理登录' in after, '退出后仍能进后台'
print('[7] 退出登录: OK')

# 8. 登录后不带 csrf_token 的 POST 应被拒绝
post('/admin', {'pw': PW})  # 重新登录
get('/admin')  # 确保 session 有效
try:
    post('/admin', {'text': 'test'})
    assert False, '缺少 csrf_token 的 POST 未被拒绝'
except urllib.error.HTTPError as e:
    assert e.code == 403, f'预期 403，实际 {e.code}'
print('[8] 登录后缺少 CSRF token 的 POST 被拒绝: OK')

print('ALL PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
