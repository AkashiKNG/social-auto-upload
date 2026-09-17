# -*- coding: utf-8 -*-
from datetime import datetime

import asyncio
import inspect
import os
import sys
from pathlib import Path

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import BASE_DIR, DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file
from utils.login_qrcode import save_data_url_image
from utils.log import douyin_logger

DOUYIN_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
DOUYIN_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


async def _read_verify_code(code_file: str) -> str:
    if os.path.exists(code_file):
        with open(code_file, encoding="utf-8") as file_obj:
            return file_obj.read().strip()

    if not sys.stdin or not sys.stdin.isatty():
        return ""

    try:
        return (await asyncio.to_thread(input, "digite o código do SMS do Douyin (só apertar Enter para tentar de novo depois): ")).strip()
    except (EOFError, OSError):
        return ""


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


async def _native_click(page, locator) -> bool:
    """faz no elemento" nível humano " clica: clique real do mouse no centro + dispara a sequência completa de eventos de ponteiro e mouse.
    verificação de identidade do Douyinçãocomponente (uc_verification_component)ele só aceita essa sequência inteira, não um clique simples.
    devolve se o clique deu certo."""
    try:
        await locator.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    try:
        box = await locator.bounding_box()
    except Exception:
        box = None
    if not box:
        try:
            await locator.click(timeout=8000)
            return True
        except Exception:
            return False
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    try:
        await page.mouse.move(x, y)
        await asyncio.sleep(0.15)
        await page.mouse.click(x, y)
        await asyncio.sleep(0.2)
        await page.evaluate(
            """({x, y}) => {
                const el = document.elementFromPoint(x, y);
                if (!el) return;
                const opts = {bubbles:true,cancelable:true,composed:true,clientX:x,clientY:y,view:window,pointerId:1,pointerType:'mouse',isPrimary:true,button:0,buttons:1};
                for (const t of ['pointerover','pointerenter','pointerdown','mousedown','pointerup','mouseup','click']) {
                    const C = t.startsWith('pointer') ? PointerEvent : MouseEvent;
                    try { el.dispatchEvent(new C(t, opts)); } catch(e){ try{ el.dispatchEvent(new MouseEvent(t,opts)); }catch(_){} }
                }
            }""",
            {"x": x, "y": y},
        )
        return True
    except Exception:
        return False


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return

    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(success: bool, status: str, message: str, account_file: str, qrcode: dict | None = None, current_url: str = "") -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def cookie_auth(account_file):
    if not os.path.exists(account_file):
        return False

    use_headless = os.environ.get("DOUYIN_COOKIE_AUTH_HEADLESS", "true").lower() in ("1", "true", "yes")
    launch_kwargs = {"headless": use_headless, "channel": "chromium", "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"]}
    for _attempt in range(3):
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_kwargs)
            try:
                context = await browser.new_context(storage_state=account_file)
                context = await set_init_script(context)
                page = await context.new_page()
                await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded", timeout=90000)
                await page.wait_for_timeout(2500)  # espera a página firmar, para uma navegação rápida não enganar
                has_login = await page.get_by_text("手机号登录").count() or await page.get_by_text("扫码登录").count()
                if "content/upload" in page.url and not has_login:
                    return True
            except Exception:
                pass
            finally:
                await browser.close()
    return False


async def douyin_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS, cdp_url: str | None = None):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookiearquivo inexistente ou expirado", account_file)
            return result if return_detail else False
        douyin_logger.info(_msg("🥹", "cookie expirou: vou abrir o navegador para entrar de novo"))
        result = await douyin_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless, cdp_url=cdp_url)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookieválido", account_file)
    return result if return_detail else True


async def _extract_douyin_qrcode_src(page: Page) -> str:
    # espera o carregamento do SPA concluído (não espera só "login por QR code" texto, senão o Douyin carregando devagar estoura os 30 s).
    # dá tempo depois do domcontentloaded para o JS do site montar o cartão de login.
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    scan_login_tab = page.get_by_text("扫码登录", exact=True).first
    # attached estado: basta existir no DOM, sem exigir visível ou renderizado, para evitar corrida
    await scan_login_tab.wait_for(state="attached", timeout=60000)

    # nova central do criador do Douyin (single_tab + animate_qrcode_container) não usa mais aria-label="QR code".
    # tenta vários seletores por ordem de prioridade; basta um acertar.
    qrcode_selectors = [
        'div#animate_qrcode_container img[src^="data:image"]',
        'div[class*="animate_qrcode_container"] img[src^="data:image"]',
        'div[class*="scan_qrcode_login_content"] img[src^="data:image"]',
        'img[aria-label="二维码"]'  # texto da própria página,
    ]
    last_err: Exception | None = None
    for sel in qrcode_selectors:
        qrcode_img = page.locator(sel).first
        try:
            await qrcode_img.wait_for(state="attached", timeout=10000)
        except Exception as e:
            last_err = e
            continue
        src = await qrcode_img.get_attribute("src")
        if src:
            return src
        last_err = RuntimeError(f"selector {sel} achei, mas o src está vazio")

    raise RuntimeError(f"não consegui pegar o endereço do QR code de login do Douyin (last_err={last_err})")


async def _save_douyin_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    # pegamos o src do QR code só para salvar e mostrar no terminal; não achar não é grave — com janela, o QR code aparece e basta escanear
    try:
        qrcode_src = await _extract_douyin_qrcode_src(page)
    except Exception as exc:
        douyin_logger.warning(_msg("😵", f"não localizei o elemento do QR code ({str(exc)[:50]})——escaneie o QR code na janela que abriu; sigo esperando o login"))
        return {"image_path": "", "image_data_url": ""}
    qrcode_path = save_data_url_image(qrcode_src, build_login_qrcode_path(account_file))
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            douyin_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {previous_qrcode_path}"))
    douyin_logger.info(_msg("🖼️", f"QR code pronto, salvo em: {qrcode_path}"))
    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, "aplicativo do Douyin")
    else:
        douyin_logger.warning(_msg("😵", f"o terminal não mostra o QR code inteiro; abra {qrcode_path} escanear o QR code"))
    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_douyin_login_completed(page: Page) -> bool:
    # depois do login vai para qualquer página sob creator-micro (home/content etc.); a tela de login é a raiz creator.douyin.com/
    if "creator.douyin.com/creator-micro" not in page.url:
        return False

    login_markers = [
        page.get_by_text("扫码登录", exact=True).first,
        page.get_by_text("手机号登录", exact=True).first,
        page.get_by_text("二维码失效", exact=True).first,
        page.get_by_role("img", name="二维码").first,
    ]

    for marker in login_markers:
        if not await marker.count():
            continue
        try:
            if await marker.is_visible():
                return False
        except Exception:
            continue

    return True


