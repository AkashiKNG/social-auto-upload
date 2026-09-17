# -*- coding: utf-8 -*-
"""Hupu envio de vídeo + login manual e cookie salvo.

o que faz: 
  - hupu_cookie_gen: abre o navegador para o usuário entrar (QQ/telefone etc.), salva o storage_state
  - cookie_auth: confere se o cookie ainda vale
  - hupu_setup: entrada única (verifica a sessão e, se preciso, faz login)
  - HuPuVideo: classe de envio de vídeo

adaptado de uma gravação do playwright codegen.
página de publicação: https://bbs.hupu.com/newpost?tabkey=2 (página de etiquetas do vídeo)
área: seletor fixo "Hupu — fórum → Hupu — via principal do fórum"

atenção: o Hupu detecta modo sem janela; só funciona com os parâmetros que escondem a automação.
"""
from __future__ import annotations

import asyncio
import inspect
import os
import re
import time
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.log import hupu_logger


HUPU_HOME_URL = "https://www.hupu.com/"
HUPU_LOGIN_URL = "https://passport.hupu.com/v2/login?pcPhone=1&jumpurl=https://www.hupu.com&from=https://www.hupu.com"
HUPU_PUBLISH_URL = "https://bbs.hupu.com/newpost?tabkey=2"

# padrão da URL do post para onde o Hupu vai depois de publicar
HUPU_POST_URL_PATTERN = re.compile(r"bbs\.hupu\.com/\d+\.html")

# user agent que disfarça a automação
_CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

