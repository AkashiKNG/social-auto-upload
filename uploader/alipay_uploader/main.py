# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
import json as _json
import os
import re
import time
from pathlib import Path

from playwright.async_api import Page, Playwright, TimeoutError as PWTimeoutError, async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import alipay_logger
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file

ALIPAY_HOME_URL = "https://c.alipay.com/"
ALIPAY_PORTAL_HOME = "https://c.alipay.com/page/portal/home"
# entrada da plataforma de criação: precisa do _appScene=CONTENT&appId=xxx, senão cai na página de criar a conta de vida (signup)
ALIPAY_LIFE_ACCOUNT_URL = "https://c.alipay.com/page/life-account/index?_appScene=CONTENT&appId=2030022469359777"
ALIPAY_POSTS_URL = "https://c.alipay.com/page/content-creation/posts"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _build_login_result(success: bool, status: str, message: str, account_file: str, qrcode: dict | None = None, current_url: str = "") -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return
    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {"headless": headless}
    if LOCAL_CHROME_PATH:
        launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
    return launch_kwargs


def _resolve_account_file(account_file: str | Path) -> str:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return str(path)

    if len(path.parts) == 1:
        return str((Path(BASE_DIR) / "cookies" / "alipay_uploader" / path).resolve())

    return str(path.resolve())


def format_title_with_tags(title: str, tags: list[str], max_length: int = 30) -> str:
    """as etiquetas da conta de vida do Alipay são #tag formato, junto ao fim do título, no mesmo campo.

    corta respeitando as etiquetas: primeiro garante o título inteiro, depois acrescenta etiqueta a etiqueta; o que não couber**descarta a etiqueta inteira**, 
    nunca deixa meia etiqueta nem um `#`.isso evita disparar o Alipay "corte de texto" a janela de sugestões bloqueou a publicação.
    """
    if not tags:
        return title[:max_length]
    result = title
    for tag in tags:
        candidate = result + " #" + tag.strip("#")
        if len(candidate) > max_length:
            break
        result = candidate
    return result


async def _capture_alipay_qr(page: Page, account_file: str, previous_qrcode_path: Path | None = None) -> dict:
    """recorta o QR code seguindo o DOM fixo da tela de login do Alipay (só aceita a aba do QR code + barcode canvas)."""
    login_iframe = page.locator('iframe[title="login"]')
    await login_iframe.first.wait_for(state="attached", timeout=30000)
    frame = page.frame_locator('iframe[title="login"]')

    try:
        await frame.locator("#J-loginMethod-tabs").first.wait_for(state="visible", timeout=15000)
        # força a aba do QR code (se já estava no modo QR code, clicar de novo não faz mal)
        await frame.locator("#J-loginMethod-tabs li[data-status='show_qr']").first.click(timeout=5000)
    except PWTimeoutError:
        # cobre a outra renderização, que já cai direto na área do QR code (sem abas)
        pass

    # só aceita o container do QR code, não os campos de usuário e senha
    await frame.locator("#J-qrcode, #J-barcode-container").first.wait_for(state="visible", timeout=25000)
    await frame.locator("#J-barcode-container canvas.barcode, #J-barcode-container canvas").first.wait_for(state="visible", timeout=25000)

    # a área de usuário e senha fica escondida no modo QR code
    try:
        login_panel = frame.locator("#J-login")
        if await login_panel.count():
            klass = (await login_panel.first.get_attribute("class") or "")
            if "fn-hide" not in klass:
                raise RuntimeError("ainda está no painel de usuário e senha (#J-login não escondido)")
    except RuntimeError:
        raise
    except Exception:
        pass

    qrcode_path = build_login_qrcode_path(account_file)
    qrcode_path.parent.mkdir(parents=True, exist_ok=True)

    qr_canvas = frame.locator("#J-barcode-container canvas.barcode, #J-barcode-container canvas").first
    await qr_canvas.screenshot(path=str(qrcode_path), timeout=15000)

    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            alipay_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {previous_qrcode_path}"))
    alipay_logger.info(_msg("🖼️", f"QR code salvo em: {qrcode_path}"))
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, "aplicativo do Alipay")
    else:
        alipay_logger.warning(_msg("😵", f"o terminal não mostra o QR code inteiro; abra {qrcode_path} escanear o QR code"))
    return {"image_path": str(qrcode_path), "image_data_url": ""}


