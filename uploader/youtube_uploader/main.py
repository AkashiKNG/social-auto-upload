# -*- coding: utf-8 -*-
"""YouTube uploader (browser automation via YouTube Studio).

Unlike the other platforms here, YouTube also offers an official Data API. We deliberately
use browser automation instead, because videos uploaded through an *unaudited* API project
are force-locked to private and cannot be made public without passing Google's compliance
audit (which is impractical for personal/single-channel use). Browser automation has no such
restriction and can publish public videos right away, and it matches the cookie-based pattern
used by every other uploader in this project.

Login is interactive (Google account, no QR code): the browser opens, the user signs in, and
the storage_state is saved. Reuse it afterwards for fully unattended uploads.
"""
import asyncio
from pathlib import Path

from patchright.async_api import Page, Playwright, async_playwright

from conf import DEBUG_MODE
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import youtube_logger

try:
    # Onde o youtube.com é bloqueado a conexão direta estoura o tempo, e o chromium do patchright ignora o proxy do sistema.
    # defina YT_PROXY no conf.py = "http://127.0.0.1:7890" (porta do proxy local)basta; sem isso, não usa proxy.
    from conf import YT_PROXY
except Exception:
    YT_PROXY = None

STUDIO_URL = "https://studio.youtube.com"
UPLOAD_URL = "https://www.youtube.com/upload"
VISIBILITY = {"public": "PUBLIC", "unlisted": "UNLISTED", "private": "PRIVATE"}


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _build_login_result(success, status, message, account_file, current_url=""):
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "current_url": current_url,
    }


