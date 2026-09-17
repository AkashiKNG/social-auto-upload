# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
import os
from datetime import datetime
from pathlib import Path

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file
from utils.login_qrcode import save_data_url_image
from utils.log import kuaishou_logger

KUAISHOU_UPLOAD_URL = "https://cp.kuaishou.com/article/publish/video"
KUAISHOU_MANAGE_URL = "https://cp.kuaishou.com/article/manage/video?status=2&from=publish"
KUAISHOU_LOGIN_URL = "https://passport.kuaishou.com/pc/account/login/?sid=kuaishou.web.cp.api&callback=https%3A%2F%2Fcp.kuaishou.com%2Frest%2Finfra%2Fsts%3FfollowUrl%3Dhttps%253A%252F%252Fcp.kuaishou.com%252Farticle%252Fpublish%252Fvideo%26setRootDomain%3Dtrue"
KUAISHOU_UPLOAD_URL_PATTERN = "**/article/publish/video**"
KUAISHOU_MANAGE_URL_PATTERN = "**/article/manage/video?status=2&from=publish**"
KUAISHOU_COOKIE_INVALID_SELECTOR = "div.names div.container div.name:text('机构服务')"
KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
KUAISHOU_PUBLISH_STRATEGY_SCHEDULED = "scheduled"
KUAISHOU_UPLOAD_TIMEOUT_SECONDS = 480
KUAISHOU_PUBLISH_ATTEMPTS = 3


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


async def _dump_page_debug(page, tag: str) -> str:
    """quando dá erro, guarda um print da página inteira + o HTML atual, e devolve a pasta onde salvou, para comparar com o DOM novo e corrigir os seletores."""
    import time
    base = Path("ks_debug")
    base.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    try:
        await page.screenshot(path=str(base / f"{tag}_{ts}.png"), full_page=True)
    except Exception:
        pass
    try:
        (base / f"{tag}_{ts}.html").write_text(await page.content(), encoding="utf-8")
    except Exception:
        pass
    return str(base.resolve())


async def _focus_desc_editor(page) -> None:
    """acha e foca, na página de publicação do Kuaishou, o" descrição " área de edição.

    o DOM do painel do Kuaishou muda de tempos em tempos; o antigo
        get_by_text("描述").locator("xpath=following-sibling::div")
    qualquer mudança na estrutura faria esperar 30 s à toa; aqui tentamos várias estratégias em sequência (ambos ancorados em "descrição"
    etiquetaspor perto, para não clicar no campo de título por engano), cada tentativa tem um tempo curto; falhando todas, guarda print e HTML
    para investigar e lançar um erro claro em vez de simplesmente estourar o tempo.
    """
    label = page.get_by_text("描述")  # 默认子串匹配，"作品descrição " 等也能命中
    strategies = [
        # estrutura antiga:"descrição" div vizinha
        lambda: label.locator("xpath=following-sibling::div"),
        # nova descriçãoa área costuma ser o campo de texto rico logo em seguida
        lambda: label.locator("xpath=following::div[@contenteditable='true'][1]"),
        # a área editável do mesmo container
        lambda: label.locator("xpath=ancestor::*[1]//div[@contenteditable='true'][1]"),
        # reserva: o primeiro elemento editável depois dele
        lambda: label.locator("xpath=following::*[@contenteditable='true'][1]"),
    ]
    last_err = None
    for i, make in enumerate(strategies):
        try:
            loc = make().first
            await loc.wait_for(state="visible", timeout=8000)
            await loc.click(force=True)
            if i > 0:
                kuaishou_logger.warning(_msg(
                    "⚠️", f"descriçãoárea: usando a estratégia reserva#{i}localizado (o Kuaishou pode ter mudado o site; vale conferir os seletores)"))
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
    dbg = await _dump_page_debug(page, "desc_not_found")
    raise RuntimeError(
        f"não achei a área de edição da descrição no Kuaishou (a página de publicação parece ter mudado). Print e HTML salvos em {dbg}, "
        f"atualize os seletores a partir disso. Último erro: {last_err}")


async def _click_visible_publish_confirm(page: Page) -> bool:
    """Confirm an already-open Ant Design publish dialog before touching the page behind it."""
    modal = page.locator("div.ant-modal-confirm-centered:visible").first
    if not await modal.count():
        return False

    primary_button = modal.locator("button.ant-btn-primary:visible").first
    if not await primary_button.count():
        raise RuntimeError("a janela de confirmação do Kuaishou apareceu, mas não achei o botão principal clicávelão")

    await primary_button.click(timeout=8000)
    return True


