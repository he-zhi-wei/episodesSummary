from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re

import asyncio
import aiohttp
import aiofiles
import random
import os

class DramaInfo:
    def __init__(self):
        self.title = None
        self.wd = None
        self.options = webdriver.EdgeOptions()
        self.info = []

    def webdriver_optionset(self):
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option("excludeSwitches", ["enable-logging","enable-automation"])
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument('--headless')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument("--window-size=1920,1080")  # 或更大的尺寸
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.options.add_argument(f'--user-agent={user_agent}')
        self.options.add_argument('--log-level=0')
        # prefs = {"profile.managed_default_content_settings.images": 2}
        # options.add_experimental_option("prefs", prefs)
        self.options.add_argument("--log-level=INFO")  # 设置日志级别为INFO
        self.options.add_argument("-disable-web-security")  # 禁用Web安全
        self.options.add_argument("-disable-extensions")  # 禁用扩展
        self.options.add_argument("-disable-notifications")  # 禁用通知

    def webdriver_set(self):
        self.webdriver_optionset()
        self.wd = webdriver.Edge(options=self.options)
        self.wd.implicitly_wait(5)

    def search(self, title):
        self.webdriver_set()
        self.title = title
        self.wd.get('https://www.tvmao.com/')
        input_box = self.wd.find_element(By.CSS_SELECTOR, 'input#key')

        # 先点击输入框，使其获得焦点
        input_box.click()
        time.sleep(0.5)

        input_box.clear()
        input_box.send_keys(self.title)

        self.wd.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        li_eles = self.wd.find_elements(By.CSS_SELECTOR, '#t_q_tab_drama > li')

        for i, li in enumerate(li_eles):
            title = li.find_element(By.TAG_NAME, 'a').get_attribute('title')
            href = li.find_element(By.TAG_NAME, 'a').get_attribute('href')
            episodes_num = li.find_element(By.CLASS_NAME, 'maskTx').text.strip()
            img_url = li.find_element(By.TAG_NAME, 'img').get_attribute('src')

            # print(f"{i} 标题:{title}  集数:{episodes_num} href:{href}")

            self.info.append({
                'id': i,
                'title': title,
                'href': href,
                'episodes_num': episodes_num,
                'img_url': img_url
            })
        
        self.wd.quit()
    
    def get_drama_list(self):
        return self.info

    



class DataProcess:
    def __init__(self, info_item):
        self.data = info_item
        self.process_data = None

    def process(self):
        title = self.data['title'][:-4]
        numbers = re.findall(r'\d+', self.data['episodes_num'])[0]
        self.process_data = {
            'title': title,
            'episodes_num': int(numbers),
            'base_url': self.data['href'],
            'img_url': self.data['img_url']
        }

    def get_process_data(self):
        return self.process_data

class DownloadImg:
    def __init__(self, data_array):
        self.data_array = data_array

    async def scrape_and_save_img(self, session, url, img_path, i):
        """异步爬取单个剧集的剧情摘要"""
        try:
            # 随机延迟
            await asyncio.sleep(random.uniform(0.2, 0.5))
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                img_data = await response.read()

                async with aiofiles.open(img_path, 'wb') as file:
                    await file.write(img_data)
                    print(f"已写入第{i}张图片")
        except Exception as e:
            print(f"第{i}张图片", f"错误: {str(e)}")


    async def scrape_all_img(self):
        if not os.path.exists('.tmp'):
            os.mkdir('.tmp')
        
        async with aiohttp.ClientSession(headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }) as session:
            tasks = [self.scrape_and_save_img(session, data['img_url'], f'.tmp/img_{data["id"]}.jpg', i) 
                    for i, data in enumerate(self.data_array)]
            
            await asyncio.gather(*tasks)

        print(f"爬取完成")


if __name__ == '__main__':
    drama_info = DramaInfo()
    drama_info.search('海棠')
    data_array = drama_info.get_drama_list()

    imgd = DownloadImg(data_array)
    asyncio.run(imgd.scrape_all_img())