async def cookie_auth(account_file) -> bool:
    """A sessão ainda vale? Abre o Studio com o cookie: se não cair na tela de login do Google e chegar ao canal, está valendo."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(STUDIO_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            url = page.url
            if "accounts.google.com" in url or "/signin" in url.lower():
                return False
            return "/channel/" in url
        except Exception:
            return False
        finally:
            await browser.close()


async def youtube_cookie_gen(account_file, headless: bool = False):
    """Login interativo: abre o navegador para entrar no Google/YouTube e, já no canal, salva o storage_state."""
    async with async_playwright() as playwright:
        # o login precisa de janela visível para digitar senha e a verificação em duas etapas
        browser = await playwright.chromium.launch(headless=False, channel="chrome")
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto(STUDIO_URL, wait_until="domcontentloaded")
        youtube_logger.info(_msg("🔐", "Entre na conta Google / YouTube na janela que abriu; a sessão é salva sozinha"))
        ok = False
        for _ in range(600):  # espera no máximo 10 minutos
            if "/channel/" in page.url:
                await page.wait_for_timeout(2000)  # deixa o cookie assentar
                ok = True
                break
            await asyncio.sleep(1)
        if ok:
            await context.storage_state(path=account_file)
            youtube_logger.success(_msg("✅", f"YouTube sessão salva: {account_file}"))
        else:
            youtube_logger.error(_msg("😵", "tempo esgotado esperando o login; sessão não foi salva"))
        await browser.close()
        return _build_login_result(ok, "logged_in" if ok else "timeout",
                                   "login concluído" if ok else "tempo esgotado no login", account_file, page.url)


async def youtube_setup(account_file, handle: bool = False, return_detail: bool = False, headless: bool = False):
    """confere a sessão; se expirou e handle=True dispara o login interativo."""
    if not Path(account_file).exists() or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "sem sessão ou sessão expirada", account_file)
            return result if return_detail else False
        youtube_logger.info(_msg("🥹", "YouTube sem sessão válida: vou abrir o navegador para entrar"))
        result = await youtube_cookie_gen(account_file, headless=headless)
        return result if return_detail else result["success"]
    result = _build_login_result(True, "cookie_valid", "sessão válida", account_file)
    return result if return_detail else True


async def _dismiss_autocomplete(page: Page):
    """fecha # hashtag / @ camada de sugestão de menção (cobriria os botões de continuar/publicar).

    primeiro tira o foco; se a camada continuar visível, manda um Escape — só quando ela existe,
    evita fechar a janela de envio inteira quando não há camada nenhuma."""
    try:
        await page.evaluate("() => { const a = document.activeElement; if (a && a.blur) a.blur(); }")
    except Exception:
        pass
    try:
        dropdown = page.locator("tp-yt-iron-dropdown:visible")
        if await dropdown.count() > 0:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(200)
    except Exception:
        pass


async def _fill_editable(page: Page, selector: str, text: str):
    """preenche o campo de texto rico (contenteditable) do YouTube Studio (título/descrição), limpa antes de digitar.

    usa fill() de uma vez, não type() letra a letra: um # no título/descrição (ex.: #Shorts) dispara a
    YouTube camada de sugestão de hashtag; digitar letra a letra faz ela seguir o cursor e cobrir o campo e
    sugestão que cobre os botões de continuar/publicar e trava o envio. Com fill() isso não acontece."""
    box = page.locator(selector).first
    await box.wait_for(state="visible", timeout=30000)
    await box.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Delete")
    try:
        await box.fill(text)            # de uma vez, sem disparar a sugestão de hashtag
    except Exception:
        await box.type(text, delay=6)   # em contenteditable que não aceita fill, volta a digitar letra a letra
    await page.wait_for_timeout(400)
    await _dismiss_autocomplete(page)   # no fim, fecha a camada de sugestão que possa ter aparecido


async def _click_if_present(page: Page, selector: str, timeout: int = 4000) -> bool:
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=timeout)
        await el.click()
        return True
    except Exception:
        return False


async def _wait_upload_complete(page: Page, max_polls: int = 360) -> bool:
    """espera o envio ir de X% a 100% antes de publicar; o navegador só termina com a janela aberta,
    publicar no meio do envio e fechar o navegador corta a transferência pela metade (ex.: 76%).
    considera terminado quando aparece processando/verificando/enviado ou some o "enviando". max_polls*5s=30min limite."""
    last = ""
    for _ in range(max_polls):
        txt = ""
        for sel in (".progress-label", "span.progress-label", "ytcp-video-upload-progress"):
            loc = page.locator(sel).first
            try:
                if await loc.count():
                    txt = (await loc.inner_text()).strip()
                    if txt:
                        break
            except Exception:
                pass
        if txt:
            # os quatro primeiros são o texto da própria página em chinês: não traduzir
            if any(k in txt for k in ("处理", "检查", "上传完成", "已上传", "Processing", "complete", "Checks", "Finished")):
                youtube_logger.info(_msg("✅", f"envio concluído: {txt[:40]}"))
                return True
            if txt != last:
                youtube_logger.info(_msg("⏳", f"enviando: {txt[:40]}"))
                last = txt
        await page.wait_for_timeout(5000)
    youtube_logger.warning(_msg("⚠️", "tempo esgotado esperando o envio(30min), tenta publicar assim mesmo"))
    return False


class YouTubeVideo(BaseVideoUploader):
    def __init__(self, title, file_path, tags, account_file, *,
                 description="", thumbnail_path=None, playlist=None,
                 visibility="public", debug=DEBUG_MODE, headless=False):
        self.title = title
        self.file_path = str(file_path)
        self.tags = tags or []
        self.account_file = str(account_file)
        self.description = description or ""
        self.thumbnail_path = str(thumbnail_path) if thumbnail_path else None
        self.playlist = playlist
        self.visibility = visibility if visibility in VISIBILITY else "public"
        self.debug = debug
        self.headless = headless

    async def upload(self, playwright: Playwright) -> None:
        browser = await playwright.chromium.launch(
            headless=self.headless, channel="chrome",
            proxy={"server": YT_PROXY} if YT_PROXY else None,
        )
        context = await browser.new_context(storage_state=self.account_file)
        context = await set_init_script(context)
        page = await context.new_page()
        page.set_default_timeout(60000)

        youtube_logger.info(_msg("🎬", f"começando o envio: {Path(self.file_path).name}"))
        await page.goto(UPLOAD_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        if "accounts.google.com" in page.url or "signin" in page.url.lower():
            await browser.close()
            raise RuntimeError("YouTube sessão expirada: rode o login de novo")

        # 1) escolhe o arquivo de vídeo
        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=60000)
        await file_input.set_input_files(self.file_path)

        # 2) espera a janela de detalhes
        await page.locator("#title-textarea").wait_for(state="visible", timeout=120000)

        # 3) título
        youtube_logger.info(_msg("✍️", "preenche o título"))
        await _fill_editable(page, "#title-textarea #textbox", self.title[:100])

        # 4) descrição
        if self.description.strip():
            youtube_logger.info(_msg("✍️", "preenche a descrição"))
            await _fill_editable(page, "#description-textarea #textbox", self.description)

        # 5) miniatura (só libera depois de certo progresso; falhar aqui não é grave)
        if self.thumbnail_path and Path(self.thumbnail_path).exists():
            try:
                thumb_input = page.locator(
                    "#file-loader input[type='file'], ytcp-thumbnail-uploader input[type='file']"
                ).first
                await thumb_input.wait_for(state="attached", timeout=20000)
                await thumb_input.set_input_files(self.thumbnail_path)
                await page.wait_for_timeout(2000)
                youtube_logger.info(_msg("🖼️", "miniatura enviada"))
            except Exception as exc:
                youtube_logger.warning(_msg("⚠️", f"miniatura ignorada (não impede a publicação): {exc}"))

        # 6) adiciona à playlist (séries e conteúdo em capítulos).a janela precisa fechar, senão atrapalha os passos seguintes.
        if self.playlist:
            try:
                await _click_if_present(
                    page, "#basics ytcp-text-dropdown-trigger, ytcp-video-metadata-playlists ytcp-dropdown-trigger", 8000)
                await page.wait_for_timeout(1200)
                existing = page.locator(
                    f"tp-yt-paper-checkbox:has-text('{self.playlist}'), "
                    f"ytcp-checkbox-group:has-text('{self.playlist}')").first
                if await existing.count():
                    await existing.click()
                else:
                    if await _click_if_present(page, "ytcp-button:has-text('New playlist'), ytcp-button:has-text('创建播放列表')", 4000):
                        await page.wait_for_timeout(800)
                        await _click_if_present(page, "tp-yt-paper-item:has-text('New playlist'), tp-yt-paper-item:has-text('新建播放列表')", 3000)
                        title_box = page.locator("ytcp-playlist-metadata-editor #textbox, #create-playlist-form #textbox").first
                        if await title_box.count():
                            await title_box.click()
                            await title_box.type(self.playlist, delay=6)
                            await _click_if_present(page, "ytcp-button#create-button, tp-yt-paper-dialog ytcp-button:has-text('Create'), tp-yt-paper-dialog ytcp-button:has-text('创建')", 4000)
            except Exception as exc:
                youtube_logger.warning(_msg("⚠️", f"playlist ignorada (não impede a publicação): {exc}"))
            finally:
                await _click_if_present(page, "ytcp-playlist-dialog #save-button, ytcp-button:has-text('Done'), ytcp-button:has-text('完成')", 3000)
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(600)

        # 7) público: não é conteúdo infantil (obrigatório)
        if not await _click_if_present(page, "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']", 10000):
            await _click_if_present(page, "tp-yt-paper-radio-button:has-text('not made for kids'), tp-yt-paper-radio-button:has-text('不是面向儿童')", 6000)

        # 8) etiquetas ("dentro de" mostrar mais ")
        if self.tags:
            try:
                await _click_if_present(page, "#toggle-button", 6000)
                await page.wait_for_timeout(800)
                tag_input = page.locator("#tags-container #text-input, ytcp-form-input-container#tags-container input").first
                await tag_input.click()
                await tag_input.type(",".join(self.tags)[:500] + ",", delay=4)
            except Exception as exc:
                youtube_logger.warning(_msg("⚠️", f"etiquetas ignoradas (não impede a publicação): {exc}"))

        # 9) clica em Avançar até o passo de visibilidade
        for _ in range(5):
            vis = page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
            if await vis.count() and await vis.first.is_visible():
                break
            if not await _click_if_present(page, "#next-button", 6000):
                await page.wait_for_timeout(1200)
            await page.wait_for_timeout(1000)

        # 10) visibilidade
        youtube_logger.info(_msg("🌐", f"define a visibilidade = {self.visibility}"))
        await _click_if_present(page, f"tp-yt-paper-radio-button[name='{VISIBILITY[self.visibility]}']", 10000)

        # 10.5) importante: só publica com o envio concluído; o navegador transfere enquanto a janela está aberta,
        #       publicar com o envio pela metade+fecha o navegador = o envio foi cortado no meio (ex.: 76%).
        youtube_logger.info(_msg("📤", "espera o envio terminar (só publica com o envio completo)…"))
        await _wait_upload_complete(page)

        # 11) publicar
        await page.wait_for_timeout(1200)
        if not await _click_if_present(page, "#done-button", 15000):
            youtube_logger.warning(_msg("🤔", "não achei o botão de publicar; o envio talvez ainda não tenha chegado lá — publique pela janela"))
        else:
            await page.wait_for_timeout(4000)
            video_url = ""
            try:
                link = page.locator("a[href*='youtu.be'], a[href*='watch?v=']").first
                if await link.count():
                    video_url = await link.get_attribute("href") or ""
            except Exception:
                pass
            await _click_if_present(page, "ytcp-button:has-text('Close'), ytcp-button:has-text('关闭'), #close-button", 8000)
            youtube_logger.success(_msg("🥳", f"publicado ({self.visibility}){(' ' + video_url) if video_url else ''}"))

        # renova o cookie
        try:
            await context.storage_state(path=self.account_file)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        await browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
