# 方果 POD 官网 — Fangguo POD Website

AI 驱动的 POD 生产与全球履约平台官网静态页面。

## 文件结构

```
fangguo/
├── index.html          首页 (9 屏:Hero / 引擎 / 工厂 / 商家 / AI / 行业 / 生态 / 优势 / CTA)
├── ai.html             AI 铺货页 (3 条核心流程)
├── factory.html        工厂解决方案页 (生产数字化 / 履约自动化 / 供应链平台化)
├── merchant.html       商家解决方案页 (4 大核心价值)
├── industries.html     行业方案页 (14 个 POD 品类详解)
├── ecosystem.html      平台与物流生态页
├── cases.html          客户案例页 (21 个真实工厂案例)
├── about.html          关于方果页
├── README.md
└── assets/
    ├── design-system.css   完整设计系统 (~1500 行)
    ├── main.js             导航 + 滚动动画
    └── logo.png            原始 Logo
```

## 使用方法

1. 解压压缩包
2. 双击 `index.html` 直接在浏览器中打开
3. 或部署到任意静态托管服务 (Vercel / Netlify / Cloudflare Pages / OSS / 七牛云等)

## 设计系统

- **设计语言**: Editorial Modern × Industrial × Warm
- **主色**: Coral #E8556B / Slate #2A3441 / Cream #FAF7F2 / Leaf #6FBE3F
- **字体**: Fraunces (display italic) · Noto Serif SC · Noto Sans SC · JetBrains Mono
- **响应式**: 支持桌面、平板、移动端

## 浏览器兼容

Chrome / Edge / Safari / Firefox 最近 2 个主版本。

## 替换内容

- Logo: 替换 `assets/logo.png`,导航和 footer 的内联 SVG 也可同步替换
- 案例视频链接: 编辑 `cases.html` 中所有 `https://www.douyin.com/` 改为真实抖音 URL
- 案例图片: 当前为渐变占位,可在 `.case-card__thumb` 内增加 `<img>` 标签
- 备案号: footer 中替换 `粤ICP备 XXXXXXXX 号`

---

© 2026 深圳市渔童科技有限公司 · FANGGUO POD