def _print_ks_qrcode(qrcode_content: str, qrcode_path: Path) -> None:
    try:
        print_terminal_qrcode(qrcode_content, qrcode_path, "aplicativo do Kuaishou", compact=False, border=2)
    except TypeError as exc:
        if "unexpected keyword argument 'compact'" not in str(exc):
            raise
        kuaishou_logger.warning(_msg("😵", "achei a função antiga de desenhar QR code; voltando ao modo compatível para seguir o login"))
        print_terminal_qrcode(qrcode_content, qrcode_path, "aplicativo do Kuaishou")


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


async def _is_ks_cookie_invalid(page: Page, timeout: int = 5000) -> bool:
    try:
        await page.wait_for_selector(KUAISHOU_COOKIE_INVALID_SELECTOR, timeout=timeout)
        return True
    except Exception:
        return False


async def _extract_ks_qrcode_src(page: Page) -> str:
    login_form = page.locator("main#login-form").first
    await login_form.wait_for(state="visible", timeout=30000)

    qrcode_img = login_form.locator('div.qr-login img[alt="qrcode"]').first
    try:
        if not await qrcode_img.count() or not await qrcode_img.is_visible():
            platform_switch = login_form.locator("div.platform-switch").first
            await platform_switch.wait_for(state="visible", timeout=10000)
            await platform_switch.click()
            await asyncio.sleep(1)
    except Exception:
        platform_switch = login_form.locator("div.platform-switch").first
        await platform_switch.wait_for(state="visible", timeout=10000)
        await platform_switch.click()
        await asyncio.sleep(1)

    await qrcode_img.wait_for(state="visible", timeout=15000)

    qrcode_src = await qrcode_img.get_attribute("src")
    if not qrcode_src:
        raise RuntimeError("não consegui pegar o endereço do QR code do Kuaishou")

    return qrcode_src


async def _save_ks_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_src = await _extract_ks_qrcode_src(page)
    qrcode_path = save_data_url_image(qrcode_src, build_login_qrcode_path(account_file, suffix="ks_login_qrcode"))

    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            kuaishou_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {previous_qrcode_path}"))

    kuaishou_logger.info(_msg("🖼️", f"QR code pronto, salvo em: {qrcode_path}"))
    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if qrcode_content:
        _print_ks_qrcode(qrcode_content, qrcode_path)
    else:
        kuaishou_logger.warning(_msg("😵", f"o terminal não mostra o QR code inteiro; abra {qrcode_path} escanear o QR code"))

    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_ks_qrcode_expired(page: Page) -> bool:
    expired_box = page.locator("div.qrcode-status.qrcode-status-timeout").first
    try:
        if not await expired_box.count():
            return False
        return await expired_box.is_visible()
    except Exception:
        return False


async def _is_ks_login_page_gone(page: Page) -> bool:
    try:
        login_form = page.locator("main#login-form").first
        if not await login_form.count():
            return True
        return not await login_form.is_visible()
    except Exception:
        return True


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        if LOCAL_CHROME_PATH:
            browser = await playwright.chromium.launch(headless=True, executable_path=LOCAL_CHROME_PATH)
        else:
            browser = await playwright.chromium.launch(headless=True, channel="chromium")
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(KUAISHOU_UPLOAD_URL)
            await page.wait_for_timeout(3000)

            # vê se foi redirecionado para a tela de login
            if "passport.kuaishou.com" in page.url:
                kuaishou_logger.info(_msg("🥹", "cookie expirado (foi para a tela de login)"))
                return False

            # vê se continua na página de apresentação (aparece para quem não entrou "entrar agora" botão)
            login_btn = page.get_by_text("立即登录")
            if await login_btn.count() > 0:
                kuaishou_logger.info(_msg("🥹", "cookie expirado (página de apresentação)"))
                return False

            # prova direta: o botão de enviarãoexiste = realmente conectado
            try:
                upload_btn = page.locator("button[class^='_upload-btn']")
                await upload_btn.wait_for(state="visible", timeout=10000)
                kuaishou_logger.success(_msg("🥳", "cookie válido"))
                return True
            except Exception:
                # reserva: detecção antiga ("serviços institucionais" elemento que aparece na página de apresentação de quem não entrou)
                if await _is_ks_cookie_invalid(page):
                    kuaishou_logger.info(_msg("🥹", "cookie expirado (página de serviços institucionais)"))
                    return False
                # nada bateu: por segurança, trata como expirado para evitar falso positivo
                kuaishou_logger.warning(_msg("😵", "não dá para confirmar se o cookie é válido, tratando como expirado"))
                return False
        except Exception as exc:
            kuaishou_logger.warning(_msg("😵", f"cookie erro na verificação: tratando como expirado: {exc}"))
            return False
        finally:
            await browser.close()


