import configparser
import json
import pathlib
from time import sleep

import requests
from playwright.sync_api import sync_playwright

from conf import BASE_DIR, XHS_SERVER, LOCAL_CHROME_HEADLESS

config = configparser.RawConfigParser()
config.read('accounts.ini')


def sign_local(uri, data=None, a1="", web_session=""):
    for _ in range(10):
        try:
            with sync_playwright() as playwright:
                stealth_js_path = pathlib.Path(BASE_DIR / "utils/stealth.min.js")
                chromium = playwright.chromium

                # se falhar sempre, ponha False para abrir o navegador; um sleep ajuda a ver o que acontece
                browser = chromium.launch(headless=LOCAL_CHROME_HEADLESS)

                browser_context = browser.new_context()
                browser_context.add_init_script(path=stealth_js_path)
                context_page = browser_context.new_page()
                context_page.goto("https://www.xiaohongshu.com")
                browser_context.add_cookies([
                    {'name': 'a1', 'value': a1, 'domain': ".xiaohongshu.com", 'path': "/"}]
                )
                context_page.reload()
                # depois de definir o cookie no navegador é preciso um sleep aqui, senão a assinatura falha; se falhar muito, aumente o tempo
                sleep(2)
                encrypt_params = context_page.evaluate("([url, data]) => window._webmsxyw(url, data)", [uri, data])
                return {
                    "x-s": encrypt_params["X-s"],
                    "x-t": str(encrypt_params["X-t"])
                }
        except Exception:
            # às vezes aparece "window._webmsxyw is not a function" ou uma navegação inesperada, por isso a repetição
            pass
    raise Exception("tentei várias vezes e a assinatura não saiu")


def sign(uri, data=None, a1="", web_session=""):
    # ponha aqui o endereço do seu serviço flask de assinatura
    res = requests.post(f"{XHS_SERVER}/sign",
                        json={"uri": uri, "data": data, "a1": a1, "web_session": web_session})
    signs = res.json()
    return {
        "x-s": signs["x-s"],
        "x-t": signs["x-t"]
    }


def beauty_print(data: dict):
    print(json.dumps(data, ensure_ascii=False, indent=2))
