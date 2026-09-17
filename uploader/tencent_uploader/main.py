# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import base64
import inspect
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import BASE_DIR, DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import tencent_logger

TENCENT_LOGIN_URL = "https://channels.weixin.qq.com"
TENCENT_HOME_URL = "https://channels.weixin.qq.com/platform"
TENCENT_UPLOAD_URL = "https://channels.weixin.qq.com/platform/post/create"
TENCENT_MANAGE_URL = "https://channels.weixin.qq.com/platform/post/list"
TENCENT_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
TENCENT_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _resolve_account_file(account_file: str | Path) -> str:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return str(path)

    if len(path.parts) == 1:
        return str((Path(BASE_DIR) / "cookies" / "tencent_uploader" / path).resolve())

    return str(path.resolve())


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return

    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(
    success: bool,
    status: str,
    message: str,
    account_file: str,
    qrcode: dict | None = None,
    current_url: str = "",
) -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


def _build_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {"headless": headless}
    if LOCAL_CHROME_PATH:
        launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
    else:
        launch_kwargs["channel"] = "chrome"
    return launch_kwargs


def _get_qrcode_utils():
    from utils.login_qrcode import build_login_qrcode_path
    from utils.login_qrcode import decode_qrcode_from_path
    from utils.login_qrcode import print_terminal_qrcode
    from utils.login_qrcode import remove_qrcode_file
    from utils.login_qrcode import save_data_url_image

    return {
        "build_login_qrcode_path": build_login_qrcode_path,
        "decode_qrcode_from_path": decode_qrcode_from_path,
        "print_terminal_qrcode": print_terminal_qrcode,
        "remove_qrcode_file": remove_qrcode_file,
        "save_data_url_image": save_data_url_image,
    }


def format_str_for_short_title(origin_title: str) -> str:
    allowed_special_chars = "《》"":+?%°"
    filtered_chars = [char if char.isalnum() or char in allowed_special_chars else " " if char == "," else "" for char in origin_title]
    formatted_string = "".join(filtered_chars)

    # o título curto do Canal do WeChat exige de 6 a 16 caracteres; aqui mantemos entre 7 e 15.
    formatted_string = formatted_string.strip()
    if len(formatted_string) > 15:
        formatted_string = formatted_string[:15]
    if len(formatted_string) < 7:
        # abaixo do mínimo, completa até 7; sem espaços no fim (o site corta os espaços e o tamanho continua insuficiente)
        filler = "，精彩内容分享"  # texto enviado ao próprio site: não traduzir
        formatted_string = (formatted_string + filler)[:7] if formatted_string else "精彩视频内容分享"

    return formatted_string


async def cookie_auth(account_file):
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(TENCENT_UPLOAD_URL, wait_until="domcontentloaded")

            # cookie quando expira, a página para em post/create, depois o JS do site redireciona para a página de login;
            # é preciso esperar a navegação terminarídoe então decide, senão dá alarme falso "cookie válido"
            try:
                await page.wait_for_url("**/login.html**", timeout=8000)
                tencent_logger.info(_msg("🥹", "cookie expirado (a página redirecionou para a página de login), é preciso entrar de novo"))
                return False
            except Exception:
                pass  # 8 s sem navegar, provavelmente já está conectado

            # dupla garantia: se o iframe de login do WeChat aparecer na página, também conta como expirado
            for fr in page.frames:
                if "open.weixin.qq.com/connect/qrconnect" in fr.url:
                    tencent_logger.info(_msg("🥹", "cookie expirado (a janela de login por QR code apareceu), é preciso entrar de novo"))
                    return False

            tencent_logger.success(_msg("🥳", "cookie válido"))
            return True
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"cookie erro na verificação: tratando como expirado: {exc}"))
            return False
        finally:
            await browser.close()


async def _extract_tencent_qrcode_src(page: Page) -> str:
    if hasattr(page, "frame_locator"):
        try:
            iframe_locator = page.frame_locator('[src*="login-for-iframe"]')
            qr_code_img = iframe_locator.locator('div#app img.qrcode').first
            await qr_code_img.wait_for(state="visible", timeout=8000)
            src = await qr_code_img.get_attribute("src")
            if src and src.startswith("data:image/"):
                return src
        except Exception:
            pass

    # 2026 tela de login nova: o QR code fica no iframe de open.weixin.qq.com/connect/qrconnect,
    # img.qrcode  tem src relativo(ex.: /connect/qrcode/xxxx), precisa baixar e converter para data URL
    for frame in page.frames:
        if "open.weixin.qq.com/connect/qrconnect" not in frame.url:
            continue
        try:
            qr_img = frame.locator("img.qrcode").first
            await qr_img.wait_for(state="attached", timeout=15000)
            src = None
            for _ in range(20):
                src = await qr_img.get_attribute("src")
                if src:
                    break
                await page.wait_for_timeout(500)
            if not src:
                continue
            if src.startswith("data:image/"):
                return src
            abs_url = urljoin(frame.url, src)
            resp = await page.context.request.get(abs_url)
            if resp.ok:
                body = await resp.body()
                content_type = resp.headers.get("content-type", "image/png").split(";")[0]
                return f"data:{content_type};base64,{base64.b64encode(body).decode()}"
        except Exception:
            continue

    selector_candidates = [
        "div.login-qrcode-wrap img.qrcode",
        "div.qrcode-wrap img.qrcode",
        "img.qrcode",
        'img[src^="data:image/"]',
    ]
    for selector in selector_candidates:
        qr_code_img = page.locator(selector).first
        try:
            if not await qr_code_img.count() or not await qr_code_img.is_visible():
                continue
            src = await qr_code_img.get_attribute("src")
            if src and src.startswith("data:image/"):
                return src
        except Exception:
            continue

    raise RuntimeError("não consegui pegar o endereço do QR code do Canal do WeChat")


