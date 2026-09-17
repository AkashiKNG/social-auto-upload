# -*- coding: utf-8 -*-
"""Weibo envio de vídeo + login por QR code.

o que faz: 
  - weibo_cookie_gen: headless login por QR code (QR code do passport do Weibo)
  - cookie_auth: confere se o cookie ainda vale
  - weibo_setup: entrada única (verifica a sessão e, se preciso, faz login)
  - WeiBoVideo: classe de envio de vídeo

adaptado de uma gravação do playwright codegen.
página de entrada: https://weibo.com/
página de publicação: clica na inicial "vídeo" a entrada abre outra janela (página de publicação do vídeo)
"""
from __future__ import annotations

import asyncio
import inspect
import os
import re
import time
from pathlib import Path

from playwright.async_api import Page, Playwright, TimeoutError as PWTimeoutError, async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.log import weibo_logger
from utils.login_qrcode import build_login_qrcode_path, remove_qrcode_file


WEIBO_HOME_URL = "https://weibo.com/"
WEIBO_LOGIN_URL = "https://weibo.com/newlogin?tabtype=weibo&gid=102803&openLoginLayer=0&url=https://weibo.com/"
# tela de login por QR code do passport do Weibo (vai direto para cá, sem o pop-up da página inicial)
WEIBO_PASSPORT_QR_URL = "https://passport.weibo.com/sso/signin?entry=miniblog&source=miniblog&url=https%3A%2F%2Fweibo.com%2F"

# seletor do QR code do passport do Weibo (login por QR codea imagem do QR code da página)
QR_SELECTOR = 'img[src*="qrcode"], img[src*="qr"]'


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
        return str((Path(BASE_DIR) / "cookies" / "weibo_uploader" / path).resolve())
    return str(path.resolve())


async def _grab_qr(page: Page, account_file: str) -> dict:
    """recorta o QR code da tela de login do passport do Weibo.

    o QR code da tela de login do passport do Weibo pode ser img ou canvas; tentamos vários seletores.
    """
    # vários seletores possíveis para o QR code (passport a estrutura da página pode mudar)
    selectors = [
        'img[src*="qrcode"]',
        'img[src*="qr"]',
        'img[node-type="qrcode_img"]',
        '.qrcode img',
        'canvas',  # algumas versões desenham o QR code num canvas
    ]

    qr = None
    for sel in selectors:
        loc = page.locator(sel).first
        if await loc.count():
            qr = loc
            weibo_logger.info(_msg("🔍", f"achei o elemento do QR code: {sel}"))
            break

    if not qr:
        # última reserva: recorta o centro da página inteira
        weibo_logger.warning(_msg("⚠️", "não achei o elemento do QR code; tirando um print"))
        qrcode_path = build_login_qrcode_path(account_file)
        qrcode_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(qrcode_path))
        weibo_logger.info(_msg("🖼️", f"print da página salvo em: {qrcode_path}"))
        return {"image_path": str(qrcode_path), "image_data_url": ""}

    await qr.wait_for(state="visible", timeout=30000)

    qrcode_path = build_login_qrcode_path(account_file)
    qrcode_path.parent.mkdir(parents=True, exist_ok=True)

    # tenta primeiro baixar a URL da imagem em alta (img elemento)
    tag = await qr.evaluate("el => el.tagName.toLowerCase()")
    if tag == "img":
        src = await qr.get_attribute("src")
        if src and src.startswith("http"):
            try:
                resp = await page.context.request.get(src)
                qrcode_path.write_bytes(await resp.body())
            except Exception:
                await qr.screenshot(path=str(qrcode_path))
        else:
            await qr.screenshot(path=str(qrcode_path))
    else:
        # canvas ou outro elemento: tira o print direto
        await qr.screenshot(path=str(qrcode_path))

    weibo_logger.info(_msg("🖼️", f"QR code salvo em: {qrcode_path}"))
    # o terminal não desenha o QR code, só mostra onde está o arquivo; abra a imagem e escaneie pelo aplicativo do Weibo
    print(f"abra {qrcode_path}, escaneie este QR code pelo aplicativo do Weibo")
    return {"image_path": str(qrcode_path), "image_data_url": ""}