async def _wait_for_douyin_login(page: Page, account_file: str, qrcode_info: dict, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 100) -> dict:
    qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None
    original_url = page.url
    saw_2fa = False
    for _ in range(max_checks):
        if await _is_douyin_login_completed(page):
            douyin_logger.info(_msg("🥳", f"QR code lido: já estou na página de quem entrou: {page.url}"))
            return _build_login_result(True, "success", "login por QR code do Douyin concluído", account_file, qrcode_info, page.url)

        # URL mudança + sessionid fora do lugar → fluxo de segunda verificação; seguindo na espera
        if page.url != original_url and not await _is_douyin_login_completed(page):
            sms_input = page.locator('input[placeholder*="验证码"], input[type="tel"], input[placeholder*="短信"], input[placeholder*="手机号"]')
            if await sms_input.count() > 0:
                if not saw_2fa:
                    douyin_logger.warning(_msg("⚠️", f"o Douyin pediu verificação por SMS ou de segurançação, digite na janela que abriu. Esperando o sessionid ({_}/{max_checks})"))
                    saw_2fa = True
            await asyncio.sleep(poll_interval)
            continue

        expired_box = page.get_by_text("二维码失效", exact=True).locator("..").first
        if await expired_box.count() and await expired_box.is_visible():
            douyin_logger.warning(_msg("😵", "o QR code expirou; gerando outro"))
            await expired_box.click()
            await asyncio.sleep(1)
            qrcode_info = await _save_douyin_qrcode(page, account_file, qrcode_path, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None

        await asyncio.sleep(poll_interval)

    return _build_login_result(False, "timeout", "tempo esgotado esperando o login por QR code do Douyin", account_file, qrcode_info, page.url)

async def douyin_cookie_gen(
    account_file,
    qrcode_callback=None,
    poll_interval: int = 2,
    max_checks: int = 60,
    headless: bool = LOCAL_CHROME_HEADLESS,
    cdp_url: str | None = None,
):
    async with async_playwright() as playwright:
        if cdp_url:
            browser = await playwright.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            should_close_context = False
        else:
            browser = await playwright.chromium.launch(headless=headless, channel="chromium")
            context = await browser.new_context()
            should_close_context = True
        context = await set_init_script(context)
        qrcode_path = None
        result = _build_login_result(False, "failed", "falha no login do Douyin", account_file)
        try:
            page = await context.new_page()
            await page.goto("https://creator.douyin.com/")
            qrcode_info = await _save_douyin_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None
            douyin_logger.info(_msg("🧍", "escaneie o QR code; estou esperando o login terminar"))
            result = await _wait_for_douyin_login(
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
                # loginaprovado "publicar vídeo" confirmardeu certo e o storage_state acabou de ser tirado de um navegador logado,
                # não repete mais a verificação instável pelo navegador (era exatamente o bug antigo que fazia o sucesso passar por falha).
                # só confere de leve se o arquivo tem sessionid.
                try:
                    import json as _json
                    _d = _json.load(open(account_file))
                    _has_sess = any(c.get("name") == "sessionid" and c.get("value") for c in _d.get("cookies", []))
                    if not _has_sess:
                        result = _build_login_result(
                            False,
                            "cookie_invalid",
                            "o fluxo do QR code do Douyin terminou, mas o cookie não tem sessionid",
                            account_file,
                            qrcode_info,
                            page.url,
                        )
                except Exception as _e:
                    douyin_logger.warning(_msg("⚠️", f"cookie erro ao validar o arquivo (ignorado: tratando como sucesso): {_e}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                douyin_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {qrcode_path}"))
            if not result["success"]:
                douyin_logger.error(_msg("😢", f"falha no login: {result['message']}"))
            if should_close_context:
                await context.close()
            await browser.close()
        return result


class DouYinBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.publish_date = publish_date
        self.account_file = account_file
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.date_format = "%Y年%m月%d日 %H:%M"
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = headless

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookiearquivo inexistente; conclua antes o ídologin do Douyin: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookiearquivo expirado; conclua antes o ídologin do Douyin: {self.account_file}")
        if self.publish_strategy not in {DOUYIN_PUBLISH_STRATEGY_IMMEDIATE, DOUYIN_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"estratégia de publicação não suportada: {self.publish_strategy}")

        if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def set_schedule_time_douyin(self, page, publish_date):
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await asyncio.sleep(1)
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

    async def fill_title_and_description(self, page: Page, title: str, description: str, tags: list[str] | None = None):
        # 2026-06 DOM da página de publicação do Douyin: título=input[placeholder*=preenche o título da obra], descrição=div.zone-container[contenteditable]
        # version_2(post/video) a página de publicação espera o envio de vídeoterminar para montar o formulário (na prática, uns 40 s), por isso o tempo de espera é de 120 s
        title_input = page.locator('input[placeholder*="填写作品标题"]').first
        await title_input.wait_for(state="visible", timeout=120000)
        await title_input.fill(title[:30])

        description_editor = page.locator('div.zone-container[contenteditable="true"]').first
        await description_editor.wait_for(state="visible", timeout=120000)
        await description_editor.click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.press("Delete")

        # preenche primeiro o texto descrição, preenche de novo #hashtags (antes o parâmetro description não era escrito e o post do Douyin ficava só com etiquetas, sem texto)
        if description and description.strip():
            await page.keyboard.type(description.strip())

        for tag in tags or []:
            await page.keyboard.type(" #" + tag)
            await page.keyboard.press("Space")
        await page.keyboard.press("Escape")  # fecha a lista de hashtags para a camada não roubar os próximos cliques

    async def set_location(self, page: Page, location: str = ""):
        if not location:
            return
        await page.locator('div.semi-select span:has-text("输入地理位置")').click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    async def handle_product_dialog(self, page: Page, product_title: str):
        await page.wait_for_timeout(2000)
        await page.wait_for_selector('input[placeholder="请输入商品短标题"]', timeout=10000)
        short_title_input = page.locator('input[placeholder="请输入商品短标题"]')
        if not await short_title_input.count():
            douyin_logger.error(_msg("😵", "não achei o campo do título curto do produto"))
            return False

        product_title = product_title[:10]
        await short_title_input.fill(product_title)
        await page.wait_for_timeout(1000)

        finish_button = page.locator('button:has-text("完成编辑")')
        if "disabled" not in await finish_button.get_attribute("class"):
            await finish_button.click()
            douyin_logger.debug(_msg("🥳", "cliquei em concluir edição"))
            await page.wait_for_selector(".semi-modal-content", state="hidden", timeout=5000)
            return True

        douyin_logger.error(_msg("😵", "o botão de concluir edição está cinza; fechando a janela primeiro"))
        cancel_button = page.locator('button:has-text("取消")')
        if await cancel_button.count():
            await cancel_button.click()
        else:
            close_button = page.locator(".semi-modal-close")
            await close_button.click()
        await page.wait_for_selector(".semi-modal-content", state="hidden", timeout=5000)
        return False

    async def set_product_link(self, page: Page, product_link: str, product_title: str):
        await page.wait_for_timeout(2000)
        try:
            await page.wait_for_selector("text=添加标签", timeout=10000)
            dropdown = page.get_by_text("添加标签").locator("..").locator("..").locator("..").locator(".semi-select").first
            if not await dropdown.count():
                douyin_logger.error(_msg("😵", "não achei a lista de etiquetas"))
                return False
            douyin_logger.debug(_msg("🧍", "achei a lista de etiquetas; escolhendo 'carrinho de compras'"))
            await dropdown.click()
            await page.wait_for_selector('[role="listbox"]', timeout=5000)
            await page.locator('[role="option"]:has-text("购物车")').click()
            douyin_logger.debug(_msg("🥳", "'carrinho de compras' já está selecionado"))

            await page.wait_for_selector('input[placeholder="粘贴商品链接"]', timeout=5000)
            input_field = page.locator('input[placeholder="粘贴商品链接"]')
            await input_field.fill(product_link)
            douyin_logger.debug(_msg("🔗", f"o link do produto já está preenchido: {product_link}"))

            add_button = page.locator('span:has-text("添加链接")')
            button_class = await add_button.get_attribute("class")
            if "disable" in button_class:
                douyin_logger.error(_msg("😵", "não dá para clicar em adicionar link agora"))
                return False
            await add_button.click()
            douyin_logger.debug(_msg("🥳", "cliquei em adicionar link"))

            await page.wait_for_timeout(2000)
            error_modal = page.locator("text=未搜索到对应商品")
            if await error_modal.count():
                confirm_button = page.locator('button:has-text("确定")')
                await confirm_button.click()
                douyin_logger.error(_msg("😢", "este link de produto é inválido"))
                return False

            if not await self.handle_product_dialog(page, product_title):
                return False

            douyin_logger.debug(_msg("🥳", "link do produto definido"))
            return True
        except Exception as e:
            douyin_logger.error(_msg("😢", f"erro ao definir o link do produto: {str(e)}"))
            return False

    async def set_self_declaration(self, page: Page, declaration: str) -> bool:
        """Douyin" declaração própria ": abre a janela de declaração → escolha única do tipo de declaração → confirmar.

        janela de verdade (conferido pelo usuário no F12): header " escolha o tipo de declaração (escolha única)", a opção é
        label.semi-radio: o texto do span.semi-radio-addon dentro, "conteúdo gerado por IA" e
        "o conteúdo é uma republicação""o conteúdo é uma opinião ou impressão pessoal" fica na mesma linha; o rodapé tem
        semi-button-primary ="confirmar".

        a entrada e a janela são renderizadas de forma assíncrona e, depois das hashtags, as camadas mention-wrapper/semi-portal que sobram cobrem a entrada,
        é preciso limpar as camadas antes de clicar. Devolve False se falhar.

        Args:
            declaration: texto do tipo de declaração (quem chama passa explicitamente)
        """
        try:
            # limpa as camadas que tapam a entrada (hashtagslista ou camada de tutorial), e tira o foco do campo
            await self._clear_blocking_overlays(page)

            # entrada: abre a janela de declaração (vários textos possíveis; o nativo é só reserva)
            entry = None
            # textos da própria página do Douyin: não traduzir
            for etext in ["请选择自主声明", "请选择声明类型", "添加自主声明", "自主声明", "作品声明"]:
                cand = page.get_by_text(etext).first
                if await cand.count():
                    entry = cand
                    break
            if entry is not None:
                try:
                    await entry.scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    pass
                try:
                    await entry.click(timeout=6000)
                except Exception:
                    await _native_click(page, entry)
                await page.wait_for_timeout(1200)

            # janela: header " escolha o tipo de declaração (escolha única)"
            dialog = page.locator(".semi-modal-content").filter(has_text="请选择声明类型").first
            if await dialog.count() == 0:
                dialog = page.locator(".semi-modal-body").filter(has_text="请选择声明类型").first
            if await dialog.count() == 0:
                douyin_logger.warning(_msg("🧾", "a janela da declaração própria não abriu; pulando a declaração e continuando a publicação"))
                return False
            await dialog.first.wait_for(state="visible", timeout=6000)

            # opção: casa exatamente o span.semi-radio-addon dentro do label.semi-radio
            option = dialog.locator("label.semi-radio").filter(
                has=page.locator(f'.semi-radio-addon:text-is("{declaration}")')
            ).first
            if await option.count() == 0:
                option = dialog.locator("label.semi-radio").filter(has_text=declaration).first
            if await option.count():
                try:
                    await option.click(timeout=6000)
                except Exception:
                    await _native_click(page, option)
            else:
                await dialog.get_by_text(declaration, exact=True).first.click(timeout=6000, force=True)
            await page.wait_for_timeout(400)

            # confirmar: footer  o botão principalão
            confirm_btn = dialog.locator("button.semi-button-primary").filter(has_text="确定").first
            if await confirm_btn.count() == 0:
                confirm_btn = dialog.get_by_role("button", name="确定").first
            if await confirm_btn.count() == 0:
                confirm_btn = page.get_by_role("button", name="确定").first
            try:
                await confirm_btn.click(timeout=6000)
            except Exception:
                await _native_click(page, confirm_btn)
            try:
                await dialog.first.wait_for(state="hidden", timeout=6000)
            except Exception:
                pass
            douyin_logger.success(_msg("🧾", f"declaração própria escolhida: '{declaration}'"))
            return True
        except Exception as exc:
            douyin_logger.warning(_msg("🧾", f"não consegui definir a declaração própria; pulando esse passo e continuando a publicação: {exc}"))
            return False

    async def select_bgm(self, page: Page, bgm_name: str) -> bool:
        """escolhe a trilha do post de imagens: é um extra; sem resultado ou com erro, pula sem interromper a publicação."""
        try:
            # clica "escolhermúsica" botão
            music_entry = page.locator('text="选择音乐"').nth(1)
            if not await music_entry.count():
                music_entry = page.locator('text="选择音乐"').first
            await music_entry.wait_for(state="visible", timeout=10000)
            await music_entry.click()

            # espera a barra lateral aparecer e busca
            sidesheet = page.locator(".semi-sidesheet-content").first
            await sidesheet.wait_for(state="visible", timeout=8000)
            search_input = sidesheet.locator('input.semi-input[placeholder="搜索音乐"]').first
            await search_input.wait_for(state="visible", timeout=5000)
            await search_input.fill(bgm_name)
            await search_input.press("Enter")

            # espera o resultado da busca
            await asyncio.sleep(2)
            first_card = sidesheet.locator(".card-container-tmocjc").first
            try:
                await first_card.wait_for(state="visible", timeout=8000)
            except Exception:
                douyin_logger.warning(_msg("🎵", f"a busca pela música '{bgm_name}' não trouxe nada; pulando"))
                await self._close_music_sidesheet(page)
                return False

            # mostra o nome da música encontrada
            try:
                song_name_el = first_card.locator(".song-name-oRge4d").first
                if await song_name_el.count():
                    song_name = await song_name_el.inner_text()
                    douyin_logger.info(_msg("🎵", f"achei: {song_name}"))
            except Exception:
                pass

            # JS clica "usa" (botão visibility:hidden, o clique normal não funciona)
            apply_btn = first_card.locator(".apply-btn-LUPP0D").first
            await apply_btn.evaluate("el => el.click()")
            douyin_logger.info(_msg("🥳", f"trilha '{bgm_name}' aplicada"))

            # espera a barra lateral fechar; estourando o tempo, fecha na mão
            try:
                await sidesheet.wait_for(state="hidden", timeout=5000)
            except Exception:
                await self._close_music_sidesheet(page)

            return True
        except Exception as exc:
            douyin_logger.warning(_msg("🎵", f"erro ao adicionar a trilha; pulando esse passo e continuando a publicação: {exc}"))
            try:
                await self._close_music_sidesheet(page)
            except Exception:
                pass
            return False

    async def _close_music_sidesheet(self, page: Page) -> None:
        try:
            close_btn = page.locator(".semi-sidesheet-close").first
            if await close_btn.count() and await close_btn.is_visible():
                await close_btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass


class DouYinVideo(DouYinBaseUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        thumbnail_landscape_path=None,
        productLink="",
        productTitle="",
        thumbnail_portrait_path=None,
        desc: str | None = None,
        collection_name: str | None = None,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        declaration: str | None = None,
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
        self.tags = tags
        self.thumbnail_landscape_path = thumbnail_landscape_path
        self.thumbnail_portrait_path = thumbnail_portrait_path
        self.productLink = productLink
        self.productTitle = productTitle
        self.desc = desc or ""
        self.collection_name = collection_name
        self.declaration = declaration.strip() if declaration and declaration.strip() else None

    async def apply_self_declaration(self, page: Page) -> None:
        if not self.declaration:
            return
        if not await self.set_self_declaration(page, self.declaration):
            raise RuntimeError(f"não consegui definir a declaração própria '{self.declaration}'; recusando continuar a publicação")

    async def _clear_blocking_overlays(self, page: Page) -> None:
        """limpa as camadas que roubam o clique: as que sobram das hashtags /@lista de menções(publish-mention-wrapper)
        e o semi-portal onde ele está, outros semi-portal não modais (tooltip/popover) e a camada de tutorial do shepherd,
        e tira o foco do campo atual. O portal da própria lista de coletânea/declaração é "depois de abrir" só é criado depois, então limpar aqui não atrapalha.

        a causa está no recorder.log de 2026-08-10 05:31: apply_collection ao clicar na lista de coletâneas,
        publish-mention-wrapper / semi-portal intercepta os eventos de ponteiro → click tempo esgotado → o agrupamento foi pulado.
        """
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        try:
            await page.evaluate(
                """() => {
                    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
                    document.querySelectorAll('.shepherd-element,.shepherd-modal-overlay-container').forEach(e=>e.remove());
                    document.querySelectorAll('[class*="mention-wrapper"]').forEach(e=>{ const p=e.closest('.semi-portal'); (p||e).remove(); });
                    // fecha as camadas Semi não modais que sobraram (mantém as janelas modais, como a da declaração)
                    document.querySelectorAll('.semi-portal').forEach(e=>{ if(!e.querySelector('.semi-modal, .semi-modal-content')) e.remove(); });
                }"""
            )
        except Exception:
            pass
        await page.wait_for_timeout(400)

    async def apply_collection(self, page: Page) -> None:
        """na página do formulário de publicação" adiciona à coletânea " escolhe a coletânea na área (Semi Design select, biblioteca de componentes da ByteDance).

        a estrutura, junto com a do Kuaishou (Ant Design)diferente: o nome da coletânea é texto puro em span.option-title-*, sem atributo label,
        casa pelo texto exato; o gatilho usa a classe própria .select-collection-* localiza (único na página, primeiro nível
        "coletânea/série" tipoessa lista não tem relação e não é escolhida por engano).sem coletânea correspondente, aperta Escape para fechar a lista,
        publica direto, sem marcar nada (a tela deixa em branco, sem travar a publicação).
        """
        if not self.collection_name:
            return
        try:
            # correção importante: o que sobra das hashtags depois de preenchê-las /@lista de menções(publish-mention-wrapper) e o semi-portal
            # a camada cobre "adiciona à coletânea" na lista, o clique normal cai todo na camada de cima→tempo esgotado→o agrupamento foi pulado. Limpa as camadas antes de clicar.
            await self._clear_blocking_overlays(page)

            trigger = page.locator('[class*="select-collection-"]').first
            if await trigger.count() == 0:
                douyin_logger.warning(_msg("😵", "não achei\"adiciona à coletânea\"lista suspensa; seguindo sem agrupar"))
                return
            selection = trigger.locator(".semi-select-selection")
            try:
                await selection.click(timeout=5000)
            except Exception:
                await self._clear_blocking_overlays(page)
                await _native_click(page, selection)
            await page.wait_for_timeout(800)

            option = page.locator(".semi-select-option.collection-option").filter(
                has=page.locator(f'[class*="option-title-"]:text-is("{self.collection_name}")')
            )
            if await option.count() == 0:
                douyin_logger.warning(
                    _msg("😵", f"a lista de coletâneas não tem '{self.collection_name}': segue sem selecionar nenhuma")
                )
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                return

            try:
                await option.first.click(timeout=5000)
            except Exception:
                await _native_click(page, option.first)
            await page.wait_for_timeout(500)
            douyin_logger.success(_msg("🥳", f"coletânea escolhida: {self.collection_name}"))
        except Exception as exc:
            douyin_logger.warning(_msg("😵", f"não consegui escolher a coletânea; sigo a publicação sem ela: {exc}"))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

    async def _submit_sms_verify_code(self, page: Page, sms_input, code: str, code_file: str) -> bool:
        douyin_logger.info(_msg("✍️", f"peguei a verificaçãocódigo, pronto para preencher: {code}"))
        await sms_input.click()
        await sms_input.fill(code)
        douyin_logger.info(_msg("✅", "verificaçãocódigo preenchido no campo"))
        await page.wait_for_timeout(500)

        verify_btn = page.locator('div.uc-ui-verify_sms-verify_button:has-text("验证")').first
        if await verify_btn.count() and await verify_btn.is_visible():
            try:
                await verify_btn.click(force=True)
                douyin_logger.success(_msg("✅", "cliquei no botão de verificação (force)"))
            except Exception:
                await page.eval_on_selector('div.uc-ui-verify_sms-verify_button', 'el => el.click()')
                douyin_logger.success(_msg("✅", "cliquei no botão de verificação (JS)"))
        else:
            verify_by_text = page.get_by_text("验证", exact=True).first
            if await verify_by_text.count():
                await verify_by_text.click(force=True)
                douyin_logger.success(_msg("✅", "cliquei no botão de verificação (texto)"))
            else:
                douyin_logger.warning(_msg("⚠️", "não achei a verificaçãobotão, tentando com Enter"))
                await page.keyboard.press("Enter")

        if os.path.exists(code_file):
            os.remove(code_file)
            douyin_logger.info(_msg("🧹", "verificaçãoarquivo do código apagado"))

        await page.wait_for_timeout(3000)
        douyin_logger.info(_msg("🔄", "verificaçãocódigo tratado concluído, continua a publicaçãofluxo"))
        return True

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("no modo vídeo, o título é obrigatório")

        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_landscape_path:
            self.thumbnail_landscape_path = str(self.validate_image_file(self.thumbnail_landscape_path))
        if self.thumbnail_portrait_path:
            self.thumbnail_portrait_path = str(self.validate_image_file(self.thumbnail_portrait_path))

    async def handle_upload_error(self, page):
        douyin_logger.warning(_msg("😵", "o envio do vídeo tropeçou; tentando de novo"))
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def handle_auto_video_cover(self, page):
        if await page.get_by_text("请设置封面后再发布").first.is_visible():
            douyin_logger.info(_msg("🧍", "antes de publicar é preciso acertar a capa"))
            recommend_cover = page.locator('[class^="recommendCover-"]').first
            if await recommend_cover.count():
                douyin_logger.info(_msg("🏃", "escolhendo a primeira capa sugerida"))
                try:
                    await recommend_cover.click()
                    await asyncio.sleep(1)
                    confirm_text = "是否确认应用此封面？"  # texto da própria página
                    if await page.get_by_text(confirm_text).first.is_visible():
                        douyin_logger.info(_msg("🪟", f"a caixa de confirmação apareceu: {confirm_text}"))
                        await page.get_by_role("button", name="确定").click()
                        douyin_logger.info(_msg("🥳", "capa sugerida aplicada"))
                        await asyncio.sleep(1)
                    douyin_logger.info(_msg("🥳", "escolha da capa concluído"))
                    return True
                except Exception as e:
                    douyin_logger.warning(_msg("😵", f"não consegui escolher a capa sugerida: {e}"))
        return False

    async def set_thumbnail(self, page: Page):
        if not self.thumbnail_landscape_path and not self.thumbnail_portrait_path:
            return

        douyin_logger.info(_msg("🏃", "definindo o capa do vídeo"))
        # limpa antes a camada do tutorial (shepherd), senão ela rouba o clique da capa e a janela não abre
        await page.evaluate(
            "() => document.querySelectorAll('.shepherd-element,.shepherd-modal-overlay-container').forEach(e=>e.remove())"
        )

        cover_area = page.locator('[class*="cover-"]').filter(has=page.locator("img")).first
        if not await cover_area.count():
            cover_area = page.locator('[class*="cover"]').first

        # abre a janela da capa: nos componentes do Douyin o clique normal ou forçado costuma falhar em silêncio (mesmo problema do botão "concluído"),
        # sempre usa _native_click, que dispara a sequência nativa completa; depois do clique confere se a janela abriu e, se não, tenta de novo.
        cover_locator_str = 'div.dy-creator-content-modal'
        cover_locator = page.locator(cover_locator_str).first
        opened = False
        # logo depois do envio a página ainda está em transição: espera a área da capa firmar e tira "clicar antes da página firmar acerta o vazio" esse gatilho
        try:
            await cover_area.wait_for(state="visible", timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        for attempt in range(5):
            # hover algumas vezes, esperando "editar capa/escolhe a capa" a entrada aparecer de verdade, para não clicar no vazio no centro da capa
            trigger = None
            trigger_txt = "área da capa"
            for _ in range(3):
                try:
                    await cover_area.hover(force=True)
                    await page.wait_for_timeout(600)
                except Exception:
                    pass
                # textos da própria página do Douyin: não traduzir
                for txt in ["编辑封面", "选择封面", "设置封面"]:
                    t = page.get_by_text(txt, exact=True).first
                    if await t.count() and await t.is_visible():
                        trigger, trigger_txt = t, txt
                        break
                if trigger is not None:
                    break
            if trigger is None:
                trigger = cover_area
            # cada rodada usa _native_click (force click costuma falhar em silêncio nos componentes do Douyin e só gasta tempo)
            await _native_click(page, trigger)
            douyin_logger.info(_msg("🖼️", f"cliquei em {trigger_txt}, tentando abrir a janela da capa (tentativa {attempt + 1})"))
            try:
                await page.wait_for_selector(cover_locator_str, timeout=5000)
                opened = True
                break
            except Exception:
                continue
        if not opened:
            douyin_logger.warning(_msg("⚠️", "a janela da capa não abriu; pulando a capa personalizada e continuando a publicação (deixando a capa sugerida como reserva)"))
            return

        await page.wait_for_timeout(1500)

        # a janela da capa tem dois input.semi-upload-hidden-input (cada um vem com um irmão -replace):
        #   ① lado esquerdo "gera a imagem de referência"(AIimagem de referência da capa)——drag a área é semi-upload-drag-area-custom e só tem + ícone;
        #   ② área de escolha do quadro "envia a capa"——drag a área contém .semi-upload-drag-area-main-text " clicaenviararquivo ou arraste…".
        # o código antigo pegava com .first①, a capa acabou no espaço da imagem de referência da IA→a capa de verdade não é aplicada e a detecção/geração por IA fica rodando,
        # "concluído" a janela nunca fecha→tapa o publicar→tempo esgotado (causa real conferida pelo usuário no F12).
        # passa a localizar com precisão pela área de arrastar main-text②o input de envio; sem achar, cai para o .last.
        cover_upload = cover_locator.locator(
            '.semi-upload:has(.semi-upload-drag-area-main-text) input.semi-upload-hidden-input'
        ).first
        if await cover_upload.count() == 0:
            cover_upload = cover_locator.locator("input.semi-upload-hidden-input").last

        if self.thumbnail_portrait_path:
            # a janela já abre na aba "definir capa vertical"; por segurança, clica na aba (se já estiver ativo, ignora)
            try:
                await cover_locator.get_by_text("设置竖封面", exact=True).first.click(timeout=3000)
                await page.wait_for_timeout(800)
            except Exception:
                pass
            await cover_upload.set_input_files(self.thumbnail_portrait_path)
            await page.wait_for_timeout(3000)
            douyin_logger.info(_msg("🖼️", "capa vertical enviada para a pré-visualização"))
        elif self.thumbnail_landscape_path:
            try:
                await cover_locator.get_by_text("设置横封面", exact=True).first.click(timeout=3000)
                await page.wait_for_timeout(800)
            except Exception:
                pass
            await cover_upload.set_input_files(self.thumbnail_landscape_path)
            await page.wait_for_timeout(3000)
            douyin_logger.info(_msg("🖼️", "capa horizontal enviada para a pré-visualização"))

        # ── espera o botão "concluído" liberar: enquanto a capa é processada ele fica semi-button-disabled e clicar não adianta ──
        def _finish_btn():
            return cover_locator.get_by_role("button", name="完成", exact=True).first

        for _ in range(30):  # no máximo ~15s espera o tratamento das imagens e o botãoliberado
            try:
                b = _finish_btn()
                if await b.count():
                    cls = await b.get_attribute("class") or ""
                    if "semi-button-disabled" not in cls:
                        break
            except Exception:
                pass
            await page.wait_for_timeout(500)

        # ── clica em "concluído" e confere se a janela saiu mesmo do DOM ──
        # nos componentes do Douyin o clique normal pode não dar erro e mesmo assim não funcionar, então cada rodada confere se a janela sumiu:
        # só some quando dá certo; se não, sobe para _native_click, trata a segunda confirmação e, por último, usa Esc como reserva.
        closed = False
        for attempt in range(4):
            btn = _finish_btn()
            if not await btn.count():
                btn = cover_locator.locator("button.semi-button").filter(has_text="完成").first
            if await btn.count() and await btn.is_visible():
                try:
                    await btn.click(timeout=4000)
                except Exception:
                    pass
                await page.wait_for_timeout(1500)
                if await cover_locator.count() == 0:
                    closed = True
                    break
                # o clique normal não fechou → dispara a sequência nativa completa de eventos
                await _native_click(page, btn)
                await page.wait_for_timeout(1500)
                if await cover_locator.count() == 0:
                    closed = True
                    break

            # depois de clicar em "concluído" o Douyin pode pedir uma segunda confirmação (por exemplo, quando não há capa horizontal, pergunta se confirma a conclusão) → clica no botão de confirmar
            # textos dos botões da própria página: não traduzir
            for cname in ["确定", "确认", "仍然完成", "仍要完成", "继续"]:
                confirm = page.locator(".semi-modal-content").get_by_role("button", name=cname, exact=True).first
                if await confirm.count() and await confirm.is_visible():
                    await _native_click(page, confirm)
                    await page.wait_for_timeout(1500)
                    break
            if await cover_locator.count() == 0:
                closed = True
                break

            # ainda não fechou: usa Esc como reserva e confere de novoçãouma vez
            douyin_logger.debug(_msg("🖼️", f"a janela da capa não fechou depois do concluído; tentando de novo (tentativa {attempt + 1})"))
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
            if await cover_locator.count() == 0:
                closed = True
                break

        if closed:
            douyin_logger.info(_msg("🥳", "capa do vídeo definida concluído, janela fechada"))
        else:
            douyin_logger.warning(_msg("⚠️", "a janela da capa não fechou e pode estar tapando a declaração própria/publicar"))


    async def upload(self, playwright: Playwright) -> None:
        douyin_logger.info(_msg("🧍", "conferindo cookie, arquivo de vídeo, capa e horário de publicação"))
        await self.validate_upload_args()
        douyin_logger.info(_msg("🥳", "verificação antes do envio concluída"))

        browser = await playwright.chromium.launch(headless=self.headless, channel="chromium", args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            storage_state=f"{self.account_file}",
            permissions=["geolocation"],
        )
        context = await set_init_script(context)

        page = await context.new_page()
        await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded", timeout=90000)
        douyin_logger.info(_msg("🏃", f"enviando o vídeo: {self.title}.mp4"))
        douyin_logger.info(_msg("🧭", "indo para a página de envio"))
        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=90000)

        # ── ao entrar na página pode aparecer a verificação de identidade (código por SMS) ou o site pode mandar de volta para a tela de login ──
        await page.wait_for_timeout(2000)

        # confirmarjá estou na página de envio (fora da tela de login), procura de novo o input de envio
        # usa um seletor mais preciso para não pegar o input do formulário de login
        upload_input = page.locator("input.upload-btn-input, div[class^='container'] input[accept]").first
        if not await upload_input.count():
            # reserva: descarta o input da tela de login
            upload_input = page.locator("div[class^='container'] input[type='file'], div[class^='container'] input.upload-input").first
        if not await upload_input.count():
            # última reserva
            upload_input = page.locator("div[class^='container'] input").first
        await upload_input.wait_for(state="attached", timeout=60000)
        await upload_input.set_input_files(self.file_path)

        while True:
            try:
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page",
                    timeout=3000,
                )
                douyin_logger.info(_msg("🥳", "entrei na página de publicação version_1"))
                break
            except Exception:
                try:
                    await page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                        timeout=3000,
                    )
                    douyin_logger.info(_msg("🥳", "entrei na página de publicação version_2"))
                    break
                except Exception:
                    douyin_logger.debug(_msg("🧍", "ainda não cheguei no página de publicação do vídeo; esperando mais um pouco"))
                    await asyncio.sleep(0.5)

        await asyncio.sleep(1)
        douyin_logger.info(_msg("✍️", "preenchendo título, descrição e hashtags"))
        await self.fill_title_and_description(page, self.title, self.desc, self.tags)
        douyin_logger.info(_msg("🏷️", f"colei no total {len(self.tags)}  hashtags"))

        while True:
            try:
                number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                if number > 0:
                    douyin_logger.success(_msg("🥳", "vídeo enviado"))
                    break
                douyin_logger.info(_msg("🏃", "enviando o vídeo"))
                await asyncio.sleep(2)
                if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                    douyin_logger.error(_msg("😵", "detectei falha no envio; tentando de novo"))
                    await self.handle_upload_error(page)
            except Exception:
                douyin_logger.debug(_msg("🧍", "ainda esperando o envio do vídeo concluído"))
                await asyncio.sleep(2)

        if self.productLink and self.productTitle:
            douyin_logger.info(_msg("🛒", "definindo o link do produto"))
            await self.set_product_link(page, self.productLink, self.productTitle)
            douyin_logger.info(_msg("🥳", "link do produto definido concluído"))

        # declaração própria: este vídeo contém conteúdo gerado por IA (TTS narração / legenda por IA / vinheta por IA), 
        # escolha honesta, conforme as regras da plataforma "conteúdo gerado por IA" (fica junto de republicação e afins: escolha única, sem subopção e sem fonte).
        if not self.declaration:
            self.declaration = "内容由AI生成"  # texto da opção na própria página
        await self.apply_self_declaration(page)

        # agrupa primeiro: a janela da capa ainda não abriu, então a camada dy-creator-content-portal não bloqueia a lista de coletâneas
        #  (na prática, sem janela a tela da capa costuma travar "verificando" não fechou e vai tapar "adiciona à coletânea" lista suspensa)
        await self.apply_collection(page)

        # define a capa de novo (fica por último: fecha a janela para nenhuma camada tapar o botão de publicar)
        await self.set_thumbnail(page)

        third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
        if await page.locator(third_part_element).count():
            if "semi-switch-checked" not in await page.eval_on_selector(third_part_element, "div => div.className"):
                await page.locator(third_part_element).locator("input.semi-switch-native-control").click()

        if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        sms_prompt_logged = False
        while True:
            try:
                # remove o que bloqueia o botão de publicarclicaa camada do tutorial ou da lista de hashtags
                await page.evaluate(
                    "() => { document.querySelectorAll('.shepherd-element, .shepherd-modal-overlay-container, [class*=\"mention-wrapper\"]').forEach(e => e.remove()); }"
                )
                # detecta e trata a verificação por SMSçãojanela do código
                sms_input = page.locator('input[placeholder*="验证码"], input[type="tel"], input[placeholder*="短信"], input[placeholder*="手机号"]').first
                if await sms_input.count() and await sms_input.is_visible():
                    douyin_logger.warning(_msg("📱", "o site pediu verificação por SMSçãojanela do código"))
                    # clica no botão de pegar o código (só na primeira vez)
                    get_code_btn = page.get_by_text("获取验证码").first
                    if await get_code_btn.count() and await get_code_btn.is_visible():
                        await get_code_btn.click()
                        douyin_logger.info(_msg("📤", "cliquei em pegar o código; veja o SMS no celular"))
                    code_file = os.path.join(BASE_DIR, "verify_code.txt")
                    code = await _read_verify_code(code_file)
                    if code:
                        sms_prompt_logged = False
                        await self._submit_sms_verify_code(page, sms_input, code, code_file)
                    elif not sms_prompt_logged:
                        douyin_logger.warning(_msg("⏳", f"espera a verificaçãodigitação do código: dá para digitar no terminal ou gravar num arquivo: {code_file}"))
                        sms_prompt_logged = True

                # ── fluxo normal de publicação ──
                publish_button = page.get_by_role("button", name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click(force=True)
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/manage**",
                    timeout=3000,
                )
                douyin_logger.success(_msg("🥳", "vídeo publicado com sucesso"))
                break
            except Exception:
                await self.handle_auto_video_cover(page)
                douyin_logger.info(_msg("🏃", "publicando o vídeo"))
                if self.debug:
                    await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

        await context.storage_state(path=self.account_file)
        douyin_logger.success(_msg("🥳", "cookie atualização concluída"))
        await asyncio.sleep(2)
        await context.close()
        await browser.close()

    async def douyin_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.douyin_upload_video()


class DouYinNote(DouYinBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        bgm: str = "",
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
        self.bgm = bgm or ""

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("no modo imagem e texto, o título é obrigatório")

        if len(self.title) > 20:
            raise ValueError(f"o título não pode passar de 20 caracteres; agora tem: {len(self.title)}caracteres")

        if not self.image_paths:
            raise ValueError("no modo imagem e texto, as imagens são obrigatórias")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        if len(self.image_paths) > 35:
            raise ValueError("no modo imagem e texto dá para enviar no máximo 35 imagens")

        note_len = len(self.note) if self.note else 0
        if note_len > 1000:
            raise ValueError(f"o texto não pode passar de 1000 caracteres; agora tem: {note_len}caracteres")

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def upload_note_content(self, page: Page) -> None:
        douyin_logger.info(_msg("🏃", f"enviando o post de imagem e texto, com {len(self.image_paths)}  imagens"))
        douyin_logger.info(_msg("🔀", "mudando para a publicação de imagem e texto"))
        await page.get_by_text("发布图文", exact=True).click()
        await page.wait_for_timeout(1000)

        douyin_logger.info(_msg("📤", "enviando as imagens"))
        await page.locator("div[class^='container'] input[accept*='image']").set_input_files(self.image_paths)

        while True:
            try:
                await page.wait_for_url(
                    "**/creator-micro/content/post/image?**",
                    timeout=3000,
                )
                douyin_logger.info(_msg("🥳", "entrei na página de publicação de imagem e texto"))
                break
            except Exception:
                douyin_logger.debug(_msg("🧍", "ainda esperando o envio das imagens concluído"))
                await asyncio.sleep(0.5)

        await asyncio.sleep(1)
        douyin_logger.info(_msg("✍️", "preenchendo título, descrição e hashtags"))
        await self.fill_title_and_description(page, self.title, self.note, self.tags)
        title_len = len(self.title) if self.title else 0
        tags_text = " ".join(f"#{t}" for t in self.tags) if self.tags else ""
        desc_and_tags_len = len(self.note or "") + (len(tags_text) + 2 if self.tags else 0)
        douyin_logger.info(_msg("📝", f"total de caracteres do título: {title_len}, descrição+hashtagstotal de caracteres: {desc_and_tags_len}"))
        douyin_logger.info(_msg("🏷️", f"colei no total {len(self.tags)}  hashtags"))

        if self.bgm:
            await self.select_bgm(page, self.bgm)

        if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        while True:
            try:
                publish_button = page.get_by_role("button", name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()
                await page.wait_for_url(
                    "**/creator-micro/content/manage?enter_from=publish**",
                    timeout=3000,
                )
                douyin_logger.success(_msg("🥳", "post de imagem e texto publicado com sucesso"))
                break
            except Exception:
                douyin_logger.info(_msg("🏃", "publicando o post de imagem e texto"))
                await asyncio.sleep(0.5)

    async def upload(self, playwright: Playwright) -> None:
        douyin_logger.info(_msg("🧍", "conferindo cookie, imagens e horário de publicação"))
        await self.validate_upload_args()
        douyin_logger.info(_msg("🥳", "verificação antes do envio do post concluída"))

        browser = await playwright.chromium.launch(headless=self.headless, channel="chromium", args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            storage_state=f"{self.account_file}",
            permissions=["geolocation"],
        )
        context = await set_init_script(context)

        upload_success = False
        try:
            page = await context.new_page()
            await page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded", timeout=90000)
            douyin_logger.info(_msg("🧭", "indo para a página de publicação de imagem e texto"))
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=90000)

            await self.upload_note_content(page)
            upload_success = True
        finally:
            if upload_success:
                await context.storage_state(path=self.account_file)
                douyin_logger.success(_msg("🥳", "cookie atualização concluída"))
                await asyncio.sleep(2)
            await context.close()
            await browser.close()

    async def douyin_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
