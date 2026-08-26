# 借阅室展示站 · 自助部署与更新指南（Render + GitHub）

本目录是一个**自带管理后台**的图书展示站：访客正常浏览，你（管理员）可在手机上自己修改「已借出」清单，所有人立刻看到最新状态。

## 一、目录里有什么

| 文件 | 作用 |
|------|------|
| `app.py` | Flask 主程序：展示站 + 管理后台（含 CSRF、登录频率限制、session 安全） |
| `builder.py` | 合并构建：把 `books.json` + `borrowed.json` 内联进 `template.html` 生成 `index.html` |
| `build.py` | 命令行构建（同 builder），用于本地/CI 生成静态页 |
| `template.html` | 站点模板（搜索/分类/卡片/详情/深色模式等） |
| `books.json` | 5002 册基础数据（书名/作者/ISBN/出版社/索书号/类目）。**不会被改写** |
| `borrowed.json` | **借出状态的唯一可变来源**，每行一个书名（或 JSON 数组）。初始为当前 24 本 |
| `requirements.txt` / `render.yaml` / `Procfile` | Render 部署配置 |
| `smoke.js` / `search_smoke.js` / `test_admin.py` / `verify_count.py` | 本地回归测试脚本（不影响线上运行） |

## 二、部署到 Render（一次性）

> 前提：需要一个 GitHub 账号（免费）。Render 也免费。

1. **建 GitHub 仓库**：把本目录全部文件推到一个新仓库（例如 `renbao-showcase`）。
   注意必须包含：`app.py`、`builder.py`、`build.py`、`template.html`、`books.json`、`borrowed.json`、`requirements.txt`、`render.yaml`。
2. **注册 Render**：打开 https://render.com ，用 GitHub 登录（免费）。
3. **新建 Web Service**：Dashboard → New → Web Service → 连接你的仓库 → 选中该仓库。
   Render 会自动读取 `render.yaml`。
4. **设置环境变量**（在 Render 的 Environment 里）：
   - `ADMIN_PASSWORD`：**管理密码，务必改成你自己的强密码**（不设则默认 `change-me`，谁都能进后台）。建议 12 位以上，含大小写字母+数字。
   - `SECRET_KEY`：随便一长串随机字符（用于会话签名，长度建议 ≥32）。
   - `ADMIN_PATH_PREFIX`（可选）：后台路径前缀。例如填 `secret`，后台就变成 `https://你的链接/secret/admin`，更难被扫描到。不填就是 `/admin`。
   - `SESSION_COOKIE_SECURE`：填 `true`（Render 默认 HTTPS，开启后 cookie 只通过 HTTPS 传输，更安全）。
   - `GITHUB_TOKEN`（**强烈建议配置**，否则更新不持久）：见下方说明。
   - `GITHUB_REPO`：你的 `owner/仓库名`，例如 `haonch/renbao-showcase`。
   - `GITHUB_BRANCH`：默认 `main`。
5. 点 **Deploy**。完成后拿到形如 `https://renbao-showcase.onrender.com` 的公开链接。

### 生成 GITHUB_TOKEN（让借出更新持久化）
1. GitHub → 右上角头像 → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token**。
2. 勾选 `repo`（读写仓库）权限，生成后复制那串 token。
3. 把它填到 Render 的 `GITHUB_TOKEN` 环境变量。
   作用：你在后台保存清单时，程序会自动把 `borrowed.json` 提交并推回 GitHub，触发 Render 重新部署 —— 这样状态**永久保存**，实例重启/休眠也不丢。

> 若**不**配置 `GITHUB_TOKEN`：更新只保存在运行实例内存/磁盘，Render 免费实例休眠或重启后会回退到仓库里的 `borrowed.json`，可能丢失最新改动。所以务必配置。

## 三、日常使用（手机上改借出状态）

1. 浏览器打开站点链接，正常浏览、搜索、分类。
2. 改借出状态：访问 `你的链接/admin` → 输入 `ADMIN_PASSWORD` 登录。
3. 在文本框**粘贴「已借出」清单（每行一本书名）**，或点「选择 TXT 文件」上传你微信里那份清单。
4. 点「保存并更新站点」——站点**即时更新**，所有人刷新即可看到新书标「已外借」。
   规则与之前一致：清单里有几本就标几本；按书名匹配；同名多副本只标一本。

## 四、注意事项

- **安全**：
  - `ADMIN_PASSWORD` 一定要改掉默认，并设得够强。
  - 后台已自带：① CSRF 防护（防止恶意网站替你提交表单）；② 登录频率限制（同一 IP 输错 5 次锁定 15 分钟，防暴力破解）；③ session cookie 仅 HTTPS + HttpOnly。
  - 如想进一步降低被扫描风险，可配置 `ADMIN_PATH_PREFIX`（见上方），把 `/admin` 改成不公开的路径。
  - 不要在任何公开地方贴出 `/admin` 链接或 `ADMIN_PASSWORD`。
- **冷启动**：Render 免费实例一段时间无人访问会休眠，下次访问首次会慢几秒，正常现象。
- **旧站**：之前 CloudStudio 那个静态站可保留作备份，或停用；以后以 Render 这个带后台的为准。
- **本地预览/测试**：`ADMIN_PASSWORD=你的密码 PORT=5000 python app.py`，浏览器开 `http://127.0.0.1:5000`。
  回归测试：`python test_admin.py`（需先起服务）、`node smoke.js`、`node search_smoke.js`。
