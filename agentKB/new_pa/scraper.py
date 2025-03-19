import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re
import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import base64

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=2560,1440')
    options.add_argument('--force-device-scale-factor=1')
    options.add_argument('--enable-print-browser')
    options.add_argument('--kiosk-printing')
    options.add_argument('--hide-scrollbars')
    options.add_argument('--print-to-pdf-no-header')
    options.add_argument('--hide-scrollbars')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_valid_filename(title):
    return re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')

def save_as_pdf(driver, output_path):
    # 移除页面中的无关元素
    driver.execute_script(
        """
        const elementsToRemove = [
            '.header', '.footer', '.banner',
            '.company-info', '.nav-bar', '.contact-info','content-left',
            '.top-bar', '.novobottom', '.cebianlan.pailie[data-id="zt"]',
            '.linkurl.duichen.jiegou'
        ];
        elementsToRemove.forEach(selector => {
            document.querySelectorAll(selector).forEach(element => element.remove());
        });
        """
    )
    try:
        time.sleep(3)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        result = driver.execute_cdp_cmd('Page.printToPDF', {
            'landscape': False,
            'displayHeaderFooter': False,
            'ignoreCSSPageRules': True,
            'preferCSSPageSize': True,
            'headerTemplate': '<span></span>',
            'footerTemplate': '<span></span>',
            'printBackground': True,
            'paperWidth': 8.27,
            'paperHeight': 11.69,
            'marginTop': 0,
            'marginBottom': 0,
            'marginLeft': 0,
            'marginRight': 0
        })
        
        with open(output_path, 'wb') as f:
            f.write(base64.b64decode(result['data']))
            
        return os.path.exists(output_path)
    except Exception as e:
        print(f"保存PDF失败: {e}")
        return False

def wait_for_element(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        print(f"等待元素超时: {selector}")
        return None

def download_image(url, save_path):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return False

def extract_content(driver, section_title, content_dir):
    content = [f'# {section_title}\n']
    
    # 等待主体内容加载
    content_selector = '.content'
    content_element = wait_for_element(driver, content_selector)
    if not content_element:
        return None
    
    # 移除左侧导航栏内容
    try:
        nav_elements = content_element.find_elements(By.CSS_SELECTOR, '.sidebar-left, .left-menu')
        for nav in nav_elements:
            driver.execute_script("arguments[0].remove();", nav)
    except Exception as e:
        print(f"移除导航栏时出错: {e}")
    
    # 提取声明内容
    try:
        notice_elements = content_element.find_elements(By.CSS_SELECTOR, '.notice, .warning, .alert')
        if notice_elements:
            content.append('## 重要声明\n')
            for notice in notice_elements:
                notice_text = notice.text.strip()
                if notice_text:
                    content.append(f'> {notice_text}\n')
    except Exception as e:
        print(f"提取声明内容时出错: {e}")
    
    # 获取所有相关元素
    elements = content_element.find_elements(By.CSS_SELECTOR, 'h2, h3, h4, p, ul, ol, table, img')
    
    img_counter = 1
    for element in elements:
        try:
            tag_name = element.tag_name
            
            # 处理图片
            if tag_name == 'img':
                src = element.get_attribute('src')
                if src:
                    if not src.startswith('http'):
                        base_url = driver.current_url
                        src = urllib.parse.urljoin(base_url, src)
                    
                    img_filename = f'image_{img_counter}.png'
                    img_path = os.path.join(content_dir, 'images', img_filename)
                    os.makedirs(os.path.dirname(img_path), exist_ok=True)
                    
                    if download_image(src, img_path):
                        content.append(f'\n![{img_filename}](images/{img_filename})\n')
                        img_counter += 1
                continue
            
            # 处理表格
            if tag_name == 'table':
                rows = element.find_elements(By.TAG_NAME, 'tr')
                if not rows:
                    continue
                    
                table_content = ['\n']
                # 处理表头
                header = rows[0].find_elements(By.TAG_NAME, 'th')
                if header:
                    header_texts = [cell.text.strip() for cell in header]
                    table_content.append('|' + '|'.join(header_texts) + '|')
                    table_content.append('|' + '|'.join(['---' for _ in header_texts]) + '|')
                
                # 处理数据行
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if cells:
                        row_texts = [cell.text.strip() for cell in cells]
                        table_content.append('|' + '|'.join(row_texts) + '|')
                
                if len(table_content) > 1:
                    content.extend(table_content)
                    content.append('\n')
                continue
            
            text = element.text.strip()
            if not text:
                continue
            
            # 处理标题
            if tag_name in ['h2', 'h3', 'h4']:
                level = int(tag_name[1])
                content.append(f'\n{"#" * level} {text}\n')
            # 处理列表
            elif tag_name in ['ul', 'ol']:
                content.append('')
                list_items = element.find_elements(By.TAG_NAME, 'li')
                for item in list_items:
                    item_text = item.text.strip()
                    if item_text:
                        content.append(f'- {item_text}')
                content.append('')
            # 处理段落
            elif tag_name == 'p':
                content.append(f'\n{text}\n')
                
        except Exception as e:
            print(f"处理元素时出错: {e}")
            continue
            
    return '\n'.join(content)

def scrape_urls():
    urls = [
        ('https://cn.novogene.com/novo/dzwjyzccx_syjy_405.html', '动植物重测序'),
        ('https://cn.novogene.com/novo/kzz_syjy_433.html', '扩增子'),
        ('https://cn.novogene.com/novo/hjyz_syjy_434.html', '宏基因组'),
        ('https://cn.novogene.com/novo/dj_zj_xj_syjy_435.html', '单菌(真菌/细菌)'),
        ('https://cn.novogene.com/novo/sd1dnayb_syjy_387.html', '三代DNA产品'),
        ('https://cn.novogene.com/novo/sd2rnayb_syjy_388.html', '三代RNA产品'),
        ('https://cn.novogene.com/novo/sd3wswyb_syjy_389.html', '三代微生物产品'),
        ('https://cn.novogene.com/novo/ptzlz_syjy_429.html', '真核转录组'),
        ('https://cn.novogene.com/novo/yhzlz_syjy_436.html', '原核转录组')
    ]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    content_dir = os.path.join(base_dir, 'content')
    pdf_dir = os.path.join(content_dir, 'pdfs')
    
    def create_dirs():
        os.makedirs(pdf_dir, exist_ok=True)
    
    try:
        with setup_driver() as driver:
            print("浏览器初始化完成")
            create_dirs()
            
            for url, title in urls:
                try:
                    driver.get(url)
                    time.sleep(2)
                    
                    filename = get_valid_filename(title)
                    pdf_path = os.path.join(pdf_dir, f'{filename}.pdf')
                    
                    if save_as_pdf(driver, pdf_path):
                        print(f"成功保存: {filename}.pdf")
                    
                except Exception as e:
                    print(f"处理{title}时出错: {str(e)[:50]}")
                    continue
    
    except Exception as e:
        print(f"主程序错误: {str(e)[:50]}")
    finally:
        print("程序执行完毕")

if __name__ == '__main__':
    scrape_urls()