async def _is_login_completed(page: Page) -> bool:
    """vê se o login do Weibo terminouído: URL volta à página inicial e aparecem a foto do perfil e o feed."""
    url = page.url
    # ainda na página de login/passport
    if "newlogin" in url or "passport" in url:
        return False
    # vê se voltou à página inicial já autenticado
    if "weibo.com" in url and "login" not in url:
        # o feed ou a foto do perfil aparecendo, o login deu certo
        has_user = await page.locator('[class*="Nav_avatar"], [class*="woo-avatar"]').count()
        if has_user:
            return True
        # cookies ter o SUB quer dizer que o login deu certo
        cookies = await page.context.cookies()
        if any(c.get("name") == "SUB" for c in cookies):
            return True
    return False


async def weibo_cookie_gen(account_file, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 120, headless: bool = LOCAL_CHROME_HEADLESS):
    """login por QR code no Weibo, com ou sem janela, salvando o cookie.

    fluxo: abre direto a tela de QR code do passport do Weibo → recorta o QR code → esperando a leitura do QR code (volta para a página inicial)→ salva o storage_state.
    devolve o dicionário padrão do resultado de login.
    """
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)
    qrcode_path = None
    result = _build_login_result(False, "failed", "falha no login do Weibo", account_file)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        try:
            page = await context.new_page()
            # vai direto para a tela de QR code do passport, sem passar pela inicial e seu "login" botão (headless fica invisível)
            await page.goto(WEIBO_PASSPORT_QR_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            if headless:
                weibo_logger.info(_msg("🧍", "login sem janela: o QR code virou imagem; escaneie pelo aplicativo do Weibo"))
            else:
                weibo_logger.info(_msg("🧍", "entre no Weibo pelo QR code na janela aberta"))

            # recorta o QR code
            qrcode_info = await _grab_qr(page, account_file)
            qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None
            await _emit_qrcode_callback(qrcode_callback, qrcode_info)

            weibo_logger.info(_msg("🧍", "escaneie o QR code; esperando o login terminar"))

            # fica verificando até o login terminar (a página sai do passport ou aparece o cookie de sessão)
            for _ in range(max_checks):
                current_url = page.url
                # sair da página do passport quer dizer que o login deu certo
                if "passport" not in current_url and "weibo.com" in current_url:
                    weibo_logger.info(_msg("🥳", f"escanear o QR codedeu certo, indo para: {current_url}"))
                    result = _build_login_result(True, "success", "login por QR code do Weibo concluído", account_file, qrcode_info, current_url)
                    break
                # procura o SUB nos cookies (às vezes a página não navega, mas o cookie já foi gravado)
                cookies = await context.cookies()
                if any(c.get("name") == "SUB" and c.get("value") for c in cookies):
                    weibo_logger.info(_msg("🥳", f"escanear o QR codedeu certo (achei o cookie SUB), atual: {current_url}"))
                    result = _build_login_result(True, "success", "login por QR code do Weibo concluído", account_file, qrcode_info, current_url)
                    break
                await page.wait_for_timeout(poll_interval * 1000)
            else:
                result = _build_login_result(False, "timeout", "tempo esgotado esperando o login por QR code do Weibo", account_file, qrcode_info, page.url)

            if result["success"]:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                weibo_logger.success(_msg("🥳", f"cookie salvo: {account_file}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                weibo_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {qrcode_path}"))
            if not result["success"]:
                weibo_logger.error(_msg("😢", f"falha no login: {result['message']}"))
            await context.close()
            await browser.close()
    return result


async def cookie_auth(account_file):
    """verificaçãoo cookie do Weibo ainda é válido.abre a página inicial e vê se pede login."""
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            page = await context.new_page()
            await page.goto(WEIBO_HOME_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # vê se houve redirecionamento para a página de login
            if "newlogin" in page.url or "passport" in page.url:
                weibo_logger.info(_msg("🥹", "cookie expirado (redirecionado para a página de login)"))
                return False

            # vê se existe "login" botão (sem sessão, aparece)
            login_btn = page.get_by_text("登录", exact=True).first
            if await login_btn.count() and await login_btn.is_visible():
                weibo_logger.info(_msg("🥹", "cookie expirado (o botão de login apareceuão)"))
                return False

            weibo_logger.success(_msg("🥳", "cookie válido"))
            return True
        except Exception as exc:
            weibo_logger.warning(_msg("😵", f"cookie erro na verificação: tratando como expirado: {exc}"))
            return False
        finally:
            await browser.close()


async def weibo_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    """entrada única: confere o cookie → se estiver inválido e handle=True dispara o login por QR code."""
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie arquivo inexistente ou expirado", account_file)
            return result if return_detail else False
        weibo_logger.info(_msg("🥹", "cookie arquivo inexistente ou expirado: abrindo o navegador para você escanear o QR code"))
        result = await weibo_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie válido", account_file)
    return result if return_detail else True


class WeiBoVideo(BaseVideoUploader):
    """Weibo envio de vídeo.

    fluxo: abre a página inicial → clica na entrada "vídeo", que abre a janela de publicação → envia o arquivo de vídeo →
         espera o envio terminarído → preenche o título → envia a capa → marca conteúdo derivado + AIdeclaração →
         preenche a descrição → clicapublicar.
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
        collection_name: str | None = None,
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
        self.collection_name = collection_name
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH
        self.max_title_length = 30

    async def validate_upload_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookiearquivo inexistente; conclua antes o ídologin do Weibo: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookiearquivo expirado; conclua antes o ídologin do Weibo: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("o título do vídeo não pode ficar vazio")
        if not self.thumbnail_path:
            raise ValueError("Weibo vídeoa publicação exige uma capa (--thumbnail)")
        self.file_path = str(self.validate_video_file(self.file_path))
        self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))
        # arquivo da capa < 5MB
        thumb_size = Path(self.thumbnail_path).stat().st_size
        if thumb_size > 5 * 1024 * 1024:
            raise ValueError(f"arquivo de capa grande demais ({thumb_size / 1024 / 1024:.1f}MB), o Weibo exige < 5MB")

    async def upload(self, playwright: Playwright) -> None:
        weibo_logger.info(_msg("🧍", "confere o cookie e o arquivo de vídeo"))
        await self.validate_upload_args()
        weibo_logger.info(_msg("🥳", "verificação antes do envio concluída"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(
            storage_state=self.account_file,
            viewport={"width": 1280, "height": 2000},  # janela alta, para o botão de publicarespera na área visível
        )

        try:
            page = await context.new_page()
            await page.goto(WEIBO_HOME_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            weibo_logger.info(_msg("🏃", f"começando o envio do vídeo: {self.title}"))

            # 1) clicapágina inicial "vídeo" entrada: abre a janela de publicação (popup)
            publish_page = await self._open_video_publish_page(page)

            # 2) envia o arquivo de vídeo
            await self._upload_video_file(publish_page)

            # 3) espera envio do vídeo realmente concluído ("envio concluído" bloco visível)
            await self._wait_upload_complete(publish_page)

            # 4) tipo = conteúdo derivado (obrigatório)
            await self._select_type(publish_page)

            # 5) declaração de conteúdo = contém conteúdo gerado por IA (obrigatório)
            await self._select_declaration(publish_page)

            # 6) preenche o título (obrigatório)
            await self._fill_title(publish_page)

            # 7) envia a capa (obrigatório)
            await self._upload_thumbnail(publish_page)

            # 8) coletânea: usa uma existente ou cria (quando há collection_name configurado)
            if self.collection_name:
                await self._apply_collection(publish_page)

            # 9) preenche a descrição (com as etiquetas)
            await self._fill_description(publish_page)

            # 10) clicapublica e confere se deu certo
            await self._submit_publish(publish_page)

            # salva o cookie
            await context.storage_state(path=self.account_file)
            weibo_logger.success(_msg("🥳", "cookie atualização concluída"))
        finally:
            await context.close()
            await browser.close()

    async def _open_video_publish_page(self, page: Page) -> Page:
        """clicapágina inicial" vídeo " entrada: espera o pop-up página de publicação do vídeo."""
        async with page.expect_popup(timeout=30000) as popup_info:
            # 录制脚本：page.locator("span").filter(has_text="视频").click()
            video_btn = page.locator("span").filter(has_text="视频").first
            await video_btn.wait_for(state="visible", timeout=15000)
            await video_btn.click()
        publish_page = await popup_info.value
        await publish_page.wait_for_timeout(3000)
        weibo_logger.info(_msg("🏃", "abri o página de publicação do vídeo"))
        return publish_page

    async def _upload_video_file(self, page: Page) -> None:
        """clica" enviar vídeo " botãoe define o arquivo."""
        # 录制脚本：page2.get_by_role("button", name="上传视频").click()
        upload_btn = page.get_by_role("button", name="上传视频")
        await upload_btn.wait_for(state="visible", timeout=15000)

        # define o arquivo pelo seletor de arquivos
        async with page.expect_file_chooser(timeout=10000) as fc_info:
            await upload_btn.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)
        weibo_logger.info(_msg("🏃", f"arquivo de vídeo escolhido: {self.file_path}"))

    async def _wait_upload_complete(self, page: Page, timeout: int = 900) -> None:
        """espera envio do vídeo realmente concluído.

        DOM real: a área de envio tem três elementos lado a lado `_info` lado a lado (enviando / pausado / envio concluído), e o que não vale
        o estado usa `display:none` escondidos; só o do estado atual fica visível:
          - enviando: `<span>enviando</span>` + `269.61MB/269.61MB`
          - envio concluído: `<i class="woo-font woo-font--check">` + `<span>envio concluído</span>`
        o critério é o bloco "envio concluído" **ficar visível** (os três textos ficam sempre no DOM: existir ou não existir não serve de critério).
        """
        start = time.monotonic()
        done = page.locator('div:has(> i.woo-font--check) span:text-is("上传完成")').first
        uploading = page.locator('span:text-is("上传中")').first
        last_log = 0.0
        while True:
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"tempo esgotado no envio do vídeo (>{timeout}s)")

            body = ""
            try:
                body = await page.inner_text("body")
            except Exception:
                pass
            if "falha no envio" in body:
                raise RuntimeError("falha no envio do vídeo")

            try:
                if await done.is_visible():
                    weibo_logger.success(_msg("🥳", "envio do vídeo concluído ('envio concluído' visível)"))
                    return
            except Exception:
                pass

            if time.monotonic() - last_log > 5:
                try:
                    if await uploading.is_visible():
                        # o "上传中" é o texto da própria página: não traduzir
                        m = re.search(r"上传中[\s\S]{0,60}?([\d.]+)\s*MB\s*/\s*([\d.]+)\s*MB", body)
                        if m:
                            weibo_logger.info(_msg("🏃", f"enviando {m.group(1)}/{m.group(2)}MB"))
                        else:
                            weibo_logger.info(_msg("🏃", "enviando…"))
                except Exception:
                    pass
                last_log = time.monotonic()
            await asyncio.sleep(2)

    async def _fill_title(self, page: Page) -> None:
        """preenche o título (no máximo 30 caracteres)."""
        title_field = page.get_by_placeholder("填写标题（0～30个字）")
        await title_field.wait_for(state="visible", timeout=15000)
        title = self.title[:self.max_title_length]
        await title_field.click()
        await title_field.fill(title)
        weibo_logger.info(_msg("🏷️", f"título preenchido: {title}"))

    async def _upload_thumbnail(self, page: Page) -> None:
        """envia a capa (obrigatório).

        DOM real e armadilhas:
          - no formulário principal, `<a>envia a capa</a>` → abre a camada "editar capa" `_layer_1mhd8_153` (dentro dela há
            `input[type=file]._file_1mhd8_65`, dá para usar set_input_files direto).
          - **armadilha importante**: escolhida a imagem, a capa passa por**corte no servidor**, nesse tempo a camada mostra " cortando / processando, aguarde…", 
            "concluído" botãoclicar agora não adianta; e "editar capa" com a camada aberta, o Weibo deixa**camada do formulário principal
            `_layer_19x8d_246` muda para display:none** → o botão de coletânea e o de publicar que vêm depoisãotodos com tamanho zero: não dá para clicar.
          - por isso é preciso esperar o corte terminar (o cropper gera a imagem blob e some o texto de "processando") → clica em "concluído" →
            **confirmareditar capacamada fechada** (senão tenta de novo ou lança erro), só então o formulário principal volta a aparecer.
        """
        # abre "envia a capa"
        upload_link = page.get_by_role("link", name="上传封面").first
        if not await upload_link.count():
            upload_link = page.locator('a:has-text("上传封面")').first
        await upload_link.wait_for(state="visible", timeout=20000)
        await upload_link.click()
        await page.wait_for_timeout(1200)

        # camada "editar capa"
        cover_layer = page.locator('div.wbpro-layer:has(div:text-is("编辑封面"))').first
        await cover_layer.wait_for(state="visible", timeout=15000)

        # coloca o arquivo da capa (o .first pega o campo principal visível; o .last pega o cortador de tamanho zero no painel escondido,
        # resulta em "cortando" trava para sempre e a requisição picupload nunca sai)
        file_input = page.locator('input[type="file"][accept*="jpg"]').first
        await file_input.wait_for(state="attached", timeout=15000)
        await file_input.set_input_files(self.thumbnail_path)
        weibo_logger.info(_msg("🏃", f"imagem de capa escolhida: {self.thumbnail_path}"))

        # cropper imagem gerada localmente (na casa dos segundos)
        blob_img = page.locator('.cropper-container img[src^="blob:"], .wb_cropper img[src^="blob:"]').first
        try:
            await blob_img.wait_for(state="attached", timeout=20000)
        except PWTimeoutError:
            weibo_logger.warning(_msg("⚠️", "cropper nenhuma imagem blob à vista; ainda assim clica em concluirído"))
        await page.wait_for_timeout(500)

        # final tolerante: o corte demora conforme a imagem e a rede, então não apostamos em tempo fixo nem numa requisição específica.
        # só aceita**resultado real**——"editar capa" se a camada fechou; nesse meio-tempo**clica de tempos em tempos "concluído"**
        #  (clicar durante o corte não faz mal; o clique depois de pronto fecha a camada), e identifica erros de corte ou envio.
        finish_btn = cover_layer.locator('div.wbpro-layer-btn button:has(span:text-is("完成"))').first
        if not await finish_btn.count():
            finish_btn = cover_layer.locator('button:has(span:text-is("完成"))').first
        closed = False
        last_click = 0.0
        start = time.monotonic()
        while time.monotonic() - start < 300:  # folga de 5 minutos
            # critério: a camada de edição da capa não está mais visível → deu certo
            try:
                if not await cover_layer.is_visible():
                    closed = True
                    break
            except Exception:
                closed = True
                break
            # identificação do erro (falha no corte, no formato ou no envio)
            try:
                layer_txt = await cover_layer.inner_text()
            except Exception:
                layer_txt = ""
            # textos de erro da própria página: não traduzir
            for err in ("裁切失败", "上传失败", "图片格式", "封面上传失败", "重新上传", "格式不支持"):
                if err in layer_txt:
                    raise RuntimeError(f"falha no corte ou no envio da capa: {err}")
            # clica periodicamente "concluído" (a cada 4 s; pula os claramente desabilitados)
            if time.monotonic() - last_click > 4:
                try:
                    if await finish_btn.count() and await finish_btn.is_visible():
                        if (await finish_btn.get_attribute("aria-disabled")) != "true":
                            await finish_btn.click(timeout=3000)
                except Exception:
                    pass
                last_click = time.monotonic()
            await asyncio.sleep(2)
        if not closed:
            raise RuntimeError("depois do concluído da capa, a camada de edição ficou mais de 300 s sem fechar; o serviço de corte parece com problema")

        # confirmaro formulário principal voltou a ficar visível (display volta de none para)
        main_form = page.locator('div.wbpro-layer[class*="_layer_19x8d"]').first
        try:
            await main_form.wait_for(state="visible", timeout=10000)
        except PWTimeoutError:
            weibo_logger.warning(_msg("⚠️", "fechada a capa, o formulário principal não confirmou estar visível; tentando de novo"))
        weibo_logger.success(_msg("🖼️", "capa enviada e concluiído"))

    async def _select_type(self, page: Page) -> None:
        """tipo (obrigatório): escolher" conteúdo derivado ".

        DOM real: `<div class="_type_1vpmt_29 ">` os dois de baixo
        `<label class="woo-radio-main"><input type=radio><span class="woo-radio-shadow"><span class="woo-radio-text">conteúdo derivado</span></label>`, 
        depois de selecionado, o `woo-radio-shadow` acrescenta `woo-radio-checked`.
        """
        label = page.locator('label.woo-radio-main:has(span.woo-radio-text:text-is("二创"))').first
        await label.wait_for(state="visible", timeout=20000)
        await label.click()
        await page.wait_for_timeout(500)

        checked_sel = 'label.woo-radio-main:has(span.woo-radio-text:text-is("二创")) span.woo-radio-checked'
        if not await page.locator(checked_sel).count():
            # reserva: marca o radio direto
            try:
                await label.locator('input.woo-radio-input').check()
                await page.wait_for_timeout(300)
            except Exception:
                pass
        if not await page.locator(checked_sel).count():
            raise RuntimeError("tipo'conteúdo derivado'não selecionado")
        weibo_logger.info(_msg("🏷️", "tipoescolhido: conteúdo derivado"))

    async def _select_declaration(self, page: Page) -> None:
        """declaração de conteúdo (obrigatório): escolher" contém conteúdo gerado por IA ".

        DOM real: 
          - abre a lista: o `.woo-pop-ctrl` dentro de `<div class="_gap1_nsgmr_26 ">` (o wbpro-select com caretDown)
          - camada: `<div class="_panel_nsgmr_114 ">`, opção `<button class="_option..."><span class="_optionLabel...">contém conteúdo gerado por IA</span></button>`
          - depois de selecionado, dentro desse botão `._check_nsgmr_237` acrescenta `_checkActive_nsgmr_251` (com _checkMark)
          - fim `._footer_nsgmr_270 button` ("confirmar")fecha a camada
        """
        # abre a lista
        trigger = page.locator('div[class*="_gap1_nsgmr"] .woo-pop-ctrl').first
        if not await trigger.count():
            trigger = page.locator('div:has(> div[class*="_tit1_nsgmr"]) .woo-pop-ctrl').first
        await trigger.wait_for(state="visible", timeout=15000)
        await trigger.click()
        await page.wait_for_timeout(1000)

        panel = page.locator('div[class*="_panel_nsgmr"]').first
        if await panel.count():
            try:
                await panel.wait_for(state="visible", timeout=8000)
            except PWTimeoutError:
                panel = None
        else:
            panel = None

        scope = panel if panel is not None else page
        ai_opt = scope.locator('button:has(span:text-is("含AI生成内容"))').first
        await ai_opt.wait_for(state="visible", timeout=8000)
        await ai_opt.click()
        await page.wait_for_timeout(500)

        # confere se ficou selecionado
        if not await ai_opt.locator('[class*="_checkActive"]').count():
            weibo_logger.warning(_msg("⚠️", "a declaração de conteúdo gerado por IA parece inativa; ainda assim vou confirmar"))

        # clica em confirmar para fechar a camada
        confirm = scope.locator('div[class*="_footer_nsgmr"] button:has(span:text-is("确定"))').first
        if not await confirm.count():
            confirm = scope.locator('button:has(span:text-is("确定"))').last
        if await confirm.count():
            await confirm.click()
            await page.wait_for_timeout(500)
        weibo_logger.info(_msg("🏷️", "declaração de conteúdoescolhido: contém conteúdo gerado por IA"))

    async def _fill_description(self, page: Page) -> None:
        """preenche a descriçãoárea (corpo do texto + etiquetas).

        descrição do Weiboçãoplaceholder da área: " O que você quer compartilhar?"
        as etiquetas entram no fim da descrição no formato #hashtag#.
        """
        desc_field = page.get_by_placeholder("有什么新鲜事想分享给大家？")
        if not await desc_field.count():
            weibo_logger.warning(_msg("⚠️", "não achei a descriçãocampo de texto"))
            return

        # monta a descriçãoconteúdo: corpo do texto + etiquetas
        content = self.desc
        if self.tags:
            tag_str = " ".join(f"#{t}#" for t in self.tags)
            content = f"{content}\n{tag_str}" if content else tag_str

        if content:
            await desc_field.click()
            await desc_field.fill(content)
            weibo_logger.info(_msg("📝", f"descrição preenchida ({len(content)} caracteres)"))

    async def _apply_collection(self, page: Page) -> None:
        """coletânea: usa uma existente ou cria.

        DOM real: abre "coletânea" ligado, o painel de coletâneas aparece `._scroll_19x8d_143`——uma coletânea existente por linha
        `woo-checkbox` + somente leitura `input value=" nome(N episódios)"`; fim `._add_19x8d_63` ("nova coletânea").
          - existente: marca a que tem o nome igual (remove "(N episódios)" depois do sufixo)o checkbox daquela linha.
          - sem ela: clica "nova coletânea"→ adiciona uma linha(marca sozinho)e com um campo editável → preenche o nome da coletânea(≤12).
        """
        target = (self.collection_name or "").strip()
        if not target:
            return

        # 1) liga a coletânea
        block = page.locator('div[class*="_switch_"]:has(div[class*="_tit1_"]:text-is("合集"))').first
        if not await block.count():
            block = page.locator('div:has(> div:text-is("合集")):has(label.woo-switch-main)').first
        try:
            switch_input = block.locator('label.woo-switch-main input.woo-switch-input').first
            try:
                already = await switch_input.is_checked()
            except Exception:
                already = False
            if not already:
                for sw in (
                    block.locator('label.woo-switch-main span[role="switch"]').first,
                    block.locator('label.woo-switch-main').first,
                ):
                    try:
                        await sw.click(timeout=6000)
                    except Exception:
                        try:
                            await sw.click(timeout=4000, force=True)
                        except Exception:
                            continue
                    await page.wait_for_timeout(1000)
                    try:
                        if await switch_input.is_checked():
                            break
                    except Exception:
                        break
        except Exception as exc:
            weibo_logger.warning(_msg("⚠️", f"erro ao ligar a coletânea; ainda assim procuro o painel: {exc}"))

        # 2) painel de coletâneas
        panel = page.locator('div[class*="_scroll_"]:has(div[class*="_add_"])').first
        if not await panel.count():
            panel = page.locator('div:has(> div[class*="_add_"]:has-text("新建合集"))').first
        try:
            await panel.wait_for(state="visible", timeout=8000)
        except PWTimeoutError:
            weibo_logger.warning(_msg("⚠️", "o painel de coletâneas não apareceu; seguindo sem ela"))
            return

        # 3) casa com uma coletânea existente (remove "(N episódios)" sufixo)
        rows = panel.locator('div[class*="_top2_"]')
        n = await rows.count()
        matched = False
        for i in range(n):
            row = rows.nth(i)
            inp = row.locator('input[type="text"]').first
            if not await inp.count():
                continue
            val = (await inp.get_attribute("value")) or ""
            name = re.sub(r"\(共\d+集\)\s*$", "", val).strip()
            if name and name == target:
                await row.locator('label.woo-checkbox-main').first.click()
                await page.wait_for_timeout(400)
                matched = True
                weibo_logger.info(_msg("🥳", f"coletânea existente escolhida: {target}"))
                break

        # 4) se não houver, cria (best-effort: se criar falhar, apenas segue sem coletânea, nunca interrompe a publicação)
        if not matched:
            try:
                add_btn = panel.locator('div[class*="_add_"]:has-text("新建合集")').first
                if not await add_btn.count():
                    add_btn = page.locator('div:has-text("新建合集")').last
                # "nova coletânea" a linha tem 598px de largura e a parte clicável "＋nova coletânea " o texto fica à esquerda; clicar no centro da linha cai
                # à direita é vazia e não dispara; passamos a clicar no interior "nova coletânea" span de texto (fica à esquerda e sempre dispara o onClick).
                add_target = add_btn.get_by_text("新建合集", exact=True).first
                if not await add_target.count():
                    add_target = add_btn
                # o campo editável da linha nova (os campos das linhas existentes vêm desabilitados; os da linha nova, não)
                new_inp = panel.locator('div[class*="_top2_"] input[type="text"]:not([disabled])').last
                created = False
                for _ in range(3):
                    try:
                        await add_target.scroll_into_view_if_needed(timeout=2000)
                    except Exception:
                        pass
                    try:
                        await add_target.click(timeout=4000)
                    except Exception:
                        try:
                            await add_target.click(timeout=3000, force=True)
                        except Exception:
                            try:
                                await add_target.evaluate("el => el.click()")
                            except Exception:
                                pass
                    await page.wait_for_timeout(800)
                    if await new_inp.count() and await new_inp.is_visible():
                        created = True
                        break
                if not created:
                    weibo_logger.warning(_msg("⚠️", f"a linha de digitação da nova coletânea não apareceu: seguindo sem coletânea ({target[:12]})"))
                    return
                await new_inp.click()
                await new_inp.fill(target[:12])
                await page.wait_for_timeout(500)
                weibo_logger.info(_msg("🥳", f"nova coletânea: {target[:12]}"))
            except Exception as exc:
                weibo_logger.warning(_msg("⚠️", f"nova coletâneafalhou: seguindo sem coletâneação: {exc}"))
                return

    async def _submit_publish(self, page: Page) -> None:
        """clicapublica e confere se deu certo de verdade.

        DOM real: 
          - botão de publicar: `._check_2z30i_81 button` (conteúdo "publicar").botãoo centro pode estar coberto por uma div vazia,
            dispara o botão por JSãoo próprio click contorna a camada.
          - o único critério confiável de sucesso: a camada de sucesso `_layer1_9a8j7_2` sai de `display:none` e **fica visível**,
            contendo "publica outro vídeo" botão → usa ele ou esse botãovisível: sucesso confirmado.
             ("vídeoenviado; será publicado após a conversão" esse texto é um modelo escondido que existe sempre: não serve de critério.)
          - 60s não consegui confirmar o sucesso dentro do prazo → lança erro (não finge mais sucesso), deixa o nível de cima registrar a falha.
        """
        # fecha listas e camadas que tenham sobrado
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
        except Exception:
            pass

        publish_btn = page.locator('div[class*="_check_2z30i"] button:has(span:text-is("发布"))').first
        if not await publish_btn.count():
            publish_btn = page.get_by_role("button", name="发布").first
        await publish_btn.wait_for(state="visible", timeout=15000)
        await publish_btn.evaluate("el => el.click()")
        weibo_logger.info(_msg("🏃", "cliquei no botão de publicar(JS)"))

        success_layer = page.locator('div[class*="_layer1_9a8j7"]').first
        again_btn = page.locator('button:has(span:text-is("再发一条视频"))').first
        start = time.monotonic()
        while time.monotonic() - start < 60:
            try:
                if await again_btn.is_visible():
                    weibo_logger.success(_msg("🥳", "vídeo publicado (apareceu o botão de publicar outro vídeo)"))
                    return
            except Exception:
                pass
            try:
                if await success_layer.is_visible():
                    weibo_logger.success(_msg("🥳", "vídeo publicado (camada de sucesso visível)"))
                    return
            except Exception:
                pass
            # trata a possível janela de segunda confirmação
            try:
                dialog = page.locator('.woo-dialog-main, .woo-modal-wrap, [class*="Dialog"]').first
                if await dialog.count() and await dialog.is_visible():
                    # nomes dos botões na própria página: não traduzir
                    for name in ("确定", "确认", "继续", "仍然发布", "发布"):
                        cb = dialog.locator(f'button:has(span:text-is("{name}"))').first
                        if await cb.count() and await cb.is_visible():
                            await cb.evaluate("el => el.click()")
                            weibo_logger.info(_msg("🏃", f"janela confirmada: {name}"))
                            break
            except Exception:
                pass
            await page.wait_for_timeout(1500)

        raise RuntimeError("60 s depois de publicar, nem a camada de sucesso nem o botão de publicar outro vídeo apareceram: a publicação não deu certo (nada foi para o banco)")

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