async def ks_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS, cdp_url: str | None = None):
    account_file = get_absolute_path(account_file, "ks_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookiearquivo inexistente ou expirado", account_file)
            return result if return_detail else False
        kuaishou_logger.info(_msg("🥹", "cookie expirou: entrando de novo no painel do Kuaishou"))
        result = await get_ks_cookie(account_file, qrcode_callback=qrcode_callback, headless=headless, cdp_url=cdp_url)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookieválido", account_file)
    return result if return_detail else True


async def get_ks_cookie(
    account_file,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
    poll_interval: int = 3,
    max_checks: int = 100,
    cdp_url: str | None = None,
):
    if headless:
        kuaishou_logger.info(_msg("🖼️", "o login do Kuaishou roda sem janela: o QR code sai no terminal e também é salvo como imagem"))

    async with async_playwright() as playwright:
        if cdp_url:
            browser = await playwright.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            should_close_context = False
        else:
            if LOCAL_CHROME_PATH:
                browser = await playwright.chromium.launch(headless=headless, executable_path=LOCAL_CHROME_PATH)
            else:
                browser = await playwright.chromium.launch(headless=headless, channel="chromium")
            context = await browser.new_context()
            should_close_context = True
        context = await set_init_script(context)
        qrcode_path = None
        qrcode_info = None
        result = _build_login_result(False, "failed", "falha no login do Kuaishou", account_file)
        try:
            page = await context.new_page()
            await page.goto(KUAISHOU_LOGIN_URL)
            kuaishou_logger.info(_msg("🧍", "entre no Kuaishou pelo QR code na janela aberta; estou esperando"))

            qrcode_info = await _save_ks_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])

            for _ in range(max_checks):
                if page.url.startswith(KUAISHOU_UPLOAD_URL) or await _is_ks_login_page_gone(page):
                    await context.storage_state(path=account_file)
                    if await cookie_auth(account_file):
                        kuaishou_logger.success(_msg("🥳", "login por QR code do Kuaishou concluído"))
                        result = _build_login_result(True, "success", "login por QR code do Kuaishou concluído", account_file, qrcode_info, page.url)
                    else:
                        kuaishou_logger.error(_msg("😢", "leitura do QR code do Kuaishou concluídaído, mas a validação do cookie falhou"))
                        result = _build_login_result(
                            False,
                            "cookie_invalid",
                            "o fluxo do QR code do Kuaishou terminou, mas a validação do cookie falhou",
                            account_file,
                            qrcode_info,
                            page.url,
                        )
                    return result

                if qrcode_info and await _is_ks_qrcode_expired(page):
                    kuaishou_logger.warning(_msg("😵", "o QR code expirou; gerando outro"))
                    refresh_button = page.locator("p.qrcode-refresh").first
                    if await refresh_button.count():
                        await refresh_button.click()
                        await asyncio.sleep(1)
                    qrcode_info = await _save_ks_qrcode(
                        page,
                        account_file,
                        qrcode_path,
                        qrcode_callback=qrcode_callback,
                    )
                    qrcode_path = Path(qrcode_info["image_path"])

                await asyncio.sleep(poll_interval)

            result = _build_login_result(
                False,
                "timeout",
                "tempo esgotado esperando o login por QR code do Kuaishou",
                account_file,
                qrcode_info,
                page.url,
            )
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                kuaishou_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {qrcode_path}"))
            if not result["success"]:
                kuaishou_logger.error(_msg("😢", f"falha no login: {result['message']}"))
            if should_close_context:
                await context.close()
            await browser.close()

    return result


class KSBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str | None = None,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.publish_date = publish_date
        self.account_file = str(account_file)
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH
        self.date_format = "%Y-%m-%d %H:%M"

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookiearquivo inexistente; conclua antes o ídologin do Kuaishou: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookiearquivo expirado; conclua antes o ídologin do Kuaishou: {self.account_file}")

        if self.publish_strategy is None:
            self.publish_strategy = (
                KUAISHOU_PUBLISH_STRATEGY_SCHEDULED
                if self.publish_date != 0
                else KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE
            )

        if self.publish_strategy not in {
            KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE,
            KUAISHOU_PUBLISH_STRATEGY_SCHEDULED,
        }:
            raise ValueError(f"estratégia de publicação não suportada: {self.publish_strategy}")

        if self.publish_strategy == KUAISHOU_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def set_schedule_time(self, page: Page, publish_date: datetime):
        kuaishou_logger.info(_msg("🕒", "definindo o horário da publicação agendada"))
        publish_date_str = publish_date.strftime("%Y-%m-%d %H:%M:%S")

        # 1. muda para "publicação agendada" radio (casar pelo texto é mais estável)
        await page.locator('label.ant-radio-wrapper').filter(has_text="定时发布").click()
        await asyncio.sleep(2)

        # 2. clica picker abre a lista
        await page.locator('input[placeholder="选择日期时间"]').click()
        await asyncio.sleep(1)

        # 3. define o value do input de um jeito que o React aceita
        #    (ant-design DatePicker é um componente controlado, precisa do setter nativo + bubbling event)
        js_code = """
        (newValue) => {
            // o placeholder em chinês é o da própria página: não traduzir
            const input = document.querySelector('input[placeholder="选择日期时间"]');
            if (!input) return false;
            const nativeSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeSetter.call(input, newValue);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }
        """
        ok = await page.evaluate(js_code, publish_date_str)
        if not ok:
            kuaishou_logger.error("❌ não achei o campo do seletor de horário")
            return

        await asyncio.sleep(1)
        # 4. confirma com Enter
        await page.keyboard.press("Enter")
        await asyncio.sleep(2)
        kuaishou_logger.info(f"✅ publicação agendada para {publish_date_str}")

    async def close_guide_overlay(self, page: Page) -> bool:
        """fecha a camada do tour Joyride do painel do Kuaishou.

        Joyride há dois elementos importantes:
        1. tooltip (alertdialog) — caixa do tour, com botão de fecharão
        2. spotlight (react-joyride__spotlight) — camada de destaque, que engole os cliques
        as duas podem aparecer sozinhas; é preciso fechar ambas para usar a página.
        """
        closed = False

        # jeito 1: clica no botão de fechar/pular do tooltipão
        joyride_tooltip = page.locator('div[id^="react-joyride-step"] div[role="alertdialog"]')
        if await joyride_tooltip.count() > 0 and await joyride_tooltip.first.is_visible():
            print("camada do tour Joyride encontrada; fechando...")
            # tenta vários botões de fecharão selector
            close_selectors = [
                '[aria-label="Skip"], [data-action="skip"], button[title="Skip"]',
                'button:text("跳过")',
                'button:text("我知道了")',
                'button:text("关闭")',
                'button:text("下一步")',  # às vezes é preciso pular vários passos
            ]
            for sel in close_selectors:
                btn = page.locator('div[role="alertdialog"]').locator(sel)
                if await btn.count() > 0:
                    await btn.first.click(force=True)
                    await asyncio.sleep(0.5)
                    break
            closed = True

        # jeito 2: remove o portal do Joyride (reserva, para o destaque não bloquear mais)
        joyride_portal = page.locator('div#react-joyride-portal')
        if await joyride_portal.count() > 0:
            try:
                await page.evaluate("document.getElementById('react-joyride-portal')?.remove()")
                print("✅ camada do portal do Joyride removida")
                closed = True
            except Exception:
                pass

        # jeito 3: remove o elemento de destaque
        spotlight = page.locator('div.react-joyride__spotlight')
        if await spotlight.count() > 0:
            try:
                await page.evaluate("document.querySelectorAll('.react-joyride__spotlight').forEach(e => e.remove())")
                print("✅ destaque do Joyride removido")
                closed = True
            except Exception:
                pass

        if not closed:
            print("nenhuma camada do Joyride; seguindo")
        else:
            await asyncio.sleep(0.5)