async def _save_tencent_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_utils = _get_qrcode_utils()
    qrcode_src = await _extract_tencent_qrcode_src(page)
    qrcode_path = qrcode_utils["save_data_url_image"](
        qrcode_src,
        qrcode_utils["build_login_qrcode_path"](account_file, suffix="tencent_login_qrcode"),
    )
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if qrcode_utils["remove_qrcode_file"](previous_qrcode_path):
            tencent_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {previous_qrcode_path}"))

    tencent_logger.info(_msg("🖼️", f"QR code pronto, salvo em: {qrcode_path}"))
    qrcode_content = qrcode_utils["decode_qrcode_from_path"](qrcode_path)
    if qrcode_content:
        qrcode_utils["print_terminal_qrcode"](qrcode_content, qrcode_path, "WeChat")
    else:
        tencent_logger.warning(
            _msg(
                "😵",
                f"não consegui extrair da imagem um conteúdo que dê para desenhar no terminal; abra direto {qrcode_path} escanear o QR code",
            )
        )

    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_tencent_login_completed(page: Page) -> bool:
    publish_markers = [
        page.locator('div:has-text("发表视频")').first,
        page.locator('button:has-text("发表")').first,
        page.locator('button:has-text("保存草稿")').first,
    ]
    for marker in publish_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return True
        except Exception:
            continue

    if not (page.url.startswith(TENCENT_UPLOAD_URL) or page.url.startswith(TENCENT_MANAGE_URL)):
        return False

    login_markers = [
        page.locator("div.login-qrcode-wrap").first,
        page.locator("div.qrcode-wrap").first,
        page.locator("img.qrcode").first,
        page.locator('span:has-text("微信扫码登录 视频号助手")').first,
    ]
    for marker in login_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return False
        except Exception:
            continue

    return True


