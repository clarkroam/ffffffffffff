#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蓝湖原型抓取器 (lanhu prototype scraper)
=========================================

用 Playwright 控制本地 Chromium，登录后自动遍历项目里所有文档和页面，
逐页等待 lanhu 父页面 + Axure 子帧渲染完成 → 截全屏 PNG → 生成索引页。
解决"本地无法离线渲染 Axure"的问题——用真实浏览器渲染、产物是图片，离线随时可看。

────────────────────────────────────────────────────
依赖：
    python3 -m pip install --upgrade playwright
    python3 -m playwright install chromium

运行：
    python3 lanhu_scraper.py                   # 全量抓取，断点续抓
    python3 lanhu_scraper.py --max-docs 3      # 仅抓前 3 份文档（先验证流程）
    python3 lanhu_scraper.py --start-doc 80    # 从第 80 份开始
    python3 lanhu_scraper.py --concurrency 3   # 并发 3 个浏览器实例（更快但更耗资源）
    python3 lanhu_scraper.py --headless        # 无头模式（默认有头便于排错）
    python3 lanhu_scraper.py --reset           # 清空进度，重新开始

输出：
    ./lanhu_archive/
      ├── index.html               <- 总索引
      ├── _state/                  <- 浏览器登录态与进度持久化
      └── <doc-name>/
           ├── index.html          <- 该文档的页面索引
           ├── 0001_页面名.png
           ├── 0002_页面名.png
           └── ...

首次运行会启动一个浏览器窗口让你登录蓝湖，登录后回到终端按回车继续，
脚本会把 Cookie 保存到 _state 目录，后续运行不需重复登录。

────────────────────────────────────────────────────
主要思路：
1. 调 /api/project/product_documents 拿到所有 .rp 文档
2. 对每份文档调 /api/project/image 拿 versionId
3. 导航到 lanhu 文档 URL，从 DOM 的 .tree-item-wrapper-{32hex} class 里提取所有 pageId
4. 对每个 pageId 改 URL 的 hash 触发 SPA 内导航，等待 iframe 渲染
5. 用 CSS 隐藏掉 lanhu 自身 UI，full_page=True 截图
6. 写 PNG，记录到 .completed.json，下次跑时跳过
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Error as PlaywrightError,
        Page,
        TimeoutError as PlaywrightTimeout,
        async_playwright,
    )
except ImportError:
    print(
        "缺少 Playwright。请先运行:\n"
        "  python3 -m pip install --upgrade playwright\n"
        "  python3 -m playwright install chromium",
        file=sys.stderr,
    )
    sys.exit(1)


# ─── 项目配置（来自最初提供的 lanhu URL） ────────────────────────────────
TID = "12a3baa4-7464-425c-b959-e2052d79f580"
PID = "042735e4-bb4c-4ae8-a6a0-1de17b7e824f"

# 输出目录与状态目录
SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "lanhu_archive"
STATE_DIR = OUT_DIR / "_state"
PROFILE_DIR = STATE_DIR / "browser_profile"
COMPLETED_FILE = STATE_DIR / "completed.json"
LOG_FILE = STATE_DIR / "scraper.log"
DOCS_CACHE = STATE_DIR / "docs_cache.json"

# 文件名安全字符：去掉 / \ : * ? " < > | 等
_SAFE_NAME = re.compile(r'[\\/:*?"<>|\r\n\t]')


def safe_name(name: str, max_len: int = 180) -> str:
    """把文档/页面名转换成可作目录或文件名的安全字符串。"""
    out = _SAFE_NAME.sub("_", name).strip().rstrip(". ")
    return (out or "未命名")[:max_len]


def lanhu_doc_url(version_id: str, doc_id: str, page_id: str | None = None) -> str:
    """构造 lanhu Web 端 URL。"""
    base = (
        f"https://lanhuapp.com/web/#/item/project/product?"
        f"tid={TID}&pid={PID}&versionId={version_id}&docId={doc_id}"
        f"&docType=axure&image_id={doc_id}"
    )
    if page_id:
        base += f"&pageId={page_id}"
    return base


def log(msg: str, also_print: bool = True) -> None:
    """同时打印到屏幕和写入日志文件。"""
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    if also_print:
        print(line, flush=True)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── 蓝湖 API 调用（在浏览器内 fetch 以利用 cookie） ───────────────────