async def alipay_cookie_gen(account_file, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 100, headless: bool = LOCAL_CHROME_HEADLESS):
    """abre o navegador, o usuário entra na conta de vida do Alipay pelo QR code e o cookie é salvo (espelha o douyin_cookie_gen).

    o png do QR code vai para a pasta cookies (*login_qrcode*.png)serve para mostrar no terminal ou avisar onde está; qrcode_callback é opcional (por exemplo, avisa o Feishu quando precisa entrar de novo).
    headless=False também dá para escanear direto na janela que abriu.
    devolve o dicionário do _build_login_result.
    """
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)
    qrcode_path = None
    result = _build_login_result(False, "failed", "falha no login do Alipay", account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        try:
            page = await context.new_page()
            # atenção: não dá para usar set_init_script(stealth) —— verificação realçãoo modo furtivo impede a injeção do iframe de login do Alipay
            # entra primeiro numa página protegida: sem sessão, a janela de login aparece (iframe[title="login"], injeção assíncrona, cerca de 2~4s)
            await page.goto(ALIPAY_PORTAL_HOME, timeout=60000, wait_until="domcontentloaded")
            if headless:
                alipay_logger.info(_msg("🧍", "login sem janela: o QR code virou imagem; escaneie pelo terminal ou abra o arquivo (ou é enviado ao Feishu pelo processo de publicação)"))
            else:
                alipay_logger.info(_msg("🧍", "entre na conta de vida do Alipay pelo QR code, na janela aberta (loginconcluídonão feche o navegador na mão depois disso)"))

            # espera o iframe de login aparecer
            login_iframe = page.locator('iframe[title="login"]')
            for _ in range(30):
                try:
                    if await login_iframe.count():
                        break
                except Exception:
                    pass
                await page.wait_for_timeout(1000)
            else:
                await context.close()
                await browser.close()
                return _build_login_result(False, "timeout", "tempo esgotado esperando a janela de login (30s), desistindo de salvar", account_file, current_url=page.url)

            # captura o QR code (sem janela, vai para o terminal/Feishu; com janela, guarda uma cópia — falhar aqui não é grave)
            qrcode_info = await _capture_alipay_qr(page, account_file)
            qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None
            await _emit_qrcode_callback(qrcode_callback, qrcode_info)
            alipay_logger.info(_msg("🧍", "escaneie o QR code; esperando o login terminar"))

            # fica verificando até o login terminar: login iframe sumiu (logindando certo, a página de auth sai sozinha)
            for _i in range(max_checks):  # espera no máximo 3~5 minutos
                if await _is_alipay_login_completed(page, login_iframe):
                    alipay_logger.info(_msg("🥳", f"QR code lido: já estou na página de quem entrou: {page.url}"))
                    result = _build_login_result(True, "success", "login por QR code do Alipay concluído", account_file, qrcode_info, page.url)
                    break
                await page.wait_for_timeout(poll_interval * 1000)
            else:
                result = _build_login_result(False, "timeout", "tempo esgotado esperando o login por QR code do Alipay", account_file, qrcode_info, page.url)

            if result["success"]:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                # loginno fim, confere rapidamente se o arquivo de cookie tem conteúdo
                try:
                    _d = _json.load(open(account_file))
                    _has_cookie = any(c.get("value") for c in _d.get("cookies", []))
                    if not _has_cookie:
                        result = _build_login_result(False, "cookie_invalid", "o fluxo do QR code do Alipay terminou, mas o cookie ficou vazio", account_file, qrcode_info, page.url)
                except Exception as _e:
                    alipay_logger.warning(_msg("⚠️", f"cookie erro ao validar o arquivo (ignorado: tratando como sucesso): {_e}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                alipay_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {qrcode_path}"))
            if not result["success"]:
                alipay_logger.error(_msg("😢", f"falha no login: {result['message']}"))
            await context.close()
            await browser.close()
    return result


async def _is_alipay_login_completed(page: Page, login_iframe) -> bool:
    # logindeu certo quando o iframe de login some (logindando certo, a página de auth sai sozinha), e a URL voltar para c.alipay.com, que não é a tela de login
    try:
        if await login_iframe.count() != 0:
            return False
        url = page.url
        if url.startswith("https://c.alipay.com/") and "login" not in url.lower():
            return True
    except Exception:
        return False
    return False


async def cookie_auth(account_file):
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            page = await context.new_page()
            await page.goto(ALIPAY_LIFE_ACCOUNT_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # logino login troca a página inteira para auth.alipay.com; só vale se continuar em c.alipay.com e fora da tela de loginálido
            url = page.url
            if url.startswith("https://auth.alipay.com/") or "login" in url.lower():
                alipay_logger.info(_msg("🥹", "cookie expirado (redirecionado para a página de login)"))
                return False
            if await page.locator('iframe[title="login"]').count():
                alipay_logger.info(_msg("🥹", "cookie expirado (a janela de login apareceu)"))
                return False

            alipay_logger.success(_msg("🥳", "cookie válido"))
            return True
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"cookie erro na verificação: tratando como expirado: {exc}"))
            return False
        finally:
            await browser.close()


