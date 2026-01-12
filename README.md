# Episodes Summary Scraper

这是一个用于爬取电视猫中电视剧每集剧情摘要的Python项目。

## 安装依赖

首先，安装依赖项：

```bash
pip install -e .
```

## 使用方法

1. 编辑 `main.py` 中的 `episode_urls` 列表，添加每集剧情页面的URL。
2. 根据目标网站的HTML结构，调整 `scrape_episode_summary` 函数中的选择器（例如，查找剧情文本的CSS类）。
3. 运行脚本：

```bash
python main.py
```

4. 结果将保存到 `episodes_summary.txt` 文件中，每集剧情按顺序写入。

## 注意事项

- 请遵守网站的robots.txt和使用条款。
- 添加适当的延迟以避免对服务器造成过大压力。
- 如果网站有反爬虫措施，可能需要添加User-Agent或其他头信息。