async def fetch_all_docs(page: Page) -> list[dict[str, Any]]:
    """
    通过 /api/project/product_documents 获取项目里所有 .rp 文档清单。
    返回元素结构: { id, name, type, latest_version, order, ... }
    """
    js = f"""
    (async () => {{
      const r = await fetch(
        '/api/project/product_documents?team_id={TID}&project_id={PID}',
        {{ credentials: 'include' }}
      );
      if (!r.ok) throw new Error('product_documents HTTP ' + r.status);
      const data = await r.json();
      return (data.result?.resources || []).filter(d => d.type === 'axure');
    }})()
    """
    docs = await page.evaluate(js)
    docs.sort(key=lambda d: d.get("order", 0))
    return docs


async def fetch_doc_version(page: Page, doc_id: str) -> str | None:
    """获取文档最新版本的 versionId（导航 URL 需要）。"""
    js = f"""
    (async () => {{
      const r = await fetch(
        '/api/project/image?team_id={TID}&project_id={PID}&image_id={doc_id}',
        {{ credentials: 'include' }}
      );
      const data = await r.json();
      return data.result?.versions?.[0]?.id || null;
    }})()
    """
    return await page.evaluate(js)


# ─── 页面发现：从 lanhu 侧边栏 DOM 抽 32-hex pageId ───────────────────
async def discover_page_ids(page: Page, doc: dict, version_id: str) -> list[dict]:
    """
    导航到文档 URL，等侧边栏渲染完，展开所有目录折叠节点，
    抽出每个 .tree-item-wrapper-{32hex} 的 pageId 与名称。
    返回 [{id, name}, ...]
    """
    url = lanhu_doc_url(version_id, doc["id"])
    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    # 等侧边栏出现
    try:
        await page.wait_for_selector(".tree-item-wrapper", timeout=20_000)
    except PlaywrightTimeout:
        log(f'  ! 侧边栏未加载: {doc["name"]}')
        return []

    # 多次循环：展开折叠节点 + 滚动加载虚拟列表
    for _ in range(8):
        # 点击所有可见的折叠箭头来展开
        try:
            await page.evaluate(
                """
                () => {
                  // lanhu 用 v-icon 类 + 旋转角度表示折叠状态；点击 tree-collapse 类
                  const arrows = document.querySelectorAll(
                    '.tree-collapse-arrow:not(.expanded), .lan-tree-arrow:not(.expand), [class*="arrow"][class*="collapsed"]'
                  );
                  arrows.forEach(a => { try { a.click(); } catch(e) {} });
                }
                """
            )
        except Exception:
            pass

        # 滚动侧边栏底部以加载更多
        try:
            await page.evaluate(
                """
                () => {
                  const scrollers = document.querySelectorAll('.lan-tree-list, .lan-virtual-scroll, [class*="page-tree"], [class*="tree-container"]');
                  scrollers.forEach(s => { s.scrollTop = s.scrollHeight; });
                  window.scrollTo(0, document.body.scrollHeight);
                }
                """
            )
        except Exception:
            pass

        await asyncio.sleep(0.4)

    # 抽取所有 32-hex pageId
    ids = await page.evaluate(
        """
        () => {
          const seen = new Map();
          document.querySelectorAll('.tree-item-wrapper').forEach(w => {
            const m = w.className.match(/tree-item-wrapper-([a-f0-9]{32})\\b/);
            if (m && !seen.has(m[1])) {
              const nameEl = w.querySelector('.lan-tree-list-item, [class*="directory-list-item"]')
                || w.querySelector('.tree-name, [class*="tree-text"]')
                || w;
              const name = (nameEl.textContent || '').trim();
              seen.set(m[1], name.slice(0, 200));
            }
          });
          return [...seen.entries()].map(([id, name]) => ({ id, name }));
        }
        """
    )
    return ids


# ─── 单页渲染 + 截图 ─────────────────────────────────────────────────
INJECT_HIDE_CHROME = """
() => {
  const css = `
    /* 隐藏 lanhu 自身的导航/侧边栏/评论面板，只保留主要画布 */
    .project-nav, .lan-side-panel, .lan-toolbar, .nav-bar,
    [class*="header-bar"], [class*="side-bar"], [class*="comment"],
    .lan-help-tip, .lan-mini-tip, .lan-popup-prototype, .help-mini-button {
      display: none !important;
    }
    /* 让 iframe 占满整宽 */
    .lan-mapping-iframe, [class*="iframe-wrap"], [class*="canvas-container"] {
      left: 0 !important; top: 0 !important;
      width: 100vw !important; height: auto !important;
      min-width: 100vw !important;
    }
    body, html { overflow: visible !important; }
  `;
  const style = document.createElement('style');
  style.id = '__lanhu_scraper_hide_chrome__';
  style.textContent = css;
  document.head.appendChild(style);
}
"""


