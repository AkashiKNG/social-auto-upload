# -*- coding: utf-8 -*-
"""Login por QR code no Baijiahao (sem janela) e gravação do cookie.

Observações:
  - o navegador sem janela abre a tela de login do Baijiahao, recorta o QR code, amplia e salva como png,
    e também mostra o QR code em ASCII no terminal; escaneie pelo celular ou pelo app da Baidu.
  - escaneado o QR code, a sessão é gravada em cookies/baijiahao_uploader/account.json.

Uso:
    python examples/get_baijiahao_cookie_headless.py
"""
from pathlib import Path

from playwright.async_api import async_playwright
from conf import BASE_DIR
from utils.login_qrcode import (
    build_login_qrcode_path,
    print_terminal_qrcode,
)
from uploader.baijiahao_uploader.main import cookie_auth, baijiahao_logger


QR_SELECTOR = 'img[src^="https://passport.baidu.com/v2/api/qrcode"]'
# o texto abaixo fica em chinês de propósito: é o que a página do Baijiahao mostra no botão
LOGIN_BTN_TEXT = "登录"
LOGIN_URL = "https://baijiahao.baidu.com/builder/theme/bjh/login"


async def _grab_qr(page, qrcode_path: Path) -> str:
    qr = page.locator(QR_SELECTOR).first
    await qr.wait_for(state="attached", timeout=60000)
    src = await qr.get_attribute("src")
    if src and src.startswith("https://"):
        resp = await page.context.request.get(src)
        qrcode_path.parent.mkdir(parents=True, exist_ok=True)
        qrcode_path.write_bytes(await resp.body())
    else:
        await qr.screenshot(path=str(qrcode_path))

    qrcode_content = ""
    try:
        import cv2
        img = cv2.imread(str(qrcode_path))
        if img is not None:
            h, w = img.shape[:2]
            up = cv2.resize(img, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
            qrcode_content = cv2.QRCodeDetector().detectAndDecode(up)[0] or ""
    except Exception:
        pass
    return qrcode_content or ""


async def _wait_login(page, max_checks: int = 120, interval: int = 3) -> bool:
    import asyncio
    async def _logged_in():
        if "login" in page.url:
            return False
        ctx = page.context
        cookies = await ctx.cookies()
        if any(c.get("name") in ("BDUSS", "STOKEN") for c in cookies):
            return True
        return False

    for _ in range(max_checks):
        if await _logged_in():
            return True
        await asyncio.sleep(interval)
    return False


async def main():
    account_file = Path(BASE_DIR / "cookies" / "baijiahao_uploader" / "account.json")
    account_file.parent.mkdir(parents=True, exist_ok=True)

    import os
    if os.path.exists(account_file) and await cookie_auth(str(account_file)):
        baijiahao_logger.success("[+] o cookie ainda vale; não precisa entrar de novo")
        return

    qrcode_path = build_login_qrcode_path(str(account_file))
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        # abre a janela de login
        await page.get_by_text(LOGIN_BTN_TEXT, exact=True).first.click(timeout=10000)
        await page.wait_for_timeout(4000)

        qrcode_content = await _grab_qr(page, qrcode_path)
        baijiahao_logger.info(f"🖼️ QR code salvo em: {qrcode_path}")
        if qrcode_content:
            print_terminal_qrcode(qrcode_content, qrcode_path, "app da Baidu")
        else:
            print(f"não consegui decodificar o QR code; abra o arquivo e escaneie:\n  {qrcode_path}")

        if await _wait_login(page):
            baijiahao_logger.success("[+] login por QR code concluído; salvando o cookie...")
            await context.storage_state(path=str(account_file))
            baijiahao_logger.success(f"[+] cookie salvo em: {account_file}")
        else:
            baijiahao_logger.error("[-] tempo esgotado esperando o QR code (uns 6 minutos); login não concluído.")
        await browser.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())