import asyncio
import sqlite3

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
import uuid
from pathlib import Path
from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH

# configuração única do navegador (evita bloqueio e permite usar o Chrome local)
def get_browser_options():
    options = {
        'headless': LOCAL_CHROME_HEADLESS,
        'args': [
            '--disable-blink-features=AutomationControlled',  # esconde window.navigator.webdriver, a marca que entrega a automação
            '--lang=zh-CN',
            '--disable-infobars',
            '--start-maximized'
        ]
    }
    # com o Chrome local configurado no conf.py, a taxa de sucesso é bem maior
    if LOCAL_CHROME_PATH:
        options['executable_path'] = LOCAL_CHROME_PATH

    return options

# login do Douyin
async def douyin_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # só interessa a mudança do frame principal
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = get_browser_options()
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        original_url = page.url
        img_locator = page.get_by_role("img", name="二维码")
        # pega o atributo src
        src = await img_locator.get_attribute("src")
        print("✅ endereço da imagem:", src)
        status_queue.put(src)
        # escuta o evento 'framenavigated', só do frame principal
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)
        try:
            # espera a URL mudar (ou estourar o tempo)
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # no máximo 200 s
            print("a página navegou como esperado")
        except asyncio.TimeoutError:
            print("tempo esgotado esperando a navegação")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # garante que a pasta cookiesFile existe
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(3, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status)
                                VALUES (?, ?, ?, ?)
                                ''', (3, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ sessão do usuário salva")
        status_queue.put("200")


# login do Canal do WeChat
async def get_tencent_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # só interessa a mudança do frame principal
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        original_url = page.url

        # escuta o evento 'framenavigated', só do frame principal
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        # espera o iframe aparecer (até 60 s)
        iframe_locator = page.frame_locator("iframe").first

        # pega a primeira img dentro do iframe
        img_locator = iframe_locator.get_by_role("img").first

        # pega o atributo src
        src = await img_locator.get_attribute("src")
        print("✅ endereço da imagem:", src)
        status_queue.put(src)

        try:
            # espera a URL mudar (ou estourar o tempo)
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # no máximo 200 s
            print("a página navegou como esperado")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("tempo esgotado esperando a navegação")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # garante que a pasta cookiesFile existe
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(2,f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status)
                                VALUES (?, ?, ?, ?)
                                ''', (2, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ sessão do usuário salva")
        status_queue.put("200")

# login do Kuaishou
async def get_ks_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # só interessa a mudança do frame principal
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com")

        # acha e clica no botão de entrar (é um link)
        await page.get_by_role("link", name="立即登录").click()
        await page.get_by_text("扫码登录").click()
        img_locator = page.get_by_role("img", name="qrcode")
        # pega o atributo src
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ endereço da imagem:", src)
        status_queue.put(src)
        # escuta o evento 'framenavigated', só do frame principal
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # espera a URL mudar (ou estourar o tempo)
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # no máximo 200 s
            print("a página navegou como esperado")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("tempo esgotado esperando a navegação")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # garante que a pasta cookiesFile existe
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(4, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                        INSERT INTO user_info (type, filePath, userName, status)
                                        VALUES (?, ?, ?, ?)
                                        ''', (4, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ sessão do usuário salva")
        status_queue.put("200")

# login do Xiaohongshu
async def xiaohongshu_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # só interessa a mudança do frame principal
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.xiaohongshu.com/")
        await page.locator('img.css-wemwzq').click()

        img_locator = page.get_by_role("img").nth(2)
        # pega o atributo src
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ endereço da imagem:", src)
        status_queue.put(src)
        # escuta o evento 'framenavigated', só do frame principal
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # espera a URL mudar (ou estourar o tempo)
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # no máximo 200 s
            print("a página navegou como esperado")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("tempo esgotado esperando a navegação")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # garante que a pasta cookiesFile existe
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(1, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO user_info (type, filePath, userName, status)
                           VALUES (?, ?, ?, ?)
                           ''', (1, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ sessão do usuário salva")
        status_queue.put("200")

# a = asyncio.run(xiaohongshu_cookie_gen(4,None))
# print(a)
