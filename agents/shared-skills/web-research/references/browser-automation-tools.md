# 网页浏览器自动化工具（2026年5月）

## 用户需求
输入账号密码登录、完成注册、页面跳转、点击输入 — 网页自动化基本操作。

## 传统成熟工具

### Playwright（微软）— ⭐72k+ — 最推荐（稳定场景）
- GitHub: microsoft/playwright
- Python 一行安装: `pip install playwright && playwright install`
- 自带录制工具 `playwright codegen`，手动操作一遍自动生成脚本
- 支持 Chromium/Firefox/WebKit，内置 auto-waiting
- 所有需求（登录/注册/跳转/点击输入）完美支持

### Selenium — ⭐31k+
- 老牌标准，20+ 年历史，社区最大
- API 老旧，需手动管理等待
- 所有语言都支持

### Puppeteer（Google）— ⭐90k+
- JS/TS only，前端开发者友好
- Chrome 支持最佳

## AI 驱动新一代工具

### Browser Use — ⭐60k+ — 最推荐（灵活场景）
- GitHub: browser-use/browser-use
- `pip install browser-use`，自然语言控制浏览器
- 不需要写 CSS 选择器，直接告诉 AI 要做什么
- 需要配 LLM（GPT-4o/Claude/开源模型）
- 稳定性略低于传统方案

### Skyvern — ⭐10k+
- 专注表单填写和工作流自动化，AI 视觉理解
- 提供 Web 管理界面，需 Docker 部署

### Stagehand — ⭐12k+
- TypeScript，Playwright + AI 混合方案
- `act()`, `extract()`, `observe()` 三核心 API

## 反爬虫方案

### CloakBrowser — ⭐高（CloakHQ/CloakBrowser）
- **定位**: 隐身 Chromium，从 C++ 源码级别修改 58 个指纹点，通过所有机器人检测
- **安装**: `pip install cloakbrowser` 或 `npm install cloakbrowser`
- **用法**: Playwright 的直接替换，改一行 import 即可
- **核心能力**: reCAPTCHA v3 0.9分、Cloudflare Turnstile 通过、FingerprintJS 通过
- **`humanize=True`**: 模拟人类鼠标轨迹、键盘节奏、滚动模式
- **Browser Profile Manager**: 自托管的多账号指纹管理（替代 Multilogin/GoLogin）
- **适用场景**: 自动登录被反爬保护的网站、批量注册、定时爬虫任务
- **集成难度极低**: OpenClaw/Hermes 浏览器工具底层都是 Playwright，直接替换 binary

## 推荐策略
- 流程固定 → **Playwright**（稳定可靠）
- 流程多变/不想写代码 → **Browser Use**（自然语言）
- **需要过反爬检测** → **Playwright + CloakBrowser**（改一行 import）
- 两者可结合使用