async def wait_iframe_ready(page: Page, timeout_ms: int = 25_000) -> None:
    """等待 lan-mapping-iframe 出现并完成 src 加载。"""
    try:
        await page.wait_for_selector(".lan-mapping-iframe", timeout=timeout_ms)
        # 等 iframe 完成 1 次切换（lanhu 切换页面会改 src）
        await page.wait_for_function(
            """
            () => {
              const f = document.querySelector('.lan-mapping-iframe');
              if (!f) return false;
              try {
                // iframe.complete 没有，用 src 是否包含 _md5__ 来判断
                return /_md5__/.test(f.src);
              } catch(e) { return true; }
            }
            """,
            timeout=timeout_ms,
        )
    except PlaywrightTimeout:
        pass  # 即使超时也尽量截图，给用户看到部分内容


async def screenshot_page(
    page: Page,
    doc: dict,
    version_id: str,
    page_info: dict,
    out_path: Path,
    settle_seconds: float = 2.5,
) -> None:
    """导航到指定页面，等待渲染，全屏截图保存。"""
    url = lanhu_doc_url(version_id, doc["id"], page_info["id"])
    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    await wait_iframe_ready(page)
    # 给 Axure 内部脚本/postMessage 协调留时间
    await asyncio.sleep(settle_seconds)
    # 注入 CSS 隐藏 lanhu chrome（每次刷新需重注）
    try:
        if "__lanhu_scraper_hide_chrome__" not in await page.content():
            await page.evaluate(INJECT_HIDE_CHROME)
    except Exception:
        pass

    # 全屏截图
    out_path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(out_path), full_page=True, type="png")