class KSVideo(KSBaseUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str | None = None,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        thumbnail_path=None,
        desc: str | None = None,
        collection_name: str | None = None,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
        )
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.thumbnail_path = thumbnail_path
        self.desc = desc or ""
        self.collection_name = collection_name

    async def apply_collection(self, page: Page) -> None:
        """escolhe no formulário de publicação" entra na coletânea " lista suspensa (Ant Design Select, label atributo=nome da coletânea).

        usa o texto do label como âncora "entra na coletânea" acha exatamente o ant-select vizinho, para não pegar outro da página
        outras listas (tipo de serviço, assunto em alta, declaração do autor, local: a mesma página tem vários ant-select).
        sem uma coletânea com esse nome, fecha a lista com Escape e publica sem selecionar nenhuma (a interface aceita vazio,
        não trava o fluxo principal de publicação).
        """
        if not self.collection_name:
            return
        try:
            trigger = page.locator(
                'label:text-is("加入合集")'
            ).locator("xpath=following-sibling::div[contains(@class,'ant-select')]").first
            if await trigger.count() == 0:
                kuaishou_logger.warning(_msg("😵", "não encontrado\"entra na coletânea\"lista suspensa: seguindo sem agrupar"))
                return
            await trigger.locator(".ant-select-selector").click(timeout=8000)
            await page.wait_for_timeout(800)

            option = page.locator(f'div.ant-select-item-option[label="{self.collection_name}"]')
            if await option.count() == 0:
                kuaishou_logger.warning(
                    _msg("😵", f"a lista de coletâneas não tem '{self.collection_name}': segue sem selecionar nenhuma")
                )
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                return

            await option.first.click(timeout=8000)
            await page.wait_for_timeout(500)
            kuaishou_logger.success(_msg("🥳", f"coletânea escolhida: {self.collection_name}"))
        except Exception as exc:
            kuaishou_logger.warning(_msg("😵", f"não consegui escolher a coletânea; sigo a publicação sem ela: {exc}"))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("Kuaishou envio de vídeo, o título é obrigatório")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_path:
            self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def handle_upload_error(self, page: Page):
        kuaishou_logger.warning(_msg("😵", "o envio do vídeo tropeçou; tentando de novo"))
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def set_thumbnail(self, page: Page):
        if not self.thumbnail_path:
            return

        kuaishou_logger.info(_msg("🖼️", "definindo a capa"))

        cover_label = page.locator("span").filter(has_text="封面设置")
        await cover_label.wait_for(state="visible", timeout=30000)
        await cover_label.locator("xpath=../following-sibling::div[1]").locator('div').nth(0).click()

        modal = page.locator('div[role="document"].ant-modal')
        await modal.wait_for(state="visible", timeout=30000)

        upload_cover_tab = modal.get_by_text("上传封面", exact=True)
        await upload_cover_tab.wait_for(state="visible", timeout=10000)
        await upload_cover_tab.click()

        file_input = modal.locator('input[type="file"]')
        await file_input.wait_for(state="attached", timeout=30000)
        await file_input.set_input_files(self.thumbnail_path)
        await asyncio.sleep(1)

        confirm_button = modal.get_by_role("button", name="确认", exact=True)
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()

        await modal.wait_for(state="hidden", timeout=30000)
        kuaishou_logger.success(_msg("🥳", "capa definida"))

    async def upload(self, playwright: Playwright) -> None:
        kuaishou_logger.info(_msg("🧍", "conferindo cookie, arquivo de vídeo, capa e horário de publicação"))
        await self.validate_upload_args()
        kuaishou_logger.info(_msg("🥳", "verificação antes do envio concluída"))

        if self.local_executable_path:
            browser = await playwright.chromium.launch(
                headless=self.headless,
                executable_path=self.local_executable_path,
            )
        else:
            browser = await playwright.chromium.launch(
                headless=self.headless,
                channel="chromium",
            )
        context = await browser.new_context(storage_state=self.account_file)
        context = await set_init_script(context)

        upload_success = False
        try:
            page = await context.new_page()
            await page.goto(KUAISHOU_UPLOAD_URL)
            kuaishou_logger.info(_msg("🏃", f"enviando o vídeo: {self.title}.mp4"))
            kuaishou_logger.info(_msg("🧭", "indo para a página de envio do Kuaishou"))
            await page.wait_for_url(KUAISHOU_UPLOAD_URL_PATTERN)

            upload_button = page.locator("button[class^='_upload-btn']")
            await upload_button.wait_for(state="visible", timeout=10000)

            async with page.expect_file_chooser() as fc_info:
                await upload_button.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(self.file_path)

            await asyncio.sleep(2)

            know_button = page.locator('button[type="button"] span:text("我知道了")').first
            try:
                if await know_button.count() and await know_button.is_visible():
                    await know_button.click()
            except Exception:
                pass

            await self.close_guide_overlay(page)

            kuaishou_logger.info(_msg("✍️", "preenchendo a descrição e hashtags"))
            # confere e fecha o Joyride de novo (pode aparecer só depois do envio do arquivo)
            await self.close_guide_overlay(page)
            await _focus_desc_editor(page)
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(self.desc or self.title)
            await page.keyboard.press("Enter")

            for index, tag in enumerate(self.tags[:3], start=1):
                kuaishou_logger.info(_msg("🏷️", f"adicionando o {index}  hashtags: #{tag}"))
                await page.keyboard.type(f"#{tag} ")
                await asyncio.sleep(2)

            loop = asyncio.get_running_loop()
            upload_deadline = loop.time() + KUAISHOU_UPLOAD_TIMEOUT_SECONDS
            retry_count = 0
            while loop.time() < upload_deadline:
                try:
                    number = await page.locator("text=上传中").count()
                    if number == 0:
                        kuaishou_logger.success(_msg("🥳", "vídeo enviado"))
                        break

                    if retry_count % 5 == 0:
                        kuaishou_logger.info(_msg("🏃", "enviando o vídeo"))

                    if await page.locator("text=上传失败").count():
                        await self.handle_upload_error(page)

                    await asyncio.sleep(2)
                except Exception as exc:
                    kuaishou_logger.warning(_msg("😵", f"erro ao ver o estado do envio; tentando de novo: {exc}"))
                    await asyncio.sleep(2)
                retry_count += 1
            else:
                raise TimeoutError(
                    f"tempo esgotado esperando o Kuaishou terminar o envio do vídeo (>{KUAISHOU_UPLOAD_TIMEOUT_SECONDS}s); publicação interrompida"
                )

            await self.set_thumbnail(page)

            await self.apply_collection(page)

            if self.publish_strategy == KUAISHOU_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time(page, self.publish_date)

            last_publish_error = None
            for attempt in range(1, KUAISHOU_PUBLISH_ATTEMPTS + 1):
                try:
                    confirmed = await _click_visible_publish_confirm(page)
                    if not confirmed:
                        publish_button = page.get_by_text("发布", exact=True)
                        if await publish_button.count() == 0:
                            raise RuntimeError("não achei o botão de publicar do Kuaishouão")
                        await publish_button.click()

                    await asyncio.sleep(1)
                    await _click_visible_publish_confirm(page)

                    await page.wait_for_url(KUAISHOU_MANAGE_URL_PATTERN, timeout=5000)
                    kuaishou_logger.success(_msg("🥳", "vídeo publicado com sucesso"))
                    break
                except Exception as exc:
                    last_publish_error = exc
                    kuaishou_logger.info(_msg(
                        "🏃", f"publicando o vídeo ({attempt}/{KUAISHOU_PUBLISH_ATTEMPTS}): {exc}"
                    ))
                    if self.debug:
                        await page.screenshot(full_page=True)
                    await asyncio.sleep(1)
            else:
                raise RuntimeError(
                    f"o Kuaishou falhou várias vezes seguidas {KUAISHOU_PUBLISH_ATTEMPTS} ª tentativa; parando por aqui: {last_publish_error}"
                )

            upload_success = True
        finally:
            if upload_success:
                await context.storage_state(path=self.account_file)
                kuaishou_logger.success(_msg("🥳", "cookie atualização concluída"))
                await asyncio.sleep(2)
            await context.close()
            await browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)


