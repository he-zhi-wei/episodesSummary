# Episodes Summary

一个基于 Python 的电视剧集信息查看工具，支持搜索电视猫（tvmao.com）上的剧集、浏览封面图片，并一键爬取完整的分集剧情摘要。

## 功能

- **GUI 图形界面** — 基于 tkinter 的现代化界面，搜索、浏览、爬取一站式操作
- **剧集搜索** — 输入关键词搜索电视猫剧集库，结果以卡片网格展示（封面图 + 标题 + 集数）
- **剧情爬取** — 点击剧集卡片自动爬取所有分集剧情摘要，进度实时显示
- **图文展示** — 爬取完成后在新窗口按集序展示完整剧情内容，带格式化排版
- **本地保存** — 剧情摘要自动保存为 `{剧名}_episodes_summary.txt` 文本文件
- **浏览器复用** — 启动时初始化一次浏览器，多次搜索复用，避免重复开销

## 依赖

- Python >= 3.12
- Edge 浏览器（Selenium WebDriver 自动调用）

### Python 包

```
selenium>=4.39.0
aiohttp>=3.9.0
aiofiles>=23.2.1
beautifulsoup4>=4.12.0
pillow>=12.1.0
requests>=2.31.0
```

## 安装

推荐使用 [uv](https://docs.astral.sh/uv/) 管理依赖：

```bash
git clone https://github.com/he-zhi-wei/episodesSummary.git
cd episodesSummary
uv sync
```

或使用 pip：

```bash
git clone https://github.com/he-zhi-wei/episodesSummary.git
cd episodesSummary
pip install -e .
```

## 使用方式

```bash
uv run main.py
```

1. 启动后 GUI 窗口自动打开，浏览器在后台初始化
2. 在搜索框输入剧集名称（如"亮剑"），按 Enter 或点击「开始搜索」
3. 左侧网格展示搜索结果（封面图 + 标题 + 集数）
4. **点击目标剧集卡片**，自动爬取所有分集剧情摘要
5. 爬取完成后弹出新窗口，展示每集标题和剧情内容
6. 剧情同时自动保存为 `{剧名}_episodes_summary.txt`

## 项目结构

```
episodesSummary/
├── main.py         # 程序入口，启动 GUI
├── gui.py          # 图形界面（tkinter），搜索/展示/爬取交互逻辑
├── dramaInfo.py    # 核心模块（Selenium 搜索、异步图片下载、数据模型）
├── pyproject.toml  # 项目配置与依赖声明
└── .tmp/           # 搜索结果的封面图片缓存（每次搜索前自动清空）
```

## 注意事项

- 需要安装 Microsoft Edge 浏览器
- 爬取时自动添加随机延迟，避免对服务器造成压力
- 请遵守目标网站的 robots.txt 和使用条款
- 图片缓存目录 `.tmp/` 每次搜索前会自动清空

## License

MIT
