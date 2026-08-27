# -*- coding: utf-8 -*-
"""
人保研修院借阅室 · 展示站 + 借出状态自助管理后台（安全加固版）

- GET  /                展示站（单文件 index.html，启动时按 borrowed.json 构建）
- GET  /<prefix>/admin  管理登录页 / 后台页（密码保护、CSRF、登录频率限制）
- POST /<prefix>/admin  提交「已借出」清单（文本框或 TXT 文件），更新并重建站点
- GET  /<prefix>/logout 退出登录

借出状态唯一可变来源：borrowed.json（每行一个书名，或 JSON 数组）。
配置环境变量：
  ADMIN_PASSWORD      管理密码（必填，部署时设置）
  ADMIN_PATH_PREFIX   可选；后台路径前缀，例如 secret 则后台为 /secret/admin
  SECRET_KEY          Flask 会话密钥（建议设置）
  SESSION_COOKIE_SECURE 可选；在 Render（HTTPS）上建议设为 true
  GITHUB_TOKEN      可选；设置后更新会自动 git 提交推送，使 Render 持久化重新部署
  GITHUB_REPO       可选；格式 owner/name
  GITHUB_BRANCH     可选；默认 main
  PORT              可选；默认 3000
"""
import os, json, subprocess, time, hmac, secrets, logging
from flask import (Flask, request, session, redirect, url_for,
                   send_from_directory, render_template_string, abort)
from builder import render_index

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

HERE = os.path.dirname(os.path.abspath(__file__))
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'change-me')
ADMIN_PATH_PREFIX = (os.environ.get('ADMIN_PATH_PREFIX') or '').strip('/')
TEMPLATE = os.path.join(HERE, 'template.html')
BOOKS = os.path.join(HERE, 'books.json')
BORROWED = os.path.join(HERE, 'borrowed.json')
INDEX = os.path.join(HERE, 'index.html')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'showcase-secret-change-me')
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true',  # Render 可设 true（HTTPS）
    SESSION_COOKIE_HTTPONLY=True,    # 禁止 JS 读取 session cookie
    SESSION_COOKIE_SAMESITE='Lax',   # 防御 CSRF：第三方网站提交表单时不带 cookie
)

# 登录失败频率限制：同一 IP 5 次失败锁定 15 分钟
MAX_FAILS = 5
LOCKOUT_SECONDS = 15 * 60
_FAILED_LOGINS = {}


def _client_ip():
    # Render 会通过 X-Forwarded-For 传真实客户端 IP
    forwarded = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    return forwarded.split(',')[0].strip()


def _check_rate_limit():
    """返回锁定剩余秒数；0 表示未锁定。"""
    ip = _client_ip()
    now = time.time()
    rec = _FAILED_LOGINS.get(ip)
    if rec and rec['count'] >= MAX_FAILS:
        elapsed = now - rec['last']
        if elapsed < LOCKOUT_SECONDS:
            return int(LOCKOUT_SECONDS - elapsed)
        # 锁定期已过，清零
        rec['count'] = 0
    return 0


def _record_login_fail():
    ip = _client_ip()
    now = time.time()
    rec = _FAILED_LOGINS.get(ip)
    if not rec or now - rec.get('last', 0) > LOCKOUT_SECONDS:
        rec = {'count': 0, 'last': now}
        _FAILED_LOGINS[ip] = rec
    rec['count'] += 1
    rec['last'] = now
    logging.warning('admin login failed from %s (count=%d)', ip, rec['count'])


def _csrf_token():
    """生成或返回当前 session 的 CSRF token。"""
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(24)
    return session['csrf']


def _verify_csrf():
    """校验 POST 请求中的 CSRF token。"""
    token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    if not token or not hmac.compare_digest(token, session.get('csrf', '')):
        abort(403)


def admin_path(rule):
    """根据 ADMIN_PATH_PREFIX 生成后台路由路径。"""
    if ADMIN_PATH_PREFIX:
        return f'/{ADMIN_PATH_PREFIX}{rule}'
    return rule