async def _is_tencent_qrcode_expired(page: Page) -> bool:
    tip_selectors = [
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for selector in tip_selectors:
        tip = page.locator(selector).first
        try:
            if await tip.count() and await tip.is_visible():
                return True
        except Exception:
            continue
    return False


async def _is_tencent_qrcode_scanned(page: Page) -> bool:
    scanned_tips = [
        'div.qr-tip div:has-text("已扫码")',
        'div.qr-tip div:has-text("需在手机上进行确认")',
    ]
    for selector in scanned_tips:
        tip = page.locator(selector).first
        try:
            if await tip.count() and await tip.is_visible():
                return True
        except Exception:
            continue
    return False


async def _refresh_tencent_qrcode(page: Page) -> None:
    visible_refresh_selectors = [
        "div.login-qrcode-wrap div.mask.show div.refresh-wrap",
        "div.login-qrcode-wrap div.mask.show .refresh-wrap",
    ]
    for selector in visible_refresh_selectors:
        refresh_wrap = page.locator(selector).first
        try:
            if not await refresh_wrap.count() or not await refresh_wrap.is_visible():
                continue
            await refresh_wrap.click()
            return
        except Exception:
            continue

    tip_selectors = [
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for selector in tip_selectors:
        tip = page.locator(selector).first
        try:
            if not await tip.count() or not await tip.is_visible():
                continue
            refresh_wrap = tip.locator("xpath=ancestor::div[contains(@class, 'refresh-wrap')]").first
            if await refresh_wrap.count():
                await refresh_wrap.click()
            else:
                await tip.click()
            return
        except Exception:
            continue

    fallback_refresh = page.locator("div.login-qrcode-wrap div.refresh-wrap").first
    if await fallback_refresh.count():
        await fallback_refresh.click()
        return

    raise RuntimeError("não achei onde clicar para atualizar o QR code do Canal do WeChat")


async def _wait_for_tencent_login(
    page: Page,
    account_file: str,
    qrcode_info: dict | None,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
) -> dict:
    qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info else None
    scanned_logged = False
    for _ in range(max_checks):
        if await _is_tencent_login_completed(page):
            tencent_logger.info(_msg("🥳", f"QR code lido: já estou na página de quem entrou: {page.url}"))
            return _build_login_result(True, "success", "Canal do WeChatlogin por QR codedeu certo", account_file, qrcode_info, page.url)

        if not scanned_logged and await _is_tencent_qrcode_scanned(page):
            tencent_logger.info(_msg("📱", "QR code lido: falta confirmar no celular"))
            scanned_logged = True

        if await _is_tencent_qrcode_expired(page):
            tencent_logger.warning(_msg("😵", "o QR code expirou; gerando outro"))
            await _refresh_tencent_qrcode(page)
            await asyncio.sleep(1)
            try:
                qrcode_info = await _save_tencent_qrcode(
                    page,
                    account_file,
                    previous_qrcode_path=qrcode_path,
                    qrcode_callback=qrcode_callback,
                )
                qrcode_path = Path(qrcode_info["image_path"])
            except Exception as exc:
                tencent_logger.warning(_msg("⚠️", f"depois de atualizar, não consegui pegar o QR code de novo({exc}), escaneie o QR code direto na janela do navegador"))

        await asyncio.sleep(poll_interval)

    return _build_login_result(False, "timeout", "tempo esgotado esperando o login por QR code do Canal do WeChat", account_file, qrcode_info, page.url)


async def tencent_cookie_gen(
    account_file,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        qrcode_path = None
        result = _build_login_result(False, "failed", "Canal do WeChatfalha no login", account_file)
        try:
            page = await context.new_page()
            await page.goto(TENCENT_LOGIN_URL)
            try:
                qrcode_info = await _save_tencent_qrcode(page, account_file, qrcode_callback=qrcode_callback)
                qrcode_path = Path(qrcode_info["image_path"])
            except Exception as exc:
                tencent_logger.warning(
                    _msg("⚠️", f"não consegui extrair a imagem do QR code({exc}), escaneie o QR code direto na janela aberta; o login segue normalmente")
                )
                qrcode_info = None
                qrcode_path = None
            tencent_logger.info(_msg("🧍", "escaneie o QR code; estou esperando o login terminar"))
            result = await _wait_for_tencent_login(
                page,
                account_file,
                qrcode_info,
                qrcode_callback=qrcode_callback,
                poll_interval=poll_interval,
                max_checks=max_checks,
            )
            if result["success"]:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                if not await cookie_auth(account_file):
                    result = _build_login_result(
                        False,
                        "cookie_invalid",
                        "Canal do WeChatescanear o QR codeo fluxo terminou, mas a validação do cookie falhou",
                        account_file,
                        qrcode_info,
                        page.url,
                    )
            return result
        except Exception as exc:
            result = _build_login_result(
                False,
                "failed",
                str(exc),
                account_file,
                current_url=page.url if "page" in locals() else "",
            )
            return result
        finally:
            qrcode_utils = _get_qrcode_utils()
            if qrcode_utils["remove_qrcode_file"](qrcode_path):
                tencent_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {qrcode_path}"))
            if not result["success"]:
                tencent_logger.error(_msg("😢", f"falha no login: {result['message']}"))
            await context.close()
            await browser.close()


async def tencent_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookiearquivo inexistente ou expirado", account_file)
            return result if return_detail else False

        tencent_logger.info(_msg("🥹", "cookie expirou: vou abrir o navegador para entrar de novo"))
        result = await tencent_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookieválido", account_file)
    return result if return_detail else True


async def get_tencent_cookie(account_file, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    return await tencent_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)


async def weixin_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    return await tencent_setup(
        account_file,
        handle=handle,
        return_detail=return_detail,
        qrcode_callback=qrcode_callback,
        headless=headless,
    )


class TencentBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        collection_name: str | None = None,
    ):
        self.publish_date = publish_date
        self.account_file = _resolve_account_file(account_file)
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.headless = headless
        self.collection_name = collection_name
        self.local_executable_path = LOCAL_CHROME_PATH

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookiearquivo inexistente; conclua antes o ídoCanal do WeChatlogin: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookiearquivo expirado; conclua antes o ídoCanal do WeChatlogin: {self.account_file}")
        if self.publish_strategy not in {TENCENT_PUBLISH_STRATEGY_IMMEDIATE, TENCENT_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"estratégia de publicação não suportada: {self.publish_strategy}")

        if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def wait_for_realtime_verification(
        self,
        page: Page,
        qr_path: str | Path | None = None,
        timeout_seconds: float = 10 * 60,
        poll_interval_seconds: float = 2,
    ) -> Path | None:
        dialog = page.locator("div.weui-desktop-dialog__wrp:visible").filter(has_text="实名验证").first
        if not await dialog.count() or not await dialog.is_visible():
            return None

        output_path = Path(qr_path) if qr_path else Path(self.account_file).with_name(
            f"{Path(self.account_file).stem}_verification_qr.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await dialog.screenshot(path=str(output_path))
        tencent_logger.warning(_msg("📱", f"um administrador precisa escanear o QR code no WeChat para concluirídoverificação de identidadeção: {output_path}"))

        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while await dialog.count() and await dialog.is_visible():
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("esperando a verificação de identidade do administrador do Canal do WeChatçãotempo esgotado")
            await asyncio.sleep(poll_interval_seconds)

        tencent_logger.success(_msg("🥳", "verificação de identidade pelo administrador concluída, continua a publicação"))
        return output_path

    async def set_schedule_time_tencent(self, page: Page, publish_date: datetime):
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()
        await page.click('input[placeholder="请选择发表时间"]')  # seletor da própria página

        current_month = publish_date.strftime("%m月")
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')
        if page_month != current_month:
            await page.click("button.weui-desktop-btn__icon__right")

        elements = await page.query_selector_all("table.weui-desktop-picker__table a")
        for element in elements:
            if "weui-desktop-picker__disabled" in await element.evaluate("el => el.className"):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        await page.click('input[placeholder="请选择时间"]')  # seletor da própria página
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(publish_date.strftime("%H"))
        await page.keyboard.press("Enter")  # confirmarhora e fecha a lista de horários
        await page.wait_for_timeout(500)
        # fecha a camada do seletor de horário: clicar direto na descriçãoa área pode ficar coberta pelo weui-desktop-dialog; daí a tolerância
        try:
            await page.locator("div.input-editor").click(timeout=5000)
        except Exception:
            await page.keyboard.press("Escape")

    async def open_upload_page(self, page: Page) -> None:
        # Canal do WeChato site mudou: abrir /platform/post/create direto joga de volta para /platform,
        # o iframe do formulário carrega só a casca (Vue não monta), a página não tem nenhum input[type=file].
        # caminho certo: entra na página inicial e clica no "publicar vídeo" botãoa navegação acontece no cliente; só então o formulário monta de verdade.
        await page.goto(TENCENT_HOME_URL, timeout=120000, wait_until="domcontentloaded")
        # cookie quando expira, o JS do site redireciona para a página de login, descobre cedo e dá um erro claro
        try:
            await page.wait_for_url("**/login.html**", timeout=8000)
            raise RuntimeError("Canal do WeChat cookie expirado (redirecionado para a página de login), entre de novo pelo QR code antes de publicar")
        except TimeoutError:
            pass  # 8 s sem navegar, normal
        except RuntimeError:
            raise
        except Exception:
            pass
        if any("open.weixin.qq.com/connect/qrconnect" in fr.url for fr in page.frames):
            raise RuntimeError("Canal do WeChat cookie expirado (redirecionado para a página de login), entre de novo pelo QR code antes de publicar")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        # 注意：get_by_text("发表视频") 会命中一个隐藏的说明 <p>（不可点）；
        # na página inicial, quem é clicável de verdade é o button.weui-desktop-btn.
        publish_entry = page.locator("button.weui-desktop-btn", has_text="发表视频").first
        try:
            await publish_entry.wait_for(state="visible", timeout=30000)
            await publish_entry.click()
        except Exception:
            # reserva: botãosem acertar o clique, volta ao caminho antigo e navega direto (ainda pode ser só a casca, mas mantém a compatibilidade)
            await page.goto(TENCENT_UPLOAD_URL, timeout=120000, wait_until="domcontentloaded")
        try:
            await page.wait_for_url("**/platform/post/create", timeout=120000)
        except Exception:
            pass

        # enviaro formulário fica no iframe micro/content/post/create, ainda vazio no domcontentloaded.
        # procura o input sem esperar a rede sossegar[type=file], dá alarme falso "não achei o campo de envio de arquivo do Canal do WeChat"——
        # no print de erro a coluna da esquerda aparece certa e o conteúdo principal em branco: não parece falta de carregamentoído.
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass  # se não der para silenciar, tudo bem: há uma nova tentativa adiante

    async def upload_video_file(self, page: Page, file_path: str) -> None:
        async def find_file_input():
            for fr in page.frames:  # frame principal + todos os iframes (Canal do WeChato editor pode estar dentro de um iframe)
                try:
                    fi = fr.locator('input[type="file"]')
                    if await fi.count():
                        return fi.first
                except Exception:
                    continue
            return None

        fi = await find_file_input()
        clicked_publish = False
        for _ in range(60):
            if fi is not None:
                break
            if not clicked_publish:
                # a versão nova do assistente do Canal do WeChat pode cair na página inicial, e "publicar vídeo" botãoaparece de forma assíncrona.
                # verifica todos os botões acessíveis; no Patchright, casar pelo nome exato nesta página é instável.
                try:
                    publish_buttons = await page.get_by_role("button").all()
                except Exception:
                    publish_buttons = []
                for candidate in publish_buttons:
                    try:
                        button_text = (await candidate.inner_text()).strip()
                        is_visible = await candidate.is_visible()
                    except Exception:
                        continue
                    if "publicar vídeo" in button_text and is_visible:
                        await candidate.click(force=True)
                        clicked_publish = True
                        break
            fi = await find_file_input()
            if fi is None:
                await asyncio.sleep(1)
        if fi is None:
            # guarda evidências: esse erro tem causas demais (sem sessão, na página inicial ou com o iframe incompleto /
            # o site mudou), só pelo texto do erro não dá para distinguir; o print mostra na hora qual é.
            try:
                shot = Path(BASE_DIR) / "debug_tencent_no_file_input.png"
                await page.screenshot(path=str(shot), full_page=True)
                tencent_logger.info(_msg(
                    "📸",
                    f"print do erro guardado {shot}; url={page.url}; "
                    f"frames={[fr.url[:80] for fr in page.frames]}",
                ))
            except Exception:
                pass
            raise RuntimeError("não achei o campo de envio de arquivo do Canal do WeChat")
        await fi.set_input_files(file_path)

    async def set_short_title(self, page: Page, title: str, short_title: str | None = None) -> None:
        # Canal do WeChat "título curto" é o "título" que a tela pede (aquela área grande de edição é na verdade o "descrição do vídeo").
        # passa pelo format_str_for_short_title para o tamanho ficar em 7~15, evita ser barrado na validação da publicação.
        value = format_str_for_short_title(short_title or title)
        # localiza primeiro pelo placeholder (verificação salva em arquivoçãomais estável), reserva: o input vizinho do antigo "título curto".
        field = page.locator('input[placeholder="填写短标题有机会获得更多流量"]').first
        if not await field.count():
            field = (
                page.get_by_text("短标题", exact=True)
                .locator("..")
                .locator("xpath=following-sibling::div")
                .locator('span input[type="text"]')
            )
        if await field.count():
            await field.fill(value)
            tencent_logger.info(_msg("🏷️", f"título curto preenchido ({len(value)} caracteres): {value}"))
        else:
            tencent_logger.info(_msg("🧾", "não achei o campo de título curto; pulando"))

    async def _dismiss_switch_account_dialog(self, page: Page) -> None:
        # Canal do WeChatenviaràs vezes aparece depois "troca o Canal do WeChat" janela(.changeAccount-dialog / .common-dialog)cobre o formulário de publicação.
        # ele traz "cancelar" botão, não é obrigatório; clica "cancelar"/ canto superior direito × / Esc pode pular: segue a publicação com a conta atualção.
        cancel = page.locator('.changeAccount-dialog button:has-text("取消")').first
        closeb = page.locator('.changeAccount-dialog .weui-desktop-dialog__close-btn').first
        for cand in (cancel, closeb):
            try:
                if await cand.count() and await cand.is_visible():
                    await cand.click(timeout=2000)
                    await page.wait_for_timeout(600)
                    return
            except Exception:
                continue
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(600)
        except Exception:
            pass

    async def fill_title_and_tags(self, page: Page) -> None:
        # enviarde vez em quando, depois "troca o Canal do WeChat" a janela cobre a descriçãocampo: se o clique não pegar, fecha a janela e tenta de novo (para conseguir clicar na descriçãoesse campo indica sucesso).
        for _ in range(4):
            try:
                await page.locator("div.input-editor").click(timeout=5000)
                break
            except Exception:
                await self._dismiss_switch_account_dialog(page)
                await page.wait_for_timeout(500)
        else:
            await page.locator("div.input-editor").click(timeout=8000)
        await page.keyboard.type(self.title)
        await page.keyboard.press("Enter")
        for tag in self.tags:
            await page.keyboard.type("#" + tag)
            await page.keyboard.press("Space")
        tencent_logger.info(_msg("🏷️", f"hashtag adicionada: {len(self.tags)}"))

    async def fill_description(self, page: Page) -> None:
        await page.keyboard.press("Enter")
        await page.keyboard.type(self.desc)
        tencent_logger.info(_msg("🏷️", f"descrição adicionada: {len(self.desc)}"))

    async def apply_collection(self, page: Page) -> None:
        """na página do formulário" adiciona à coletânea " seleciona na lista pelo nome exato da coletânea (estrutura da página: option-item > .item > .name/.desc).

        sem coletânea com esse nome, não abre nem seleciona (publica sem selecionar nada; a interface aceita vazio,
        não trava o fluxo principal).a versão antiga era "itens da lista>1escolhe o primeiro", equivalia a escolher no acaso; agora casa exatamente.
        """
        if not self.collection_name:
            return
        try:
            trigger = page.get_by_text("添加到合集").first
            if await trigger.count() == 0:
                tencent_logger.info(_msg("🧾", "não achei nesta página a entrada de adicionar à coletânea: seguindo sem agrupar"))
                return
            dropdown = trigger.locator("xpath=following-sibling::div").first
            await dropdown.click(timeout=8000)
            await page.wait_for_timeout(800)

            option = dropdown.locator(".option-list-wrap .option-item").filter(
                has=page.locator(f'.name:text-is("{self.collection_name}")')
            )
            if await option.count() == 0:
                tencent_logger.warning(
                    _msg("😵", f"a lista de coletâneas não tem '{self.collection_name}': segue sem selecionar nenhuma")
                )
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                return

            # headless a opção costuma dar "element is not visible": a lista abre fora da área visível /
            # dentro do container rolável .option-list-wrap, com janela (janela grande)fica visível e dá para clicar direto,
            # headless com a janela pequena o clique erra; rola a opção até a vista antes de clicar — o clique comum
            # quando ainda é considerado invisível → force clica (pula a checagem de visibilidade)→ dispara um clique nativo como reserva.
            target = option.first
            try:
                await target.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            try:
                await target.click(timeout=4000)
            except Exception:
                try:
                    await target.click(force=True, timeout=4000)
                except Exception:
                    await target.dispatch_event("click")
            await page.wait_for_timeout(500)
            tencent_logger.success(_msg("🥳", f"coletânea escolhida: {self.collection_name}"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"não consegui escolher a coletânea; sigo a publicação sem ela: {exc}"))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

    async def apply_original_statement(self, page: Page) -> None:
        # Canal do WeChat "marcação do vídeo" lista: neste projeto o vídeo passa por IA (TTS narração, legenda e vinheta feitas por IA), 
        # escolha conforme as regras da plataforma: "contém conteúdo gerado por IA" (ao lado de "conteúdo republicado" e outras; basta escolher, sem informar a fonte).
        # atenção: isto é diferente do de cima "declarar conteúdo original" são dois campos diferentes; aqui usamos a marcação de IA e não marcamos conteúdo original.
        # o texto abaixo é o rótulo da própria página: não traduzir
        label_text = getattr(self, "content_label", None) or "含AI生成内容"
        try:
            entry = page.get_by_text("选择视频标注", exact=True).first
            if not await entry.count():
                tencent_logger.info(_msg("🧾", "não achei nesta página a entrada de marcação do vídeo: pulando a marcação e continuando a publicação"))
                return
            await entry.click()
            await page.wait_for_timeout(800)
            option = page.get_by_text(label_text, exact=True).first
            await option.wait_for(state="visible", timeout=5000)
            await option.click()
            await page.wait_for_timeout(500)
            tencent_logger.success(_msg("🏷️", f"marcação do vídeo escolhida: {label_text}"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"não consegui definir a marcação do vídeo '{label_text}'; pulando e continuando a publicação: {exc}"))

    async def wait_for_upload_complete(
        self, page: Page, timeout_seconds: int = 3600, max_retries: int = 3
    ) -> None:
        """espera o envio terminarído.

        **precisa terminar, e o número de tentativas precisa ter limite.** antes era um while True sem saída: qualquer erro no envio
        apagava e reenviava sem parar, escrevendo uma linha a cada 2 s " enviando o vídeo..."——
        esse log é idêntico ao de um envio real: de fora não dá para diferenciar.

        medido na prática (2026-08-11, 172MB / upload ~0.5Mbps): dava erro por volta dos 4 minutos e recomeçava,
        ficava quase 2 horas em laço sem parar nem encerrar o processo; o usuário só via "enviando o vídeo",
        na verdade é o mesmo vídeofoi reenviado mais de 20 vezes.

        por padrão 1 hora e 3 tentativas: em rede lenta um arquivo grande demora mesmo, e o limite precisa caber;
        mas no limite de tempo ou de tentativas, erra de forma clara com print, em vez de seguir em silêncio.
        """
        deadline = time.monotonic() + timeout_seconds
        last_report = 0.0
        retries = 0
        while True:
            if time.monotonic() > deadline:
                try:
                    shot = Path(BASE_DIR) / "debug_tencent_upload_timeout.png"
                    await page.screenshot(path=str(shot), full_page=True)
                    tencent_logger.error(_msg("📸", f"tempo esgotado no envioprint guardado {shot}"))
                except Exception:
                    pass
                raise RuntimeError(
                    f"o envio ao Canal do WeChat passou de {timeout_seconds} s e não terminou (o botão de publicar continua indisponível)"
                )
            try:
                publish_button = page.locator('div.form-btns button:has-text("发表"):visible').first
                if await publish_button.count():
                    button_class = await publish_button.get_attribute("class")
                    if (
                        not await publish_button.is_disabled()
                        and (not button_class or "weui-desktop-btn_disabled" not in button_class)
                    ):
                        tencent_logger.info(_msg("🥳", "envio do vídeo concluído"))
                        break

                # repetir a mesma linha a cada 2 s não informa nada e só entope o log (no teste, 1600 linhas em 50 minutos).
                # 30 uma linha por segundo, dizendo há quanto tempo espera —"quanto falta" é a única informação útil aqui.
                now = time.monotonic()
                if now - last_report >= 30:
                    waited = int(timeout_seconds - (deadline - now))
                    tencent_logger.info(_msg("🏃", f"enviando o vídeo... (esperando há {waited} s)"))
                    last_report = now
                await asyncio.sleep(2)

                upload_failed = await page.locator("div.status-msg.error").count()
                delete_button = await page.locator('div.media-status-content div.tag-inner:has-text("删除")').count()
                if upload_failed and delete_button:
                    retries += 1
                    if retries > max_retries:
                        try:
                            shot = Path(BASE_DIR) / "debug_tencent_upload_failed.png"
                            await page.screenshot(path=str(shot), full_page=True)
                            tencent_logger.error(_msg("📸", f"enviarfalhou várias vezes; print guardado {shot}"))
                        except Exception:
                            pass
                        raise RuntimeError(
                            f"Canal do WeChatenviarfalhas seguidas {max_retries} ª tentativa; parando por aqui"
                            " (causas comuns: arquivo grande demais, upload lento que estoura o tempo do site, ou proxy/VPN no caminho)"
                        )
                    tencent_logger.error(_msg("😵", f"o envio deu erro; tentando de novo ({retries}/{max_retries})"))
                    await self.handle_upload_error(page)
            except RuntimeError:
                raise
            except Exception:
                await asyncio.sleep(2)

    async def submit_publish(self, page: Page) -> None:
        is_draft = getattr(self, "is_draft", False)
        # espera e limpa camadas e janelas antes,espera o botão de publicarapareceu
        for wait_round in range(60):
            await self._dismiss_switch_account_dialog(page)
            try:
                await page.evaluate("""() => document.querySelectorAll('.mask, .changeAccount-dialog, .common-dialog').forEach(e => e.remove())""")
            except Exception:
                pass
            publish_btn = page.get_by_role("button", name="发表", exact=True).first if not is_draft else page.get_by_role("button", name="保存草稿").first
            try:
                if await publish_btn.count() and await publish_btn.is_visible():
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        else:
            tencent_logger.warning(_msg("😵", "60s não achei o botão visível de publicar ou salvar rascunhoão, tenta continuar à força"))
        # clica em publicar ou rascunho
        for attempt in range(20):
            try:
                if await publish_btn.count():
                    try:
                        await publish_btn.click(timeout=4000)
                    except Exception:
                        await publish_btn.evaluate("el => el.click()")
                if is_draft:
                    await page.wait_for_url("**/post/list**", timeout=5000)
                    tencent_logger.success(_msg("🥳", "rascunho do vídeo salvo"))
                else:
                    # publicado, o Canal do WeChat pode ir para /platform (página inicial), /post/list ou fica na página create, mas o botãosumiu.
                    # decisão combinada: a URL sai de /post/create ou o botão de publicarnão existe mais.
                    for _ in range(10):
                        await asyncio.sleep(1)
                        cur = page.url
                        if "/post/create" not in cur:
                            tencent_logger.success(_msg("🥳", "vídeo publicado"))
                            return
                        if not await publish_btn.count():
                            tencent_logger.success(_msg("🥳", "vídeo publicado (botãosumiu)"))
                            return
                    raise Exception("10 s depois de publicar e a página não mudou")
                return
            except Exception as exc:
                current_url = page.url
                if is_draft and ("post/list" in current_url or "draft" in current_url):
                    tencent_logger.success(_msg("🥳", "rascunho do vídeo salvo"))
                    return
                if (not is_draft) and "/post/create" not in current_url:
                    tencent_logger.success(_msg("🥳", "vídeo publicado"))
                    return
                if attempt and attempt % 5 == 0:
                    tencent_logger.warning(_msg("😵", f"a publicação ainda não terminou (tentativa {attempt}); erro: {str(exc)[:60]}"))
                tencent_logger.info(_msg("🏃", "publicando o vídeo..."))
                await asyncio.sleep(1)
        raise RuntimeError("a publicação não terminou no tempo esperadoído, confira a página de publicação")


class TencentVideo(TencentBaseUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        category=None,
        is_draft=False,
        desc: str | None = None,
        thumbnail_path: str | None = None,
        thumbnail_landscape_path: str | None = None,
        thumbnail_portrait_path: str | None = None,
        short_title: str | None = None,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        collection_name: str | None = None,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
            collection_name=collection_name,
        )
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.category = category
        self.is_draft = is_draft
        self.desc = desc or ""
        self.thumbnail_path = thumbnail_path
        self.thumbnail_landscape_path = thumbnail_landscape_path
        self.thumbnail_portrait_path = thumbnail_portrait_path or thumbnail_path
        self.short_title = short_title

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("no modo vídeo, o título é obrigatório")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_landscape_path:
            self.thumbnail_landscape_path = str(self.validate_image_file(self.thumbnail_landscape_path))
        if self.thumbnail_portrait_path:
            self.thumbnail_portrait_path = str(self.validate_image_file(self.thumbnail_portrait_path))

    async def handle_upload_error(self, page: Page) -> None:
        tencent_logger.info(_msg("😵", "vídeodeu erro; enviando de novo"))
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role("button", name="删除", exact=True).click()
        await self.upload_video_file(page, self.file_path)

    async def open_thumbnail_dialog(self, page: Page, selectors: list[str], dialog_titles: list[str]):
        for selector in selectors:
            cover_entry = page.locator(selector).first
            try:
                if not await cover_entry.count():
                    continue
                await cover_entry.wait_for(state="visible", timeout=3000)
                await cover_entry.click()
                await page.wait_for_timeout(500)
                break
            except Exception:
                continue

        for title in dialog_titles:
            cover_dialog = page.locator("div.weui-desktop-dialog").filter(has_text=title).first
            if await cover_dialog.count():
                return cover_dialog
        return None

    async def confirm_thumbnail_crop(self, page: Page) -> None:
        crop_dialog = page.locator("div.weui-desktop-dialog").filter(has_text="裁剪封面图").first
        if not await crop_dialog.count():
            return

        try:
            await crop_dialog.wait_for(state="visible", timeout=10000)
            crop_confirm_button = crop_dialog.locator(
                'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确定")'
            ).first
            if await crop_confirm_button.count():
                await crop_confirm_button.wait_for(state="visible", timeout=5000)
                await crop_confirm_button.click()
                await page.wait_for_timeout(1000)
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"erro ao confirmar o corte da capa; tentando salvar pela janela principal: {exc}"))

    async def upload_thumbnail_in_dialog(self, page: Page, cover_dialog, thumbnail_path: str) -> None:
        await cover_dialog.wait_for(state="visible", timeout=5000)
        file_input = cover_dialog.locator('.single-cover-uploader-wrap input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(thumbnail_path)
        await page.wait_for_timeout(2000)

        confirm_button = cover_dialog.locator(
            'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确认")'
        ).first
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()

    async def set_single_thumbnail(
        self,
        page: Page,
        thumbnail_path: str,
        selectors: list[str],
        dialog_titles: list[str],
        label: str,
    ) -> None:
        cover_dialog = await self.open_thumbnail_dialog(page, selectors, dialog_titles)
        if not cover_dialog:
            tencent_logger.info(_msg("🧍", f"não apareceu nesta página{label}janela de edição da capa: pulando"))
            return

        try:
            await self.upload_thumbnail_in_dialog(page, cover_dialog, thumbnail_path)
            tencent_logger.success(_msg("🥳", f"{label}capa definida"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"{label}não consegui definir a capa; pulando desta vez: {exc}"))

    async def set_thumbnail(self, page: Page) -> None:
        if not self.thumbnail_landscape_path and not self.thumbnail_portrait_path:
            return

        tencent_logger.info(_msg("🖼️", "definindo a capa"))

        landscape_selectors = [
            'div.horizontal-cover-wrap:has-text("4:3")',
            'div[class*="cover-wrap"]:has-text("4:3"):has-text("动态")',
            'div:has-text("视频号动态"):has-text("4:3")',
            'div:has-text("横版封面"):has-text("4:3")',
        ]
        portrait_selectors = [
            'div.vertical-cover-wrap:has-text("个人主页卡片"):has-text("3:4")',
            'div.vertical-cover-wrap:has-text("3:4")',
            'div.vertical-cover-wrap:has-text("个人主页卡片")',
        ]

        if self.thumbnail_landscape_path:
            await self.set_single_thumbnail(
                page,
                self.thumbnail_landscape_path,
                landscape_selectors,
                ["编辑视频号动态封面", "编辑动态封面", "编辑封面"],  # títulos das janelas na própria página
                "4:3 horizontal",
            )
        if self.thumbnail_portrait_path:
            await self.set_single_thumbnail(
                page,
                self.thumbnail_portrait_path,
                portrait_selectors,
                ["编辑个人主页卡片", "编辑封面"],  # títulos das janelas na própria página
                "3:4 vertical",
            )

    async def prepare_video_for_publish(self, page: Page) -> None:
        await self.wait_for_realtime_verification(page)
        await self.fill_title_and_tags(page)
        await self.fill_description(page)
        # a coletânea não é escolhida aqui: neste ponto o vídeo ainda enviando; envio concluídodepois o formulário recarrega,
        # enviandoa coletânea escolhida é perdida ou não fica vinculada ("o log dizia que escolheu, mas o site não aplicou" causa raiz).
        # passou a ser escolhido depois do wait_for_upload_complete; veja upload().

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "conferindo o cookie e o arquivo do vídeo e horário de publicação"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "verificação antes do envio concluída"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"enviando o vídeo: {self.title}"))

            await self.upload_video_file(page, self.file_path)
            await self.prepare_video_for_publish(page)
            await self.wait_for_upload_complete(page)
            # envio concluído, escolhe a coletânea depois que o formulário estabiliza (senão o que foi escolhido durante o envio é perdido)
            await self.apply_collection(page)
            await self.apply_original_statement(page)
            await self.set_thumbnail(page)

            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)

            await self.set_short_title(page, self.title, self.short_title)
            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            tencent_logger.success(_msg("🥳", "cookie atualização concluída"))
        finally:
            await context.close()
            await browser.close()

    async def tencent_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_video()