class KSNote(KSBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str | None = None,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
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
        self.title = title or (self.note[:20] if self.note else "")
        self.tags = tags or []

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("no envio de imagem e texto do Kuaishou, o título é obrigatório")
        if not self.image_paths:
            raise ValueError("no envio de imagem e texto do Kuaishou, as imagens são obrigatórias")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def upload_note_content(self, page: Page) -> None:
        kuaishou_logger.info(_msg("🏃", f"enviando o post de imagem e texto, com {len(self.image_paths)}  imagens"))
        kuaishou_logger.info(_msg("🔀", "mudando para o modo imagem e texto"))
        await page.locator('div[role="tablist"] div[role="tab"]:has-text("图文")').click()
        await page.wait_for_timeout(1000)

        kuaishou_logger.info(_msg("📤", "enviando as imagens"))
        upload_button = page.locator("button[class^='_upload-btn']").filter(has_text="上传图片")
        await upload_button.wait_for(state="visible", timeout=10000)

        async with page.expect_file_chooser() as fc_info:
            await upload_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.image_paths)

        know_button = page.locator('button[type="button"] span:text("我知道了")').first
        try:
            if await know_button.count() and await know_button.is_visible():
                await know_button.click()
        except Exception:
            pass

        await self.close_guide_overlay(page)

        kuaishou_logger.info(_msg("✍️", "preenchendo o conteúdo e as hashtags do post"))
        await _focus_desc_editor(page)
        await page.keyboard.press("Backspace")
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.press("Delete")
        await page.keyboard.type(self.note)
        await page.keyboard.press("Enter")

        for index, tag in enumerate(self.tags[:3], start=1):
            kuaishou_logger.info(_msg("🏷️", f"adicionando o {index}  hashtags: #{tag}"))
            await page.keyboard.type(f"#{tag} ")
            await asyncio.sleep(2)

        max_retries = 60
        retry_count = 0
        while retry_count < max_retries:
            try:
                number = await page.locator("text=上传中").count()
                if number == 0:
                    kuaishou_logger.success(_msg("🥳", "imagens enviadas"))
                    break

                if retry_count % 5 == 0:
                    kuaishou_logger.info(_msg("🏃", "enviando as imagens"))

                if await page.locator("text=上传失败").count():
                    kuaishou_logger.warning(_msg("😵", "o envio das imagens tropeçou; tentando de novo"))
                    await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.image_paths)

                await asyncio.sleep(2)
            except Exception as exc:
                kuaishou_logger.warning(_msg("😵", f"erro ao ver o estado do envio das imagens; tentando de novo: {exc}"))
                await asyncio.sleep(2)
            retry_count += 1

        if retry_count == max_retries:
            kuaishou_logger.warning(_msg("😵", "passei do limite de tentativas; o envio das imagens pode não ter terminadoído"))

        if self.publish_strategy == KUAISHOU_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            await self.set_schedule_time(page, self.publish_date)

        while True:
            try:
                publish_button = page.get_by_text("发布", exact=True)
                if await publish_button.count() > 0:
                    await publish_button.click()

                await asyncio.sleep(1)
                confirm_button = page.get_by_text("确认发布")
                if await confirm_button.count() > 0:
                    await confirm_button.click()

                await page.wait_for_url(KUAISHOU_MANAGE_URL_PATTERN, timeout=5000)
                kuaishou_logger.success(_msg("🥳", "post de imagem e texto publicado com sucesso"))
                break
            except Exception as exc:
                kuaishou_logger.info(_msg("🏃", f"publicando o post de imagem e texto: {exc}"))
                if self.debug:
                    await page.screenshot(full_page=True)
                await asyncio.sleep(1)

    async def upload(self, playwright: Playwright) -> None:
        kuaishou_logger.info(_msg("🧍", "conferindo cookie, imagens e horário de publicação"))
        await self.validate_upload_args()
        kuaishou_logger.info(_msg("🥳", "verificação antes do envio do post concluída"))

        if self.local_executable_path:
            browser = await playwright.chromium.launch(
                headless=self.headless,
                executable_path=self.local_executable_path,
            )
        else:
            browser = await playwright.chromium.launch(
                headless=self.headless,
                channel="chromium",
            )
        context = await browser.new_context(storage_state=self.account_file)
        context = await set_init_script(context)

        upload_success = False
        try:
            page = await context.new_page()
            await page.goto(KUAISHOU_UPLOAD_URL)
            kuaishou_logger.info(_msg("🧭", "indo para a página de imagem e texto do Kuaishou"))
            await page.wait_for_url(KUAISHOU_UPLOAD_URL_PATTERN)

            await self.upload_note_content(page)
            upload_success = True
        finally:
            if upload_success:
                await context.storage_state(path=self.account_file)
                kuaishou_logger.success(_msg("🥳", "cookie atualização concluída"))
                await asyncio.sleep(2)
            await context.close()
            await browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