def rebuild():
    out, marked = render_index(BOOKS, BORROWED, TEMPLATE)
    with open(INDEX, 'w', encoding='utf-8') as f:
        f.write(out)
    return marked


def try_git_push():
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPO')
    branch = os.environ.get('GITHUB_BRANCH', 'main')
    if not (token and repo):
        return '（未配置 GITHUB_TOKEN/GITHUB_REPO：更新仅保存在运行实例，Render 休眠/重启后可能丢失；建议配置以持久化）'
    try:
        r = subprocess.run(['git', '-C', HERE, 'status', '--porcelain'],
                           capture_output=True, text=True, check=True)
        if not r.stdout.strip():
            return '（无变动，无需提交）'
        subprocess.run(['git', '-C', HERE, 'config', 'user.email', 'bot@showcase'], check=False)
        subprocess.run(['git', '-C', HERE, 'config', 'user.name', 'showcase-bot'], check=False)
        subprocess.run(['git', '-C', HERE, 'add', 'borrowed.json', 'index.html'], check=True)
        subprocess.run(['git', '-C', HERE, 'commit', '-m', 'update borrowed status'], check=True)
        url = f'https://{token}@github.com/{repo}.git'
        subprocess.run(['git', '-C', HERE, 'push', url, branch], check=True)
        return '已提交并推送到 GitHub，Render 将自动重新部署（持久化生效）'
    except Exception as e:
        return f'git 推送失败：{e}（更新已在当前实例生效，但未能持久化）'


# 启动时构建一次
try:
    rebuild()
except Exception as e:
    print('initial build failed:', e)


