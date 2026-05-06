# 方果 POD 官网 — 玻璃拟态版 (Glassmorphism)

AI 驱动的 POD 生产与全球履约平台官网静态页面。

## 视觉风格

- **美学语言:** Glassmorphism (玻璃拟态) ✨
- **背景:** 紫蓝渐变 #667eea → #764ba2 + 浮动光晕 (粉/蓝两个 80px 模糊光球缓慢漂移)
- **卡片:** rgba(255,255,255,0.10) + backdrop-blur 20px + 1px 半透白边框
- **圆角:** 20-28px
- **字体:** Outfit 600-800 (标题) / Plus Jakarta Sans 400-500 (正文)
- **强调色:** 黄→粉→紫渐变文字 (#FFD66B → #FF7494 → #C9A9FF)
- **动效:** 卡片入场 staggered 浮现、hover 放大 1.05、产品卡片浮动呼吸、鼠标视差

## 文件结构

```
fangguo-glass/
├── index.html          首页(完整 7 屏)
├── ai.html             AI 铺货页
├── factory.html        工厂方案页
├── merchant.html       商家方案页
├── industries.html     行业方案页(14 个 POD 品类详解)
├── ecosystem.html      平台与物流生态页
├── cases.html          客户案例页(21 个真实工厂)
├── about.html          关于方果页
├── README.md
└── assets/
    ├── styles.css          完整 glassmorphism 设计系统 (~1400 行)
    ├── main.js             滚动动画 + 鼠标视差
    ├── icons.svg           SVG 占位
    └── logo.png            原 Logo
```

## POD 配图

由于环境网络受限,采用了大量精心绘制的内联 SVG POD 产品插画,反而比照片更贴合玻璃拟态美学:
- 首页 Hero 区:5 张浮动产品卡(T 恤 / 马克杯 / 手机壳 / 帆布包 / 卫衣)+ 旋转虚线圆环
- AI 页:3 张浮动卡片展示"输入图 → 套图 → SKU 矩阵"流程
- 工厂页:产线图 / 扫码出货 / 履约完成进度
- 商家页:SKU 矩阵 / 转化率环形图 / 营收柱状图
- 行业页:14 个品类各自的产品图标(渐变色)
- 案例页:21 个工厂卡片各有独立 SVG 缩略图
- 生态页:全球地球网络图
- 关于页:品牌徽章 + 同心圆 + 增长曲线

## 使用方法

1. 解压压缩包
2. 双击 `index.html` 直接在浏览器中打开
3. 或部署到任意静态托管服务 (Vercel / Netlify / Cloudflare Pages / OSS / 七牛云等)

## 浏览器兼容

需支持 `backdrop-filter` (Chrome 76+ / Safari 9+ / Edge 17+ / Firefox 103+)。
玻璃拟态效果在不支持的浏览器中会降级为半透明无模糊背景,基本功能正常。

## 自定义

- **替换 Logo:** 替换 `assets/logo.png`,导航和 footer 内联 SVG 渐变 ID `logoG`/`logoG2`/`lg2` 也可同步替换
- **案例视频链接:** 编辑 `cases.html` 中所有 `https://www.douyin.com/` 改为真实抖音 URL
- **修改背景色:** 在 `styles.css` 顶部 `:root` 修改 `--grad-bg`
- **备案号:** footer 中替换 `粤ICP备 XXXXXXXX 号`

---

© 2026 深圳市渔童科技有限公司 · FANGGUO POD