# script que esconde o webdriver
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _build_login_result(success: bool, status: str, message: str, account_file: str, current_url: str = "") -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "current_url": current_url,
    }


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return
    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {
        "headless": headless,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if LOCAL_CHROME_PATH:
        launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
    return launch_kwargs


def _resolve_account_file(account_file: str | Path) -> str:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return str(path)
    if len(path.parts) == 1:
        return str((Path(BASE_DIR) / "cookies" / path).resolve())
    return str(path.resolve())


async def _create_stealth_context(browser, account_file: str | None = None) -> BrowserContext:
    """cria o contexto com as proteções contra detecção."""
    kwargs = {
        "user_agent": _CHROME_UA,
        "viewport": {"width": 1920, "height": 1080},
    }
    if account_file and os.path.exists(account_file):
        kwargs["storage_state"] = account_file
    context = await browser.new_context(**kwargs)
    return context


async def _new_stealth_page(context: BrowserContext) -> Page:
    """cria a página com o script que esconde a automação."""
    page = await context.new_page()
    await page.add_init_script(_STEALTH_SCRIPT)
    return page


async def hupu_cookie_gen(account_file, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 120, headless: bool = False):
    """QQ login por QR codeHupu, e salva o cookie.

    fluxo: abre a tela de login do Hupu → clica QQ login → recorta o QR code do QQ → esperando a leitura do QR code → salva o storage_state.
    funciona sem janela (mostra o QR code no terminal).
    """
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)
    result = _build_login_result(False, "failed", "falha no login do Hupu", account_file)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await _create_stealth_context(browser)
        try:
            page = await _new_stealth_page(context)
            await page.goto(HUPU_LOGIN_URL, timeout=60000, wait_until="load")
            await page.wait_for_timeout(3000)

            # clica QQ loginbotão
            qq_btn = page.get_by_role("button", name="qq QQ登录")
            if not await qq_btn.count():
                hupu_logger.error(_msg("😢", "não achei o botão de login do QQão"))
                result = _build_login_result(False, "failed", "não achei o botão de login do QQão", account_file, page.url)
                return result

            await qq_btn.click()
            await page.wait_for_timeout(5000)
            hupu_logger.info(_msg("🏃", "já está na tela de login do QQ"))

            # pega o QR code do iframe do QQ
            qrcode_info = await _grab_qq_qrcode(page, context, account_file)

            if qrcode_info:
                await _emit_qrcode_callback(qrcode_callback, qrcode_info)
                hupu_logger.info(_msg("🧍", "escaneie o QR code pelo aplicativo do QQ"))
            else:
                hupu_logger.warning(_msg("⚠️", "não consegui pegar o QR code do QQ; escaneie direto na janela do navegador"))

            # fica verificando até o login terminar
            for _ in range(max_checks):
                current_url = page.url
                # QQ autorizado, volta para a página inicial do Hupu
                if "www.hupu.com" in current_url and "passport" not in current_url and "graph.qq.com" not in current_url:
                    hupu_logger.info(_msg("🥳", f"logindeu certo, indo para: {current_url}"))
                    result = _build_login_result(True, "success", "login no Hupu pelo QQ concluído", account_file, current_url)
                    break
                # vê se realmente foi para a página de retorno do passport do Hupu (não é o que vem no parâmetro redirect_uri)
                if current_url.startswith("https://passport.hupu.com/pc/qqcallback"):
                    await page.wait_for_timeout(5000)
                    current_url = page.url
                    hupu_logger.info(_msg("🥳", f"QQ retorno bem-sucedido; atual: {current_url}"))
                    result = _build_login_result(True, "success", "login no Hupu pelo QQ concluído", account_file, current_url)
                    break
                # procura o u nos cookies (sessão principal)
                cookies = await context.cookies()
                if any(c.get("name") == "u" and c.get("value") for c in cookies):
                    hupu_logger.info(_msg("🥳", f"logindeu certo (achei o cookie u), atual: {current_url}"))
                    result = _build_login_result(True, "success", "login no Hupu pelo QQ concluído", account_file, current_url)
                    break
                await page.wait_for_timeout(poll_interval * 1000)
            else:
                result = _build_login_result(False, "timeout", "tempo esgotado esperando o login por QR code do QQ", account_file, page.url)

            if result["success"]:
                await asyncio.sleep(2)
                # garante que a página inicial carregou com o cookie
                if "www.hupu.com" not in page.url:
                    await page.goto(HUPU_HOME_URL, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)
                await context.storage_state(path=account_file)
                hupu_logger.success(_msg("🥳", f"cookie salvo: {account_file}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            # apaga o arquivo temporário do QR code
            qr_path = Path(account_file).parent / f"{Path(account_file).stem}_qq_qrcode.png"
            if qr_path.exists():
                qr_path.unlink()
            if not result["success"]:
                hupu_logger.error(_msg("😢", f"falha no login: {result['message']}"))
            await context.close()
            await browser.close()
    return result


async def _grab_qq_qrcode(page: Page, context: BrowserContext, account_file: str) -> dict | None:
    """pega o QR code dentro do iframe de login do QQ."""
    from utils.login_qrcode import decode_qrcode_from_path, print_terminal_qrcode

    # espera o iframe do QQ carregar (no máximo 15 s)
    qq_frame = None
    for _ in range(5):
        for frame in page.frames:
            if "xui.ptlogin2.qq.com" in frame.url or "ptlogin2.qq.com" in frame.url:
                qq_frame = frame
                break
        if qq_frame:
            break
        await asyncio.sleep(3)

    if not qq_frame:
        return None

    await asyncio.sleep(3)

    # pega a imagem do QR code (id="qrlogin_img")
    qr_selectors = ["#qrlogin_img", 'img[src*="ptqrshow"]', 'img[id*="qr"]']
    for sel in qr_selectors:
        qr_loc = qq_frame.locator(sel).first
        if await qr_loc.count():
            src = await qr_loc.get_attribute("src")
            if src and src.startswith("http"):
                # baixa a imagem do QR code
                try:
                    resp = await context.request.get(src)
                    qr_path = Path(account_file).parent / f"{Path(account_file).stem}_qq_qrcode.png"
                    qr_path.parent.mkdir(parents=True, exist_ok=True)
                    qr_path.write_bytes(await resp.body())

                    # tenta decodificar e mostrar no terminal
                    qrcode_content = decode_qrcode_from_path(qr_path)
                    if qrcode_content:
                        print_terminal_qrcode(qrcode_content, qr_path, "QQversão do celular")
                    else:
                        hupu_logger.warning(_msg("😵", f"o terminal não mostra o QR code; abra {qr_path} escanear o QR code"))

                    return {"image_path": str(qr_path), "image_data_url": ""}
                except Exception as exc:
                    hupu_logger.warning(_msg("⚠️", f"não consegui baixar o QR code do QQ: {exc}"))
                    continue

    return None


async def cookie_auth(account_file):
    """verificaçãoo cookie do Hupu ainda é válido.abre a página de publicação e vê se ela carrega."""
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await _create_stealth_context(browser, account_file)
            page = await _new_stealth_page(context)
            await page.goto(HUPU_PUBLISH_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # vê se houve redirecionamento para a página de login
            if "passport" in page.url or "login" in page.url:
                hupu_logger.info(_msg("🥹", "cookie expirado (redirecionado para a página de login)"))
                return False

            # vê se a página de publicação apareceu "enviar vídeo" botão (loginsó aparece depois)
            upload_btn = page.get_by_role("button", name="上传视频")
            if await upload_btn.count():
                hupu_logger.success(_msg("🥳", "cookie válido"))
                return True

            # reserva: procura o campo u no cookie
            cookies = await context.cookies()
            if any(c.get("name") == "u" and c.get("value") for c in cookies):
                hupu_logger.success(_msg("🥳", "cookie válido (u cookie existe)"))
                return True

            hupu_logger.info(_msg("🥹", "cookie expirado (nenhuma sessão encontrada)"))
            return False
        except Exception as exc:
            hupu_logger.warning(_msg("😵", f"cookie erro na verificação: tratando como expirado: {exc}"))
            return False
        finally:
            await browser.close()


async def hupu_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = False):
    """entrada única: confere o cookie → se estiver inválido e handle=True dispara o login manual."""
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie arquivo inexistente ou expirado", account_file)
            return result if return_detail else False
        hupu_logger.info(_msg("🥹", "cookie arquivo inexistente ou expirado, abrindo o navegador para você entrar"))
        result = await hupu_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie válido", account_file)
    return result if return_detail else True


class HuPuVideo(BaseVideoUploader):
    """Hupu envio de vídeo.

    fluxo: vai direto para a página de publicação → envia o arquivo de vídeo → preenche o título → preenche a descrição →
         envia a capa → escolhe a área (Hupu — via principal do fórum)→ escolhe original/conteúdo derivado → escolhe a declaração de IA →
         clica "confirma a publicação"→ espera ir para a página do post.
    """

    def __init__(
        self,
        title,
        file_path,
        tags,
        account_file,
        publish_date=0,
        desc: str | None = None,
        thumbnail_path: str | None = None,
        debug: bool = True,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.account_file = _resolve_account_file(account_file)
        self.publish_date = publish_date
        self.desc = desc or ""
        self.thumbnail_path = thumbnail_path
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH
        self.max_title_length = 40
        self.min_title_length = 4

    async def validate_upload_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookiearquivo inexistente; conclua antes o ídologin do Hupu: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookiearquivo expirado; conclua antes o ídologin do Hupu: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("o título do vídeo não pode ficar vazio")
        if len(self.title) < self.min_title_length:
            raise ValueError(f"vídeoo título precisa de pelo menos{self.min_title_length} caracteres")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_path:
            self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def upload(self, playwright: Playwright) -> None:
        hupu_logger.info(_msg("🧍", "confere o cookie e o arquivo de vídeo"))
        await self.validate_upload_args()
        hupu_logger.info(_msg("🥳", "verificação antes do envio concluída"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await _create_stealth_context(browser, self.account_file)

        try:
            page = await _new_stealth_page(context)
            # vai direto para o página de publicação do vídeo (pula o clique na página inicial)
            await page.goto(HUPU_PUBLISH_URL, timeout=60000, wait_until="load")
            await page.wait_for_timeout(5000)
            hupu_logger.info(_msg("🏃", f"começando o envio do vídeo: {self.title}"))

            # 1) envia o arquivo de vídeo
            await self._upload_video_file(page)

            # 2) preenche o título
            await self._fill_title(page)

            # 3) preenche a descrição
            await self._fill_description(page)

            # 4) envia a capa (se houver)
            if self.thumbnail_path:
                await self._upload_thumbnail(page)

            # 5) escolherárea (Hupu — fórum → Hupu — via principal do fórum)
            await self._select_zone(page)

            # 6) escolheroriginal/conteúdo derivado + AI declaração
            await self._check_declarations(page)

            # 7) clicapublicar
            await self._submit_publish(page)

            # salva o cookie
            await context.storage_state(path=self.account_file)
            hupu_logger.success(_msg("🥳", "cookie atualização concluída"))
        finally:
            await context.close()
            await browser.close()

    async def _upload_video_file(self, page: Page) -> None:
        """clica" enviar vídeo " botãoe define o arquivo."""
        upload_btn = page.get_by_role("button", name="上传视频")
        await upload_btn.wait_for(state="visible", timeout=15000)

        # define o arquivo pelo seletor de arquivos
        async with page.expect_file_chooser(timeout=10000) as fc_info:
            await upload_btn.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)
        hupu_logger.info(_msg("🏃", f"arquivo de vídeo escolhido: {self.file_path}"))

        # espera envio de vídeo pronto (dá para preencher assim que o campo de título aparecer)
        title_field = page.get_by_placeholder("请输入标题（最少4个字，最多40个字）")
        await title_field.wait_for(state="visible", timeout=300000)
        hupu_logger.info(_msg("🥳", "vídeo pronto"))

    async def _fill_title(self, page: Page) -> None:
        """Preenche o título (de 4 a 40 caracteres)."""
        title_field = page.get_by_placeholder("请输入标题（最少4个字，最多40个字）")
        await title_field.wait_for(state="visible", timeout=15000)
        title = self.title[:self.max_title_length]
        await title_field.click()
        await title_field.fill(title)
        hupu_logger.info(_msg("🏷️", f"título preenchido: {title}"))

    async def _fill_description(self, page: Page) -> None:
        """preenche a descrição."""
        desc_field = page.get_by_placeholder("请输入简介")
        if not await desc_field.count():
            hupu_logger.warning(_msg("⚠️", "não achei o campo de descrição"))
            return

        # monta a descrição: corpo do texto + etiquetas
        content = self.desc
        if self.tags:
            tag_str = " ".join(f"#{t}#" for t in self.tags)
            content = f"{content}\n{tag_str}" if content else tag_str

        if content:
            await desc_field.click()
            await desc_field.fill(content)
            hupu_logger.info(_msg("📝", f"descrição preenchida ({len(content)} caracteres)"))

    async def _upload_thumbnail(self, page: Page) -> None:
        """envia a capa: clica" trocar a capa "→ define o arquivo."""
        try:
            cover_span = page.locator("span").filter(has_text="更换封面")
            await cover_span.wait_for(state="visible", timeout=10000)

            # define a capa pelo seletor de arquivos
            async with page.expect_file_chooser(timeout=10000) as fc_info:
                await cover_span.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(self.thumbnail_path)
            hupu_logger.info(_msg("🏃", f"imagem de capa escolhida: {self.thumbnail_path}"))
            await page.wait_for_timeout(3000)
            hupu_logger.success(_msg("🖼️", "capa enviada"))
        except Exception as exc:
            hupu_logger.warning(_msg("⚠️", f"falha ao enviar a capa: {exc}, continua a publicação (usa a capa padrão)"))

    async def _select_zone(self, page: Page) -> None:
        """escolherárea: Hupu — fórum → Hupu — via principal do fórum."""
        try:
            # 录制脚本：page.get_by_label("发视频").get_by_text("添加专区").click()
            add_zone_btn = page.get_by_label("发视频").get_by_text("添加专区")
            await add_zone_btn.wait_for(state="visible", timeout=10000)
            await add_zone_btn.click()
            await page.wait_for_timeout(1500)

            # escolher "Hupu — fórum" categoria
            zone_dialog = page.get_by_label("添加专区")
            step_street = zone_dialog.locator("div").filter(has_text=re.compile(r"^步行街$"))
            await step_street.click()
            await page.wait_for_timeout(1000)

            # escolher "Hupu — via principal do fórum" subcategoria
            main_road = page.get_by_text("步行街主干道")
            await main_road.click()
            await page.wait_for_timeout(500)

            # clicaconfirmar
            confirm_btn = page.get_by_role("button", name="确 定")
            await confirm_btn.click()
            await page.wait_for_timeout(1000)
            hupu_logger.info(_msg("🏷️", "escolhidoárea: Hupu — via principal do fórum"))
        except Exception as exc:
            hupu_logger.warning(_msg("⚠️", f"escolherfalha na área: {exc}"))

    async def _check_declarations(self, page: Page) -> None:
        """escolheroriginal/conteúdo derivadodeclaração + AI declaração."""
        try:
            # 1) clica "original/conteúdo derivado" botão
            declaration_btn = page.get_by_role("button", name="原创/二创")
            if await declaration_btn.count():
                await declaration_btn.click(timeout=5000)
                await page.wait_for_timeout(1000)
                hupu_logger.info(_msg("🏷️", "cliquei em original/conteúdo derivado"))
        except Exception as exc:
            hupu_logger.warning(_msg("⚠️", f"clicaoriginal/conteúdo derivadofalhou: {exc}"))

        try:
            # 2) escolher "contém conteúdo gerado por IA"
            combobox = page.get_by_role("combobox")
            if await combobox.count():
                await combobox.click(timeout=5000)
                await page.wait_for_timeout(1000)

                ai_option = page.get_by_text("含AI生成内容")
                if await ai_option.count():
                    await ai_option.click(timeout=5000)
                    await page.wait_for_timeout(500)
                    hupu_logger.info(_msg("🏷️", "escolhi a opção de conteúdo gerado por IA"))
        except Exception as exc:
            hupu_logger.warning(_msg("⚠️", f"escolher AI falha na declaração: {exc}"))

    async def _submit_publish(self, page: Page) -> None:
        """clica" confirma a publicação " e espera ir para a página do post."""
        # 录制脚本：page.get_by_label("发视频").get_by_text("确定发布").click()
        publish_btn = page.get_by_label("发视频").get_by_text("确定发布")
        await publish_btn.wait_for(state="visible", timeout=15000)
        await publish_btn.click()
        hupu_logger.info(_msg("🏃", "cliquei em confirmar a publicação"))

        # espera ir para a página do post (URL casa com bbs.hupu.com/{número}.html)
        start = time.monotonic()
        while time.monotonic() - start < 60:
            current_url = page.url
            if HUPU_POST_URL_PATTERN.search(current_url):
                hupu_logger.success(_msg("🥳", f"vídeo publicado: {current_url}"))
                return

            await page.wait_for_timeout(2000)

        # tempo esgotado - pode ter dado certo sem eu conseguir detectar
        hupu_logger.warning(_msg("⚠️", f"60 s após publicar e nada de ir para a página do post; URL atual: {page.url}"))

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