LOGIN = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>管理登录</title>
<style>body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#fafaf9;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
.box{background:#fff;border:1px solid #e7e5e4;border-radius:14px;padding:28px 26px;width:300px;box-shadow:0 10px 24px rgba(0,0,0,.08)}
h1{font-size:18px;margin:0 0 14px;color:#292524}.e{color:#c2410c;font-size:13px;margin-bottom:10px}
input{padding:12px;font-size:16px;border:1px solid #e7e5e4;border-radius:10px;width:100%;box-sizing:border-box;margin-bottom:12px}
button{background:#92400e;color:#fff;border:0;border-radius:10px;padding:12px;width:100%;font-size:15px;cursor:pointer}</style></head>
<body><div class="box"><h1>借阅室管理</h1>{% if error %}<div class="e">{{error}}</div>{% endif %}
<form method="post"><input name="pw" type="password" placeholder="管理员密码" autocomplete="off"><button>登录</button></form></div></body></html>'''

ADMIN = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>借出状态管理</title>
<style>body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#fafaf9;margin:0;padding:24px}
.wrap{max-width:640px;margin:0 auto;background:#fff;border:1px solid #e7e5e4;border-radius:14px;padding:24px;box-shadow:0 10px 24px rgba(0,0,0,.08)}
h1{font-size:20px;margin:0 0 6px;color:#292524}.sub{color:#78716c;font-size:13px;margin-bottom:16px}
textarea{width:100%;height:220px;padding:12px;font-size:14px;border:1px solid #e7e5e4;border-radius:10px;box-sizing:border-box;resize:vertical;font-family:inherit;line-height:1.6}
.row{display:flex;gap:12px;align-items:center;margin-top:12px}button{background:#92400e;color:#fff;border:0;border-radius:10px;padding:12px 20px;font-size:15px;cursor:pointer}
a{color:#92400e;font-size:14px}.ok{background:#f0fdf4;border:1px solid #86efac;color:#166534;border-radius:10px;padding:12px;font-size:14px;margin-bottom:14px}
.note{color:#78716c;font-size:12px;margin-top:8px;display:block}.hint{color:#78716c;font-size:12px;margin:10px 0 0}
.divider{height:1px;background:#e7e5e4;margin:22px 0 18px}
.reset{background:#fff;color:#b91c1c;border:1px solid #fecaca}
.reset:hover{background:#fef2f2}
.warn{color:#b91c1c;font-size:12px;margin-top:8px;display:block}</style>
<script>function confirmBlank(){var t=document.getElementById('txt');if(t&&t.value.trim()===''){return confirm('文本框为空，将清空所有借出标记（即全部图书标记为「在馆」）。确定继续吗？');}return true;}
function confirmResetAll(){return confirm('确定将所有图书标记为「已还（在馆）」吗？此操作会清空当前的借出清单。');}</script></head>
<body><div class="wrap"><h1>借出状态管理</h1>
<div class="sub">粘贴「已借出」清单（每行一本书名），或上传 TXT。按书名匹配，清单几条标几本；同名多副本只标一本。</div>
{% if reset_done %}<div class="ok">已全部重置为「在馆」。<span class="note">所有借出标记已清空。</span></div>
{% elif count is defined %}<div class="ok">已更新：清单 {{count}} 条 → 标记 {{marked}} 本「已借出」。<span class="note">{{note}}</span></div>{% endif %}
<form method="post" enctype="multipart/form-data" onsubmit="return confirmBlank()">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<textarea id="txt" name="text" placeholder="例如：&#10;周易&#10;人间失格&#10;..."></textarea>
<div class="hint">也可选择 TXT 文件上传：<input type="file" name="file" accept=".txt"></div>
<div class="row"><button>保存并更新站点</button><a href="{{ url_for('index') }}">← 返回站点</a> <a href="{{ url_for('logout') }}">退出</a></div>
</form>
<div class="divider"></div>
<form method="post" onsubmit="return confirmResetAll()">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<input type="hidden" name="action" value="reset_all">
<button class="reset" type="submit">全部已还（清空借出）</button>
<div class="warn">一键清空所有借出标记，让全部图书显示为「在馆」。谨慎使用。</div>
</form></div></body></html>'''


@app.route('/')
def index():
    return send_from_directory(HERE, 'index.html')


@app.route(admin_path('/admin'), methods=['GET', 'POST'])
def admin():
    lock_remaining = _check_rate_limit()
    if lock_remaining:
        return render_template_string(LOGIN, error=f'登录尝试过多，请 {lock_remaining} 秒后再试'), 429

    if not session.get('admin'):
        if request.method == 'POST' and request.form.get('pw'):
            if request.form.get('pw') == ADMIN_PASSWORD:
                session['admin'] = True
                session.pop('csrf', None)
                return redirect(url_for('admin'))
            _record_login_fail()
            return render_template_string(LOGIN, error='密码错误')
        return render_template_string(LOGIN)

    if request.method == 'POST':
        _verify_csrf()
        action = request.form.get('action', '')
        if action == 'reset_all':
            # 清空所有借出标记：borrowed.json 置空 → 重建后全部为「在馆」
            json.dump([], open(BORROWED, 'w', encoding='utf-8'), ensure_ascii=False)
            marked = rebuild()
            note = try_git_push()
            return render_template_string(ADMIN, count=0, marked=0, note=note,
                                          csrf=_csrf_token(), reset_done=True)
        text = request.form.get('text', '')
        f = request.files.get('file')
        if f and f.filename:
            text = f.read().decode('utf-8', 'ignore')
        titles = [l.strip() for l in text.splitlines() if l.strip()]
        json.dump(titles, open(BORROWED, 'w', encoding='utf-8'), ensure_ascii=False)
        marked = rebuild()
        note = try_git_push()
        return render_template_string(ADMIN, count=len(titles), marked=marked, note=note, csrf=_csrf_token())

    return render_template_string(ADMIN, csrf=_csrf_token())


@app.route(admin_path('/logout'))
def logout():
    session.pop('admin', None)
    session.pop('csrf', None)
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)), debug=False)