async def alipay_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie arquivo inexistente ou expirado", account_file)
            return result if return_detail else False
        alipay_logger.info(_msg("🥹", "cookie arquivo inexistente ou expirado: abrindo o navegador para você escanear o QR code"))
        result = await alipay_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie válido", account_file)
    return result if return_detail else True


class AlipayVideo(BaseVideoUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        account_file,
        desc: str | None = None,
        thumbnail_path: str | None = None,
        collection_name: str | None = None,
        debug: bool = True,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.account_file = _resolve_account_file(account_file)
        self.desc = desc or ""
        self.thumbnail_path = thumbnail_path
        self.collection_name = collection_name
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH
        self.max_title_length = 30

    async def validate_upload_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookiearquivo inexistente; conclua antes o ídologin na conta de vida do Alipay: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookiearquivo expirado; conclua antes o ídologin na conta de vida do Alipay: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("no modo vídeo, o título é obrigatório")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_path:
            self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def open_upload_page(self, page: Page) -> None:
        # entra na página inicial da plataforma de criação e clica em "publicar vídeo" cartão (JS navegação)entra no v curtoídeoformulário de publicação
        await page.goto(ALIPAY_LIFE_ACCOUNT_URL, timeout=120000, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        publish_entry = page.locator('a:has-text("发布视频推荐分辨率720p及以上，建议1080p")').first
        try:
            await publish_entry.wait_for(state="visible", timeout=30000)
            await publish_entry.click()
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"falha ao clicar na entrada de publicar vídeo: {exc}"))
            raise

        await page.wait_for_url("**/content-creation/publish/short-video**", timeout=60000)

    async def upload_video_file(self, page: Page, file_path: str) -> None:
        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=30000)
        await file_input.set_input_files(file_path)
        alipay_logger.info(_msg("🏃", f"arquivo de vídeo escolhido: {file_path}"))

    async def fill_title_and_tags(self, page: Page) -> None:
        title_field = page.get_by_placeholder("一个好的标题，能获得更多人的喜欢哦").first
        await title_field.wait_for(state="visible", timeout=30000)
        value = format_title_with_tags(self.title, self.tags, max_length=self.max_title_length)
        await title_field.fill(value)
        alipay_logger.info(_msg("🏷️", f"título preenchido (com as etiquetas, {len(value)} caracteres): {value}"))

    async def fill_description(self, page: Page) -> None:
        if not self.desc:
            return
        desc_field = page.get_by_placeholder("填写作品描述，让你的作品更容易被看到").first
        await desc_field.fill(self.desc)
        alipay_logger.info(_msg("🏷️", f"descrição da obraçãopreenchido: {self.desc[:40]}"))

    async def upload_thumbnail(self, page: Page) -> None:
        if not self.thumbnail_path:
            return
        try:
            # 1) no formulário, clica em "enviar capa" para abrir a janela de recorte
            cover_el = page.get_by_text("上传封面", exact=True).first
            await cover_el.scroll_into_view_if_needed()
            await cover_el.click(timeout=10000)
            await page.wait_for_timeout(2000)

            modal_body = page.locator(".antd5-modal-body").last

            # 2) a janela, na primeira vez, é "recorta e envia a capa" duas entradas; clica "envia a capa" abre a área de envio de imagens
            inner = modal_body.get_by_text("上传封面", exact=True).first
            if await inner.count():
                await inner.click(timeout=8000)
                await page.wait_for_timeout(1500)

            # 3) clica em "enviar imagem" e abre o seletor de arquivos
            upload_img_btn = modal_body.get_by_role("button", name="上传图片").first
            await upload_img_btn.wait_for(state="visible", timeout=10000)
            await upload_img_btn.click()
            await page.wait_for_timeout(1500)

            # 4) coloca a imagem no campo de arquivo que apareceu
            img_input = page.locator('input[type="file"][accept*="jpg"], input[type="file"][accept*="png"]').first
            await img_input.wait_for(state="attached", timeout=10000)
            await img_input.set_input_files(self.thumbnail_path)
            await page.wait_for_timeout(3000)

            # 5) na janela de corte, clica "concluído"
            done_btn = page.get_by_role("button", name="完 成").first
            if not await done_btn.count():
                done_btn = page.get_by_role("button", name="完成").first
            await done_btn.wait_for(state="visible", timeout=15000)
            await done_btn.click()
            await page.wait_for_timeout(800)
            alipay_logger.success(_msg("🖼️", "capa enviada"))
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"falha ao enviar a capa, pula e continua: {exc}"))

    async def apply_collection(self, page: Page) -> None:
        if not self.collection_name:
            return
        try:
            # antd5-select: clicao botão que abre a lista de coletâneas (compilation input  container pai), abre as opções
            compilation = page.locator('input[id*="_compilationInfo"]').first
            await compilation.scroll_into_view_if_needed()
            select = compilation.locator("xpath=../../..").first
            if not await select.count():
                select = page.locator(
                    '.antd5-select:has(.antd5-select-selection-placeholder)'
                ).first
            await select.click(timeout=8000)
            await page.wait_for_timeout(2000)

            # procura o nome exato da coletânea na lista; sem achar, não agrupa (depois que o usuário criar a coletânea à mão, ela é selecionada sozinha)
            options = page.locator('[role="option"]')
            target = options.filter(has_text=self.collection_name).first
            if await target.count():
                try:
                    await target.click(timeout=5000, force=True)
                except Exception:
                    await target.scroll_into_view_if_needed()
                    await target.click(timeout=5000)
                await page.wait_for_timeout(800)
                alipay_logger.success(_msg("🥳", f"coletânea escolhida: {self.collection_name}"))
                return

            alipay_logger.warning(_msg("😵", f"a conta não tem a coletânea '{self.collection_name}': seguindo sem agrupar"))
            await page.keyboard.press("Escape")
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"não consegui escolher a coletânea; sigo a publicação sem ela: {exc}"))

    async def check_ai_label(self, page: Page) -> None:
        # a declaração do autor é um grupo de radio (padrão "o conteúdo não precisa de marcação" NO_STATEMENT), usa radio.check() selecionado "conteúdo gerado por IA"(A_AG3)
        ai_label = page.locator('label.antd5-radio-wrapper', has_text="内容由AI生成").first
        try:
            if await ai_label.count():
                radio = ai_label.locator('input[type="radio"]').first
                await radio.scroll_into_view_if_needed()
                await radio.check(timeout=5000)
                await page.wait_for_timeout(500)
                alipay_logger.success(_msg("🏷️", "marquei o conteúdo como gerado por IA"))
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"não consegui marcar o conteúdo como gerado por IA: {exc}"))

    async def wait_for_upload_complete(self, page: Page, timeout: int = 1800) -> None:
        # espera "confirmarpublicar" botãofica clicável (envio de vídeo+conversão concluídaído)
        publish_btn = page.get_by_role("button", name="确认发布").first
        start = time.monotonic()
        while True:
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"espera envio de vídeo/tempo esgotado na conversão do vídeo (>{timeout}s), confirmarbotão de publicarsegue indisponível")
            try:
                if not await publish_btn.count():
                    await asyncio.sleep(2)
                    continue
                if await publish_btn.is_disabled():
                    alipay_logger.info(_msg("🏃", "enviando/convertendo o vídeo..."))
                    await asyncio.sleep(2)
                    continue
                alipay_logger.success(_msg("🥳", "envio do vídeo concluído"))
                return
            except Exception:
                alipay_logger.info(_msg("🏃", "enviando/convertendo o vídeo..."))
                await asyncio.sleep(2)

    async def submit_publish(self, page: Page) -> None:
        publish_btn = page.get_by_role("button", name="确认发布").first
        await publish_btn.wait_for(state="visible", timeout=30000)
        # em algumas contas o clique não leva direto para posts: é preciso olhar também a mensagem de sucesso
        if await publish_btn.is_disabled():
            raise RuntimeError("confirmarbotão de publicarcontinua sem poder clicar: não dá para enviar")

        # captura só as requisições da fase de envio, para investigar quando falha
        net_events: list[tuple[str, str, int | None, str]] = []
        req_events: list[tuple[str, str, str]] = []
        net_tasks: list[asyncio.Task] = []

        async def _collect_click_diag(tag: str):
            try:
                diag = await page.evaluate(
                    """
                    () => {
                      const btns = Array.from(document.querySelectorAll('button')).filter(b => (b.innerText || '').includes('确认发布'));
                      const confirmButtons = btns.map((b, i) => {
                        const r = b.getBoundingClientRect();
                        const cx = r.left + r.width / 2;
                        const cy = r.top + r.height / 2;
                        const topEl = document.elementFromPoint(cx, cy);
                        return {
                          i,
                          text: (b.innerText || '').trim(),
                          disabled: !!b.disabled,
                          ariaDisabled: b.getAttribute('aria-disabled'),
                          className: b.className,
                          rect: { x: r.x, y: r.y, w: r.width, h: r.height },
                          topElement: topEl ? `${topEl.tagName}.${topEl.className || ''}` : null,
                        };
                      });

                      const visibleModals = Array.from(document.querySelectorAll('.antd5-modal-wrap, .antd5-message, .antd5-notification')).filter(el => {
                        const st = window.getComputedStyle(el);
                        const r = el.getBoundingClientRect();
                        return st.display !== 'none' && st.visibility !== 'hidden' && r.width > 0 && r.height > 0;
                      }).slice(0, 5).map(el => ({
                        cls: el.className,
                        text: (el.textContent || '').trim().slice(0, 120),
                      }));

                      const errorHints = Array.from(document.querySelectorAll('.antd5-form-item-explain-error, .ant-form-item-explain-error, [class*="error"]')).map(el => (el.textContent || '').trim()).filter(Boolean).slice(0, 8);

                      return {
                        url: location.href,
                        title: document.title,
                        readyState: document.readyState,
                        confirmButtons,
                        visibleModals,
                        errorHints,
                        activeElement: document.activeElement ? `${document.activeElement.tagName}.${document.activeElement.className || ''}` : null,
                      };
                    }
                    """
                )
                alipay_logger.info(_msg("🔍", f"{tag}: {_json.dumps(diag, ensure_ascii=False)[:1000]}"))
            except Exception as exc:
                alipay_logger.warning(_msg("🔍", f"{tag}: não consegui coletar o diagnóstico: {exc}"))

        def _watch_url(url: str) -> bool:
            u = (url or "").lower()
            return any(k in u for k in (
                "publish",
                "publishshortvideo",
                "content-creation",
                "posts",
                "submit",
                "short-video",
                "captcha.alipay.com/api/v1/captcha/verify",
            ))

        async def _collect_response(resp):
            try:
                if not _watch_url(resp.url):
                    return
                status = resp.status
                text = ""
                req_body = ""
                try:
                    req_body = (resp.request.post_data or "").strip().replace("\n", " ")
                except Exception:
                    req_body = ""
                ct = (resp.headers or {}).get("content-type", "").lower()
                if "json" in ct or "text" in ct:
                    try:
                        text = (await resp.text() or "").strip().replace("\n", " ")
                    except Exception:
                        text = ""
                merged = f"req={req_body[:180]} resp={text[:180]}".strip()
                net_events.append((resp.request.method, resp.url, status, merged[:380]))
            except Exception:
                pass

        def _on_response(resp):
            try:
                net_tasks.append(asyncio.create_task(_collect_response(resp)))
            except Exception:
                pass

        def _on_request(req):
            try:
                if not _watch_url(req.url):
                    return
                body = (req.post_data or "").strip().replace("\n", " ")
                req_events.append((req.method, req.url, body[:220]))
            except Exception:
                pass

        page.on("response", _on_response)
        page.on("request", _on_request)
        async def _dismiss_quality_modal() -> bool:
            """Clica em confirmar publicação. Depois disso o Alipay pode abrir a janela de qualidade com N sugestões (corte da capa,
            corte do título etc.), bloqueia o envio de verdade e estoura os 90 s. Na janela "continua a publicação" é o que libera,
            "volta e troca" mesmo sendo o botão principalãoo estilo volta ao estado de edição: é preciso clicar pelo texto "continua a publicação".
            devolve se clicou "continua a publicação"."""
            try:
                btn = page.locator(
                    '.antd5-modal-wrap button:has-text("继续发布"), '
                    '.antd5-modal button:has-text("继续发布")'
                ).first
                if await btn.count() and await btn.is_visible():
                    await btn.click(timeout=3000)
                    alipay_logger.info(_msg("✅", "cliquei em continuar a publicação na janela de sugestões: envio liberado"))
                    await page.wait_for_timeout(500)
                    return True
            except Exception as exc:
                alipay_logger.warning(_msg("😵", f"não consegui clicar em continuar a publicação: {exc}"))
            return False

        await _collect_click_diag("antes do clique")
        await publish_btn.click()
        await page.wait_for_timeout(600)
        await _collect_click_diag("depois do primeiro clique")
        # o primeiro clique pode abrir a janela de sugestões que bloqueia o envio; deixa passar uma vez
        await _dismiss_quality_modal()

        start = time.monotonic()
        timeout = 90
        success_toast = page.locator('.antd5-message-notice-content:has-text("发布成功"), .antd5-message-notice-content:has-text("提交成功"), .antd5-message-notice-content:has-text("提交审核"), .antd5-message-notice-content:has-text("审核中")').first
        fail_toast = page.locator('.antd5-message-notice-content:has-text("发布失败"), .antd5-message-notice-content:has-text("提交失败"), .antd5-message-notice-content:has-text("请稍后重试")').first

        retried_after_aigc = False
        submit_click_retries = 0
        last_click_ts = start
        try:
            while time.monotonic() - start <= timeout:
                if "/content-creation/posts" in page.url:
                    alipay_logger.success(_msg("🥳", "vídeo publicado"))
                    return

                # a janela de sugestões pode demorar e bloquear o envio a qualquer momento: assim que aparecer, clica "continua a publicação" liberar
                await _dismiss_quality_modal()

                # quando cai no pré-processamento de IA, a página costuma ficar na publicação: é preciso clicar em confirmar mais uma vez para enviar de verdade
                try:
                    saw_aigc_done = any(
                        ("querylooptask" in u.lower() and '"done":true' in (b or "").lower())
                        for _, u, _, b in net_events
                    )
                    if saw_aigc_done and not retried_after_aigc:
                        if await publish_btn.count() and not await publish_btn.is_disabled():
                            await publish_btn.click()
                            retried_after_aigc = True
                            alipay_logger.info(_msg("🔁", "pré-processamento de IA concluído, cliquei em confirmar publicação pela segunda vez"))
                            await page.wait_for_timeout(500)
                            await _collect_click_diag("AIGCdepois do segundo clique")
                except Exception:
                    pass

                # critério principal: precisa aparecer pelo menos uma requisição captcha verify / publishShortVideo
                saw_captcha_verify = any("captcha.alipay.com/api/v1/captcha/verify" in u.lower() for _, u, _, _ in net_events)
                saw_publish_submit = any("publishshortvideo.json" in u.lower() for _, u, _, _ in net_events)
                no_submit_signal = not (saw_captcha_verify or saw_publish_submit)
                if no_submit_signal and submit_click_retries < 3 and (time.monotonic() - last_click_ts) >= 8:
                    try:
                        if await publish_btn.count() and not await publish_btn.is_disabled():
                            await publish_btn.click()
                            submit_click_retries += 1
                            last_click_ts = time.monotonic()
                            alipay_logger.info(_msg("🔁", f"não vi o sinal da requisição de envio; clicando de novo em confirmar publicação ({submit_click_retries}/3)"))
                            await page.wait_for_timeout(500)
                            await _collect_click_diag(f"depois de clicar de novo#{submit_click_retries}")
                    except Exception:
                        pass

                try:
                    if await success_toast.count() and await success_toast.is_visible():
                        alipay_logger.success(_msg("🥳", "vídeo publicado (toast encontrado)"))
                        return
                except Exception:
                    pass
                try:
                    if await fail_toast.count() and await fail_toast.is_visible():
                        raise RuntimeError("falha na publicação (a página respondeu com erro)")
                except RuntimeError:
                    raise
                except Exception:
                    pass
                await page.wait_for_timeout(1000)

            raise RuntimeError(
                f"publiquei, mas não vi o sinal de sucesso (90s), endereço atual: {page.url}"
            )
        finally:
            page.remove_listener("response", _on_response)
            page.remove_listener("request", _on_request)
            if net_tasks:
                try:
                    await asyncio.wait(net_tasks, timeout=3)
                except Exception:
                    pass
            if req_events:
                alipay_logger.info(_msg("🧾", f"{len(req_events)} requisições na fase de envio (as 10 mais recentes)"))
                for m, u, b in req_events[-10:]:
                    alipay_logger.info(_msg("🧾", f"REQ {m} {u} | {b}"))
            if net_events:
                alipay_logger.info(_msg("🧾", f"{len(net_events)} eventos de rede na fase de envio (os 10 mais recentes)"))
                for m, u, s, b in net_events[-10:]:
                    alipay_logger.info(_msg("🧾", f"{m} {s} {u} | {b}"))

    async def upload(self, playwright: Playwright) -> None:
        alipay_logger.info(_msg("🧍", "confere o cookie e o arquivo de vídeo"))
        await self.validate_upload_args()
        alipay_logger.info(_msg("🥳", "verificação antes do envio concluída"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)
        await context.grant_permissions(["geolocation"])
        # atenção: não dá para usar set_init_script(stealth) —— bloquearia a plataforma de criação do Alipay(qiankun mini aplicativo)renderização

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            alipay_logger.info(_msg("🏃", f"começando o envio do vídeo: {self.title}"))

            await self.upload_video_file(page, self.file_path)
            await self.fill_title_and_tags(page)
            await self.fill_description(page)
            await self.upload_thumbnail(page)
            await self.apply_collection(page)
            await self.check_ai_label(page)
            await self.wait_for_upload_complete(page)
            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            alipay_logger.success(_msg("🥳", "cookie atualização concluída"))
        finally:
            await context.close()
            await browser.close()

    async def alipay_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.alipay_upload_video()
