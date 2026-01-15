from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re


def find_href():
    options = webdriver.EdgeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-logging","enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1920,1080")  # 或更大的尺寸
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    options.add_argument(f'--user-agent={user_agent}')
    options.add_argument('--log-level=0')
    # prefs = {"profile.managed_default_content_settings.images": 2}
    # options.add_experimental_option("prefs", prefs)
    options.add_argument("--log-level=INFO")  # 设置日志级别为INFO
    options.add_argument("-disable-web-security")  # 禁用Web安全
    options.add_argument("-disable-extensions")  # 禁用扩展
    options.add_argument("-disable-notifications")  # 禁用通知

    # 启动浏览器
    wd = webdriver.Edge(options=options)
    wd.implicitly_wait(5)

    title = input("请输入要搜索的剧集名称：")
    wd.get('https://www.tvmao.com/')

    input_box = wd.find_element(By.CSS_SELECTOR, 'input#key')

    # 3. 先点击输入框，使其获得焦点
    input_box.click()
    time.sleep(0.5) # 短暂等待，确保焦点稳定

    input_box.clear()
    input_box.send_keys(title)

    wd.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()


    li_eles = wd.find_elements(By.CSS_SELECTOR, '#t_q_tab_drama > li')

    info = []
    for i, li in enumerate(li_eles):
        title = li.find_element(By.TAG_NAME, 'a').get_attribute('title')
        href = li.find_element(By.TAG_NAME, 'a').get_attribute('href')
        episodes_num = li.find_element(By.CLASS_NAME, 'maskTx').text.strip()

        print(f"{i} 标题:{title}  集数:{episodes_num} href:{href}")

        info.append({
            'title': title,
            'href': href,
            'episodes_num': episodes_num
        })


    index = int(input("选择你需要的剧集(填入数字id):"))

    print(f"你选择的剧集是: {info[index]}")

    wd.quit()

    return info[index]


def data_process():
    drama_info = find_href()

    title = drama_info['title'][:-4]
    numbers = re.findall(r'\d+', drama_info['episodes_num'])[0]

    data = {
        'title': title,
        'episodes_num': int(numbers),
        'base_url': drama_info['href']
    }
    return data

if __name__ == "__main__":
    data_process()
