# 蓝湖原型抓取器使用指南

`lanhu_scraper.py` 用 Playwright 控制本地 Chromium，自动遍历项目下 190 份 .rp 文档共
12,727 个原型页面，逐页等待渲染后全屏截图保存。所有产物本地可看，不依赖网络。

---

## 一、安装依赖（一次性）

打开终端：

```bash
cd "/Users/lidehui/Desktop/claude/lanhu/lanhu"

# 1. 安装 Playwright（推荐用 venv 隔离）
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install playwright

# 2. 安装 Chromium 浏览器（Playwright 自带一份）
python3 -m playwright install chromium
```

如果不想用 venv，直接 `pip install playwright` 也可以。

---

## 二、运行

### 第一次运行（建议先小规模验证）

```bash
# 先抓前 2 份文档，验证流程能跑通、截图效果你能接受
python3 lanhu_scraper.py --max-docs 2
```

第一次启动会打开一个浏览器窗口：
1. 在窗口里**手动登录蓝湖**（输入账号密码）
2. 登录后回到终端，按回车继续
3. 脚本自动开始抓取，所有产物写到 `./lanhu_archive/`

登录态保存在 `lanhu_archive/_state/browser_profile/`，下次运行不需重新登录。

### 验证效果后跑全量

```bash
python3 lanhu_scraper.py
# 单线程预计 12-18 小时；中间任何时候 Ctrl+C 都可以，下次自动断点续抓
```

### 加速（开多个浏览器并行）

```bash
python3 lanhu_scraper.py --concurrency 3
# 3 个 worker 并行，预计 4-6 小时；机器内存吃紧就降到 2
```

---

## 三、产物结构

```
lanhu_archive/
├── index.html                    <- 总索引（卡片视图，可筛选）
├── _state/                       <- 登录态、进度、日志
│   ├── browser_profile/          <- Chromium 用户目录（含 cookie）
│   ├── completed.json            <- 已完成的页面列表（断点续抓用）
│   ├── docs_cache.json           <- 文档清单缓存
│   └── scraper.log               <- 详细日志
├── 方果系统2.0/
│   ├── index.html                <- 该文档的页面索引
│   ├── 0001_系统首页.png
│   ├── 0002_订单管理.png
│   └── ...
├── 方果系统8.8-王语祝/
│   ├── index.html
│   ├── 0001_…….png
│   └── ...
└── ...（共 190 份文档目录）
```

打开 `lanhu_archive/index.html` 即可在浏览器里浏览所有截图归档。

---

## 四、常用命令

```bash
# 看完整帮助
python3 lanhu_scraper.py --help

# 仅前 5 份文档
python3 lanhu_scraper.py --max-docs 5

# 从第 80 份继续（手工跳过前面的）
python3 lanhu_scraper.py --start-doc 80

# 网络较慢时加大每页等待时间到 4 秒
python3 lanhu_scraper.py --settle 4

# 强制重抓所有页面（清空进度记录）
python3 lanhu_scraper.py --reset

# 强制刷新文档清单（蓝湖项目有新文档时）
python3 lanhu_scraper.py --refresh-docs

# 无头模式，速度更快但看不到浏览器
python3 lanhu_scraper.py --headless --concurrency 3
```

---

## 五、常见问题

**Q: 浏览器卡住不动？**
A: 大概率是网络抖动或 lanhu 后端慢。脚本对每个页面 60s 超时；如果某页一直失败，
按 Ctrl+C 中断、再次运行，断点续抓时该页会重试。

**Q: 截图里有 lanhu 的导航条/侧边栏？**
A: 脚本默认注入 CSS 隐藏 lanhu UI，但 lanhu 偶尔改类名后可能挡住效果不全。
打开 `lanhu_scraper.py` 找 `INJECT_HIDE_CHROME` 常量，在那段 CSS 末尾加你想隐藏的
selector，比如 `.your-class { display: none !important; }`。

**Q: 全量抓取要多久？**
A: 12,727 页，每页 5-10 秒（含等待 + 截图 + 文件写入）：
- 单线程：约 17-35 小时
- 并发 3：约 6-12 小时
- 并发 5：约 4-7 小时（建议 16GB+ 内存机器）

**Q: 中途出错怎么办？**
A: 日志在 `lanhu_archive/_state/scraper.log`，已完成页面在 `completed.json`。
直接重跑脚本会跳过已完成页面，只重试失败的。

**Q: 蓝湖账号登出了怎么办？**
A: 删掉 `lanhu_archive/_state/browser_profile/` 目录，下次运行会要求重新登录。

**Q: 想换一个项目（不是当前 tid/pid）？**
A: 改脚本顶部的 `TID` 和 `PID` 常量。值在你打开蓝湖时 URL 里能看到。

---

## 六、技术细节

- 用 `BrowserContext.launch_persistent_context()` 持久化登录态到 `_state/browser_profile/`
- 通过 `/api/project/product_documents` 取所有文档清单
- 通过 `/api/project/image?image_id={docId}` 取每份文档的最新 versionId
- 在 lanhu SPA 里改 URL hash 触发 SPA 内导航，等待 `.lan-mapping-iframe` 的 src 包含 `_md5__` 后再截图
- 截图前注入一段 CSS 隐藏 lanhu 自身的 UI 元素
- 用 `page.screenshot(full_page=True)` 抓全屏（含 iframe 渲染区域）
- 进度持久化到 `completed.json`，脚本任意时刻可中断 / 续抓
- 并发模式下用 `launch_persistent_context` 抓一次 cookie，再 fork 多个非持久 BrowserContext，每个用同一份 cookie

如果脚本里某段你想改（比如截图的 viewport 大小、settle 时间、隐藏的 UI 选择器），代码注释比较详细，按需调整即可。
