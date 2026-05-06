# 方果 POD 官网 — 编辑式极简版 (Editorial / Boldmind-inspired)

参考波兰创意机构 **Boldmind** 的极简编辑式排版语言重新设计。AI 驱动的 POD 生产与全球履约平台静态页面。

## 视觉风格

- **设计语言:** Editorial / Industrial Minimal (极简编辑工业风) ⚫️⚪️
- **配色:** 黑白主导 + 单一红色重点 #d83a3a + 米色质感纸张 #f4f3ef
- **顶部导航:** 黑色 64px 横条 + 大写字母间距字母
- **大标题:** 中文"切片"式排版,字符堆叠成 2-3 行(关 / 于,联 / 系,流 / 程,客 / 户)
- **英文副标题:** Inter 900 大写字母版本同样切片(O / NAS, KO / NT / AKT)
- **质感背景:** Hero 区使用米色叠加多重径向渐变模拟纸张/水泥纹理 + 旋转邮戳
- **分区:** 极细 1px 灰线分隔 + 大量留白
- **数据展示:** 4 列 / 3 列网格 + 边框分隔(类似 Boldmind 的客户 logo 墙)
- **动效:** 简单 fade-in-up 滚动进入

## 字体方案

针对简体中文优化:

- **正文中文:** [思源黑体 Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC) 400/500/700/900
- **标题中文:** 同上(Noto Sans SC 900 重磅)
- **英文标题/数字:** [Inter](https://fonts.google.com/specimen/Inter) 800/900
- **降级:** PingFang SC / Microsoft YaHei / system-ui

字体已通过 Google Fonts CDN 引入,首次加载约 200KB,缓存后实际网络消耗约 60KB。

## 文件结构

```
fangguo-bold/
├── index.html          首页 - 完整 Boldmind 模式 (NEWS / REALIZACJE / OFERTA / KLIENCI / O NAS / KONTAKT 六大区)
├── ai.html             AI 铺货 - 三阶段 AI 流程 + 价值清单
├── factory.html        工厂方案 - 3 步走 + 12 项能力 + 对比表
├── merchant.html       商家方案 - 4 价值 + 4 适合人群 + 6 步流程
├── industries.html     行业方案 - 14 个 POD 品类(每个含编号 / 痛点 / 方案 / 流程)
├── ecosystem.html      平台与物流生态 - 标签云分组 + 4 大原则
├── cases.html          客户案例 - 21 个真实工厂视频(独立编号 + 播放按钮)
├── about.html          关于方果 - 公司 / 使命 / 愿景 / 承诺 / ONE MORE THING
├── README.md
└── assets/
    ├── styles.css          完整编辑式设计系统 (~1100 行)
    ├── main.js             滚动 reveal 动画
    └── logo.png            原 Logo (备份)
```

## Boldmind 风格还原细节

参考图中的 Boldmind 网站设计语言被精确还原到方果 POD:

| 原版 (Boldmind) | 方果 POD 中文化 |
|---|---|
| NEWS / NE-WS | 动态 / 动-态 |
| REALIZACJE | 案例 / 案-例 |
| OFERTA | 服务 / 服-务 |
| KLIENCI | 客户 / 客-户 |
| O NAS | 关于 / 关-于 |
| KONTAKT | 联系 / 联-系 |
| 米色纸张 hero 背景 | 同样米色 + 邮戳 SVG |
| 细线分隔 + 大量留白 | 完全保留 |
| 4×4 客户 logo 墙 | 8 个全球电商平台 |
| 黑色顶 nav + 黑色底 footer | 完全保留 |
| 单红色点缀 | #d83a3a 用作"更多"按钮 / 关键强调 |

## SVG 配图

由于环境限制无法下载真实照片,所有产品图都是手绘 SVG 几何插画(T 恤 / 马克杯 / 手机壳 / 铁皮画 / 雨伞 / 鞋子 / 相框 / 帆布袋 / 亚克力等)。这些插画的极简黑白 + 红色点缀风格反而比真实图片更符合 Boldmind 的编辑式美学。

## 使用方法

1. 解压压缩包
2. 双击 `index.html` 直接在浏览器中打开
3. 或部署到任意静态托管(Vercel / Netlify / Cloudflare Pages / 阿里云 OSS / 腾讯云等)

## 浏览器兼容

- 现代浏览器全支持
- Chrome / Safari / Firefox / Edge 最近 2 个版本
- IE11 不再支持(CSS Grid + clamp())

## 自定义

- **替换 Logo:** 替换 `assets/logo.png`,nav 内联 SVG 也可同步替换
- **案例视频链接:** 编辑 `cases.html` 中所有 `https://www.douyin.com/` 改为真实抖音 URL
- **修改红色:** 在 `styles.css` 顶部 `:root` 修改 `--accent: #d83a3a`
- **备案号:** 全部页面 footer 中替换 `粤ICP备 XXXXXXXX 号`

---

© 2026 深圳市渔童科技有限公司 · FANGGUO POD · MADE FOR POD IN SHENZHEN
