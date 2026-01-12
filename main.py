import asyncio
import aiohttp
import aiofiles
import random
from bs4 import BeautifulSoup

async def scrape_episode_summary(session, url, episode_num):
    """异步爬取单个剧集的剧情摘要"""
    try:
        # 随机延迟 1-3 秒
        await asyncio.sleep(random.uniform(0.2, 0.5))
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')

            # 1. 定位到主要的容器
            main_left_div = soup.find('div', class_='main-left')

            # 2. 提取标题
            title_tag = main_left_div.find('p', class_='epi_t')
            title = title_tag.get_text(strip=True) if title_tag else "未找到标题"

            # 3. 提取剧情内容
            article_tag = main_left_div.find('article', class_='epi_c')
            if article_tag:
                # 找到所有的段落 <p>
                paragraphs = article_tag.find_all('p')
                # 将每个段落的文本合并，用换行符连接
                content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
            else:
                content = "未找到剧情内容"
            return episode_num, title, content
    except Exception as e:
        return episode_num, f"第{episode_num}集", f"错误: {str(e)}"

async def main():
    # 生成URL列表
    # https://www.tvmao.com/drama/Li4kNGg=/episode/13-41 海棠依旧的第41集url
    base_url = "https://www.tvmao.com/drama/Li4kNGg=/episode/"
    total_episodes = 41  # 假设总集数为100，可以修改
    episode_urls = []
    for i in range(1, total_episodes + 1):
        prefix = (i - 1) // 3
        url = f"{base_url}{prefix}-{i}"
        episode_urls.append(url)

    #第1集url特别处理
    episode_urls[0] = base_url[:-1]



    async with aiohttp.ClientSession(headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }) as session:
        tasks = [scrape_episode_summary(session, url, i+1) for i, url in enumerate(episode_urls)]
        
        results = {}
        async with aiofiles.open('episodes_summary.txt', 'w', encoding='utf-8') as file:
            current_episode = 1
            for coro in asyncio.as_completed(tasks):
                episode_num, title, content = await coro
                results[episode_num] = (title, content)
                # 检查是否可以写入顺序的集
                while current_episode in results:
                    title, content = results[current_episode]
                    await file.write(f"{title}:\n{content}\n\n")
                    print(f"已写入第{current_episode}集")
                    del results[current_episode]
                    current_episode += 1

    print("爬取完成，结果已保存到 episodes_summary.txt")

if __name__ == "__main__":
    asyncio.run(main())