class TencentNote(TencentBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        is_draft: bool = False,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
        )
        self.image_paths = image_paths
        self.note = note or ""
        self.title = title or (self.note[:30] if self.note else "")
        self.tags = tags or []
        self.is_draft = is_draft

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("no modo imagem e texto, o título é obrigatório")
        if not self.image_paths:
            raise ValueError("no modo imagem e texto, as imagens são obrigatórias")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def switch_to_note_mode(self, page: Page) -> None:
        raise NotImplementedError("implemente em TencentNote.switch_to_note_mode a troca para o modo de imagem e texto do Canal do WeChat")

    async def upload_note_images(self, page: Page) -> None:
        raise NotImplementedError("implemente em TencentNote.upload_note_images o envio das imagens do post do Canal do WeChat")

    async def fill_note_title_and_tags(self, page: Page) -> None:
        raise NotImplementedError("implemente em TencentNote.fill_note_title_and_tags o preenchimento de título e hashtags do post do Canal do WeChat")

    async def fill_note_body(self, page: Page) -> None:
        return None

    async def prepare_note_for_publish(self, page: Page) -> None:
        await self.fill_note_title_and_tags(page)
        await self.fill_note_body(page)
        await self.apply_collection(page)
        await self.apply_original_statement(page)

    async def upload_note_content(self, page: Page) -> None:
        await self.switch_to_note_mode(page)
        await self.upload_note_images(page)
        await self.prepare_note_for_publish(page)

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "conferindo cookie, imagens e horário de publicação"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "verificação antes do envio do post concluída"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)
        context = await set_init_script(context)

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"enviando o post de imagem e texto, com {len(self.image_paths)}  imagens"))

            await self.upload_note_content(page)

            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)

            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            tencent_logger.success(_msg("🥳", "cookie atualização concluída"))
        finally:
            await context.close()
            await browser.close()

    async def tencent_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_note()