# ─── 索引页生成 ──────────────────────────────────────────────────────
def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_doc_index(doc_dir: Path, doc_name: str, page_files: list[tuple[str, str]]) -> None:
    """page_files: list of (page_name, png_filename)"""
    rows = "\n".join(
        f'<tr><td>{i+1}</td><td>{_esc(name)}</td>'
        f'<td><a href="{_esc(fn)}" target="_blank">查看 PNG</a></td></tr>'
        for i, (name, fn) in enumerate(page_files)
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>{_esc(doc_name)} · {len(page_files)} 页</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#f7f8fa;margin:0;color:#333}}
header{{background:#fff;padding:18px 32px;border-bottom:1px solid #e6e8eb}}
h1{{margin:6px 0;font-size:20px}}
.back{{color:#4a90e2;text-decoration:none;font-size:13px}}
.container{{max-width:1100px;margin:18px auto;padding:0 24px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e6e8eb;border-radius:6px;overflow:hidden}}
th{{text-align:left;padding:9px 12px;background:#f0f3f7;font-size:13px}}
td{{padding:9px 12px;font-size:14px;border-bottom:1px solid #f0f1f3}}
td:first-child{{color:#999;width:50px;text-align:center}}
td a{{color:#4a90e2;text-decoration:none}}
</style></head><body>
<header>
  <a href="../index.html" class="back">← 返回总索引</a>
  <h1>{_esc(doc_name)}</h1>
  <div style="color:#666;font-size:13px">{len(page_files)} 页 · 全屏渲染截图</div>
</header>
<div class="container">
  <table><thead><tr><th>#</th><th>页面名</th><th>操作</th></tr></thead>
  <tbody>{rows}</tbody></table>
</div></body></html>"""
    (doc_dir / "index.html").write_text(html, encoding="utf-8")


def write_master_index(out_dir: Path, doc_summaries: list[dict]) -> None:
    total_pages = sum(d["captured"] for d in doc_summaries)
    cards = "\n".join(
        f'''<a class="card" href="{_esc(d["dirname"])}/index.html">
              <div class="title">{_esc(d["name"])}</div>
              <div class="meta">{d["captured"]}/{d["total"]} 页 · 截图存档</div>
            </a>'''
        for d in doc_summaries
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>方果系统原型库 · 离线截图归档</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#f7f8fa;margin:0;color:#333}}
header{{background:#fff;padding:24px 40px;border-bottom:1px solid #e6e8eb}}
h1{{margin:0 0 6px;font-size:22px}}
.summary{{color:#666;font-size:13px}}
.container{{max-width:1280px;margin:24px auto;padding:0 24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}}
.card{{display:block;text-decoration:none;color:inherit;background:#fff;border:1px solid #e6e8eb;border-radius:8px;padding:16px}}
.card:hover{{border-color:#4a90e2}}
.title{{font-weight:600;margin-bottom:6px}}
.meta{{color:#888;font-size:13px}}
.filter input{{width:280px;padding:8px 12px;border:1px solid #d6d9dc;border-radius:6px}}
.filter{{margin-bottom:16px}}
</style></head><body>
<header>
  <h1>方果系统原型库 · 离线截图归档</h1>
  <div class="summary">{len(doc_summaries)} 份文档 · 共 {total_pages} 张截图 · 抓取于 {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</header>
<div class="container">
  <div class="filter"><input id="q" placeholder="按文档名筛选..." oninput="filterDocs(this.value)"></div>
  <div class="grid" id="grid">{cards}</div>
</div>
<script>
function filterDocs(q){{
  q=q.toLowerCase().trim();
  document.querySelectorAll('.card').forEach(c=>{{
    const t=c.querySelector('.title').textContent.toLowerCase();
    c.style.display=(!q||t.includes(q))?'':'none';
  }});
}}
</script></body></html>"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")


# ─── 进度持久化 ─────────────────────────────────────────────────────
def load_completed() -> set[str]:
    if COMPLETED_FILE.exists():
        try:
            return set(json.loads(COMPLETED_FILE.read_text("utf-8")))
        except Exception:
            return set()
    return set()


def save_completed(completed: set[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = COMPLETED_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(completed), ensure_ascii=False), encoding="utf-8")
    tmp.replace(COMPLETED_FILE)


# ─── 主流程 ──────────────────────────────────────────────────────────
async def ensure_logged_in(page: Page) -> None:
    """打开蓝湖首页，如果未登录则等用户在浏览器里手动登录。"""
    await page.goto("https://lanhuapp.com/web/", wait_until="domcontentloaded")
    await asyncio.sleep(1.5)
    # 检查是否已登录：尝试调用一个需要登录的接口
    is_logged = False
    try:
        result = await page.evaluate(
            """
            (async () => {
              try {
                const r = await fetch('/api/account/user/detail?team_id=', {credentials:'include'});
                return r.status === 200;
              } catch(e) { return false; }
            })()
            """
        )
        is_logged = bool(result)
    except Exception:
        pass

    if is_logged:
        log("✓ 已登录")
        return

    log("浏览器已打开，请在窗口中登录蓝湖。登录完成后回到终端按回车继续……")
    # 阻塞等待用户回车
    await asyncio.get_event_loop().run_in_executor(None, input)
    log("继续……")


async def process_doc(
    page: Page,
    doc: dict,
    completed: set[str],
    out_dir: Path,
    settle_seconds: float,
) -> dict:
    """处理单个文档：发现页面 → 截图 → 写文档索引。返回汇总信息。"""
    name = doc["name"]
    doc_id = doc["id"]
    log(f"▶ [{doc.get('order','?')}] {name}")

    # 取最新版本
    version_id = await fetch_doc_version(page, doc_id)
    if not version_id:
        log(f"  ✗ 无版本信息，跳过")
        return {"name": name, "dirname": safe_name(name), "captured": 0, "total": 0}

    # 发现 pageId 列表
    pages = await discover_page_ids(page, doc, version_id)
    if not pages:
        log(f"  ! 未发现页面")
        return {"name": name, "dirname": safe_name(name), "captured": 0, "total": 0}

    log(f"  发现 {len(pages)} 个页面")
    doc_dir = out_dir / safe_name(name)
    doc_dir.mkdir(parents=True, exist_ok=True)

    page_files: list[tuple[str, str]] = []
    for i, p in enumerate(pages, 1):
        key = f"{doc_id}/{p['id']}"
        fname = f"{i:04d}_{safe_name(p['name'] or p['id'], max_len=80)}.png"
        out_path = doc_dir / fname

        if key in completed and out_path.exists():
            page_files.append((p["name"] or p["id"], fname))
            continue

        try:
            await screenshot_page(page, doc, version_id, p, out_path, settle_seconds)
            completed.add(key)
            page_files.append((p["name"] or p["id"], fname))
            if i % 5 == 0:
                save_completed(completed)
                print(f"    {i}/{len(pages)}", flush=True)
        except Exception as e:
            log(f"    ✗ 第 {i} 页 {p['id'][:8]}…: {e}")

    save_completed(completed)
    write_doc_index(doc_dir, name, page_files)
    log(f"  ✓ {len(page_files)}/{len(pages)} 页完成")
    return {
        "name": name,
        "dirname": safe_name(name),
        "captured": len(page_files),
        "total": len(pages),
    }


async def worker(
    worker_id: int,
    queue: asyncio.Queue,
    pw,
    headless: bool,
    completed: set[str],
    summaries: list,
    settle_seconds: float,
) -> None:
    """并发 worker：每个用独立的 BrowserContext，共享 profile 目录。"""
    ctx = await pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        viewport={"width": 1600, "height": 1100},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    try:
        while True:
            try:
                doc = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                summary = await process_doc(
                    page, doc, completed, OUT_DIR, settle_seconds
                )
                summaries.append(summary)
            except Exception as e:
                log(f"[worker {worker_id}] 处理 {doc.get('name')} 出错: {e}")
            finally:
                queue.task_done()
    finally:
        await ctx.close()


async def main(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"输出目录: {OUT_DIR}")

    if args.reset:
        if COMPLETED_FILE.exists():
            COMPLETED_FILE.unlink()
        log("已清空进度记录")

    completed = load_completed()
    log(f"已完成页面数：{len(completed)}")

    async with async_playwright() as pw:
        # 第一阶段：登录 + 拉文档清单（用单个浏览器实例）
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,  # 登录阶段强制有头
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await ensure_logged_in(page)

        # 拉文档清单（带缓存避免重复抓）
        if DOCS_CACHE.exists() and not args.refresh_docs:
            docs = json.loads(DOCS_CACHE.read_text("utf-8"))
            log(f"从缓存读取 {len(docs)} 份文档")
        else:
            docs = await fetch_all_docs(page)
            DOCS_CACHE.write_text(
                json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log(f"发现 {len(docs)} 份 .rp 文档（已缓存）")

        await ctx.close()

        # 应用过滤参数
        if args.start_doc:
            docs = docs[args.start_doc :]
        if args.max_docs:
            docs = docs[: args.max_docs]
        log(f"本轮处理 {len(docs)} 份文档")

        # 第二阶段：并发抓取
        summaries: list[dict] = []
        if args.concurrency <= 1:
            # 单线程：用一个上下文跑完
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=args.headless,
                viewport={"width": 1600, "height": 1100},
            )
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            for doc in docs:
                try:
                    s = await process_doc(
                        page, doc, completed, OUT_DIR, args.settle
                    )
                    summaries.append(s)
                except Exception as e:
                    log(f"处理 {doc.get('name')} 出错: {e}")
            await ctx.close()
        else:
            # 注意：persistent_context 同一 profile 不能多实例并发开
            # 这里走非 persistent，cookies 从 profile 复制一份再用
            # 先用 profile 启一次拿 cookies
            log(f"准备 {args.concurrency} 个并发 worker（共享 cookies）")
            ctx0 = await pw.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR), headless=True
            )
            cookies = await ctx0.cookies()
            await ctx0.close()

            queue: asyncio.Queue = asyncio.Queue()
            for d in docs:
                queue.put_nowait(d)

            async def conc_worker(wid: int):
                browser = await pw.chromium.launch(headless=args.headless)
                ctx = await browser.new_context(
                    viewport={"width": 1600, "height": 1100}
                )
                await ctx.add_cookies(cookies)
                pg = await ctx.new_page()
                try:
                    while True:
                        try:
                            doc = queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                        try:
                            s = await process_doc(
                                pg, doc, completed, OUT_DIR, args.settle
                            )
                            summaries.append(s)
                        except Exception as e:
                            log(f"[worker {wid}] {doc.get('name')}: {e}")
                        finally:
                            queue.task_done()
                finally:
                    await ctx.close()
                    await browser.close()

            await asyncio.gather(
                *(conc_worker(i + 1) for i in range(args.concurrency))
            )

        # 第三阶段：写总索引
        summaries.sort(key=lambda s: s["name"])
        write_master_index(OUT_DIR, summaries)
        save_completed(completed)
        total_captured = sum(s["captured"] for s in summaries)
        log("=" * 50)
        log(f"完成。总计抓取 {total_captured} 张截图，跨 {len(summaries)} 份文档")
        log(f"打开 {OUT_DIR / 'index.html'} 浏览全部")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="蓝湖原型抓取器（Playwright）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--max-docs",
        type=int,
        default=0,
        help="只处理前 N 份文档（0 表示全部，建议先用小值验证）",
    )
    p.add_argument(
        "--start-doc",
        type=int,
        default=0,
        help="从第 N 份文档开始（用于断点续抓）",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="并发浏览器实例数（默认 1，建议不要超过 4）",
    )
    p.add_argument(
        "--headless", action="store_true", help="无头模式（默认有头便于排错）"
    )
    p.add_argument(
        "--settle",
        type=float,
        default=2.5,
        help="每页渲染后等待秒数（默认 2.5；网络慢可设大如 4）",
    )
    p.add_argument("--reset", action="store_true", help="清空进度，从头开始")
    p.add_argument("--refresh-docs", action="store_true", help="刷新文档清单缓存")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        log("用户中断。已保存进度，下次运行将自动续抓。")
