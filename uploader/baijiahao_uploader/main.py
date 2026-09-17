# -*- coding: utf-8 -*-
"""Baijiahao (Baijiahao do Baidu)envio de vídeo + login por QR code.

o que faz: 
  - baijiahao_cookie_gen: headless login por QR code (QR code do passport do Baidu)
  - cookie_auth: confere se o cookie ainda vale
  - baijiahao_setup: entrada única (verifica a sessão e, se preciso, faz login)
  - BaiJiaHaoVideo: classe de envio de vídeo
"""
from __future__ import annotations

import asyncio
import inspect
import json as _json
import os
import time
from pathlib import Path

from playwright.async_api import Page, Playwright, TimeoutError as PWTimeoutError, async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.log import baijiahao_logger
from utils.login_qrcode import build_login_qrcode_path, decode_qrcode_from_path, print_terminal_qrcode, remove_qrcode_file


BAIJIAHAO_LOGIN_URL = "https://baijiahao.baidu.com/builder/theme/bjh/login"
BAIJIAHAO_HOME_URL = "https://baijiahao.baidu.com/builder/rc/home"
BAIJIAHAO_PUBLISH_URL = "https://baijiahao.baidu.com/builder/rc/edit?type=videoV2"
# começo da URL para onde vai depois de publicar
BAIJIAHAO_SUCCESS_URL_PREFIX = "https://baijiahao.baidu.com/builder/rc/clue"

# seletor da imagem do QR code do passport do Baidu
QR_SELECTOR = 'img[src^="https://passport.baidu.com/v2/api/qrcode"]'


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
        return str((Path(BASE_DIR) / "cookies" / "baijiahao_uploader" / path).resolve())
    return str(path.resolve())


async def _grab_qr(page: Page, account_file: str) -> dict:
    """recorta o QR code da tela de login do passport do Baidu.

    na tela de login do Baijiahao, clica "login" abre a janela de login do Baidu, onde o QR code é um img[src] aponta para
    passport.baidu.com a URL da imagem, que dá para baixar ou capturar.
    """
    qr = page.locator(QR_SELECTOR).first
    await qr.wait_for(state="attached", timeout=60000)

    qrcode_path = build_login_qrcode_path(account_file)
    qrcode_path.parent.mkdir(parents=True, exist_ok=True)

    # tenta primeiro baixar a URL da imagem em alta
    src = await qr.get_attribute("src")
    if src and src.startswith("https://"):
        try:
            resp = await page.context.request.get(src)
            qrcode_path.write_bytes(await resp.body())
        except Exception:
            await qr.screenshot(path=str(qrcode_path))
    else:
        await qr.screenshot(path=str(qrcode_path))

    qrcode_content = decode_qrcode_from_path(qrcode_path)
    baijiahao_logger.info(_msg("🖼️", f"QR code salvo em: {qrcode_path}"))
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, "aplicativo do Baidu")
    else:
        baijiahao_logger.warning(_msg("😵", f"o terminal não mostra o QR code inteiro; abra {qrcode_path} escanear o QR code"))
    return {"image_path": str(qrcode_path), "image_data_url": ""}


async def _is_login_completed(page: Page) -> bool:
    """vê se o login do Baidu terminouído: URL sair da tela de login ou aparecer o cookie BDUSS."""
    if "login" in page.url.lower():
        # ainda na tela de login; conferindo os cookies
        cookies = await page.context.cookies()
        if any(c.get("name") in ("BDUSS", "STOKEN") for c in cookies):
            return True
        return False
    # sair dessa página significa que o login deu certo
    return True


async def baijiahao_cookie_gen(account_file, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 120, headless: bool = LOCAL_CHROME_HEADLESS):
    """login por QR code no Baijiahao, com ou sem janela, salvando o cookie.

    fluxo: abre a tela de login → clica em "login" → abre a janela do passport do Baidu → recorta o QR code → espera a leitura → salva o storage_state.
    devolve o dicionário padrão do resultado de login.
    """
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)
    qrcode_path = None
    result = _build_login_result(False, "failed", "falha no login do Baijiahao", account_file)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.goto(BAIJIAHAO_LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)

            # clica "login" botãodispara a janela do passport do Baidu
            login_btn = page.get_by_text("登录", exact=True).first
            try:
                await login_btn.click(timeout=10000)
            except Exception:
                # em alguns casos a sessão já está ativa
                pass
            await page.wait_for_timeout(4000)

            if headless:
                baijiahao_logger.info(_msg("🧍", "login sem janela: o QR code virou imagem; escaneie pelo aplicativo do Baidu"))
            else:
                baijiahao_logger.info(_msg("🧍", "entre no Baijiahao pelo QR code na janela aberta"))

            # recorta o QR code
            qrcode_info = await _grab_qr(page, account_file)
            qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None
            await _emit_qrcode_callback(qrcode_callback, qrcode_info)

            baijiahao_logger.info(_msg("🧍", "escaneie o QR code; esperando o login terminar"))

            # fica verificando até o login terminar
            for _ in range(max_checks):
                if await _is_login_completed(page):
                    baijiahao_logger.info(_msg("🥳", f"escanear o QR codedeu certo; página atual: {page.url}"))
                    result = _build_login_result(True, "success", "login por QR code do Baijiahao concluído", account_file, qrcode_info, page.url)
                    break
                await page.wait_for_timeout(poll_interval * 1000)
            else:
                result = _build_login_result(False, "timeout", "tempo esgotado esperando o login por QR code do Baijiahao", account_file, qrcode_info, page.url)

            if result["success"]:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                baijiahao_logger.success(_msg("🥳", f"cookie salvo: {account_file}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                baijiahao_logger.info(_msg("🧹", f"arquivo temporário do QR code apagado: {qrcode_path}"))
            if not result["success"]:
                baijiahao_logger.error(_msg("😢", f"falha no login: {result['message']}"))
            await context.close()
            await browser.close()
    return result


async def cookie_auth(account_file):
    """verificaçãoo cookie do Baijiahao ainda é válido.abre a página inicial do painel e vê se pede login."""
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            page = await context.new_page()
            await page.goto(BAIJIAHAO_HOME_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            if await page.get_by_text("注册/登录百家号").count():
                baijiahao_logger.info(_msg("🥹", "cookie expirado"))
                return False
            else:
                baijiahao_logger.success(_msg("🥳", "cookie válido"))
                return True
        except Exception as exc:
            baijiahao_logger.warning(_msg("😵", f"cookie erro na verificação: tratando como expirado: {exc}"))
            return False
        finally:
            await browser.close()


async def baijiahao_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    """entrada única: confere o cookie → se estiver inválido e handle=True dispara o login por QR code."""
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie arquivo inexistente ou expirado", account_file)
            return result if return_detail else False
        baijiahao_logger.info(_msg("🥹", "cookie arquivo inexistente ou expirado: abrindo o navegador para você escanear o QR code"))
        result = await baijiahao_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie válido", account_file)
    return result if return_detail else True


class BaiJiaHaoVideo(BaseVideoUploader):
    """Baijiahao envio de vídeo.

    fluxo: abre a página de publicação → envia o arquivo de vídeo → preenche o título → espera o envio e a conversão terminaremído → espera a capa → clicapublicar.
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
            raise RuntimeError(f"cookiearquivo inexistente; conclua antes o ídologin do Baijiahao: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookiearquivo expirado; conclua antes o ídologin do Baijiahao: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("o título do vídeo não pode ficar vazio")
        if not self.thumbnail_path:
            raise ValueError("Baijiahao vídeoa publicação exige uma capa na horizontal (--thumbnail)")
        self.file_path = str(self.validate_video_file(self.file_path))
        self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def upload(self, playwright: Playwright) -> None:
        baijiahao_logger.info(_msg("🧍", "confere o cookie e o arquivo de vídeo"))
        await self.validate_upload_args()
        baijiahao_logger.info(_msg("🥳", "verificação antes do envio concluída"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)
        await context.grant_permissions(["geolocation"])

        try:
            page = await context.new_page()
            await page.goto(BAIJIAHAO_PUBLISH_URL, timeout=120000, wait_until="domcontentloaded")
            baijiahao_logger.info(_msg("🏃", f"começando o envio do vídeo: {self.title}"))

            # espera a página de publicação carregar
            await page.wait_for_timeout(3000)

            # 1) envia o arquivo de vídeo
            file_input = page.locator('input[type="file"][accept*="video"], input[type="file"][accept*="mp4"]').first
            if not await file_input.count():
                file_input = page.locator("div[class^='video-main-container'] input[type='file']").first
            if not await file_input.count():
                file_input = page.locator('input[type="file"]').first
            await file_input.wait_for(state="attached", timeout=30000)
            await file_input.set_input_files(self.file_path)
            baijiahao_logger.info(_msg("🏃", f"arquivo de vídeo escolhido: {self.file_path}"))

            # 2) espera entrar no formulário (contenteditable a área do título aparecendo, o formulário terminou de montar)
            title_editor = page.locator('div[class*="contentEditable"]').first
            await title_editor.wait_for(state="visible", timeout=180000)
            await page.wait_for_timeout(1000)

            # 3) preenche o título
            await self._fill_title(page)

            # 4) espera envio do vídeo concluído
            await self._wait_upload_complete(page)

            # 5) enviarcapa na horizontal (obrigatório)
            await self._upload_thumbnail(page)

            # 6) marcar "contém conteúdo gerado por IA"
            await self._check_ai_declaration(page)

            # 7) escolhercoletânea (se estiver configurado)
            await self._apply_collection(page)

            # 8) clicapublicar
            await self._submit_publish(page)

            # salva o cookie
            await context.storage_state(path=self.account_file)
            baijiahao_logger.success(_msg("🥳", "cookie atualização concluída"))
        finally:
            await context.close()
            await browser.close()

    async def _fill_title(self, page: Page) -> None:
        title_field = page.locator('div[class*="contentEditable"]').first
        await title_field.wait_for(state="visible", timeout=15000)
        title = self.title
        # o título do Baijiahao precisa de ao menos 9 caracteres
        if len(title) <= 8:
            title += " o que você não sabe"
        title = title[: self.max_title_length]
        # limpa o que havia (pode ter preenchido com o nome do arquivo), depois digita o título
        await title_field.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Backspace")
        await title_field.fill(title)
        baijiahao_logger.info(_msg("🏷️", f"título preenchido: {title}"))

    async def _wait_upload_complete(self, page: Page, timeout: int = 600) -> None:
        """espera envio do vídeo realmente concluído.

        o progresso real do Baidu é um texto com a porcentagem (9%…99%, envio concluídosome depois; neste arquivo levou uns 35 s no teste).
        旧实现用 'div .cover-overlay:has-text("上传中")' 判断——经实测该元素恒不存在，
        levava a um falso resultado logo após escolher o arquivo "enviarconcluído" (cerca de 4 s).um arquivo grande ainda está subindo em segundo plano; em seguida clica
        o Baidu recusa a publicação por "garante que envio do vídeo concluído" recusado (nenhuma obra publicada).agora acompanha a porcentagem:
        só conta como enviado quando houve progresso e ele sumiu ou chegou a 100%ído.
        """
        import re as _re
        start = time.monotonic()
        seen_progress = False
        gone_count = 0
        while True:
            if time.monotonic() - start > timeout:
                baijiahao_logger.warning(_msg("⚠️", f"tempo esgotado esperando o envio (>{timeout}s), segue para os próximos passos"))
                return

            body = ""
            try:
                body = await page.inner_text("body")
            except Exception:
                pass

            # o texto em chinês é o que a própria página mostra: não traduzir
            if "上传失败" in body:
                raise RuntimeError("falha no envio do vídeo")

            m = _re.search(r'(\d{1,3})\s*%', body)
            pct = int(m.group(1)) if m else None

            if pct is not None and pct < 100:
                seen_progress = True
                gone_count = 0
                baijiahao_logger.info(_msg("🏃", f"enviando {pct}%"))
                await asyncio.sleep(2)
                continue

            if seen_progress:
                # a porcentagem sumiu ou chegou a 100%: depois de duas confirmações seguidas, considera o envio concluído
                gone_count += 1
                if gone_count >= 2:
                    baijiahao_logger.success(_msg("🥳", "envio do vídeo concluído"))
                    return
                await asyncio.sleep(2)
                continue

            # nenhum progresso apareceu: arquivo pequeno pode subir num instanteído; libera depois de uma janela de 15 s
            if time.monotonic() - start > 15:
                baijiahao_logger.success(_msg("🥳", "envio do vídeo concluído"))
                return
            await asyncio.sleep(2)

    async def _upload_thumbnail(self, page: Page) -> None:
        """enviarcapa na horizontal (obrigatório).

        fluxo: clica "escolhe a capa"→ na janela, clica "enviar" botão → define o arquivo de imagem → espera o envio terminarído → confirmar.
        sem thumbnail_path, basta esperar o site gerar a capa sozinho.
        """
        if not self.thumbnail_path:
            # sem capa personalizada: espera o site gerar
            await self._wait_cover_ready(page)
            return

        try:
            # 1) clica "escolhe a capa" entrada
            cover_entry = page.locator('[data-testid="select-cover"]').first
            if not await cover_entry.count():
                # alternativa: localiza pelo texto
                cover_entry = page.get_by_text("选择封面", exact=True).first
            await cover_entry.scroll_into_view_if_needed()
            await cover_entry.click(timeout=10000)
            baijiahao_logger.info(_msg("🏃", "cliquei em escolher a capa"))
            await page.wait_for_timeout(2000)

            # 2) procura na janela "enviar" botão e clica
            # a janela de capa do Baijiahao costuma ter "enviar" tab/botão
            upload_btn = page.locator('button:has-text("上传"), div:has-text("上传"):not(:has(*)):visible').first
            if not await upload_btn.count():
                upload_btn = page.get_by_text("上传", exact=True).first
            await upload_btn.click(timeout=8000)
            await page.wait_for_timeout(1500)

            # 3) coloca a imagem no campo de arquivo
            # um input aparece na janela[type=file]
            img_input = page.locator('input[type="file"][accept*="image"], input[type="file"][accept*="jpg"], input[type="file"][accept*="png"]').first
            if not await img_input.count():
                # reserva geral: o campo de arquivo mais novo dentro da janela
                img_input = page.locator('input[type="file"]').last
            await img_input.set_input_files(self.thumbnail_path)
            baijiahao_logger.info(_msg("🏃", f"imagem de capa escolhida: {self.thumbnail_path}"))

            # 4) espera e clica em confirmar/concluirídobotão (se houver janela de corte).
            #    a janela de corte demora a aparecer (envio das imagens + processamento no servidor); antes havia um sleep fixo de 3 s e depois
            #    checar o confirm_btn de uma vez, antes de a janela existir, dá falso "não precisa confirmar" e pular o clique,
            #    a capa escolhida não era enviada, mas o log dizia que sim "capa enviada" sucesso — foi o que aconteceu em produção
            #    Baijiahao vídeoera a causa de capa faltando com log de sucesso; agora fica verificando (sem aumentar o tempo limite em si
            #    não é erro: a janela de corte é opcional e pode simplesmente não existir nesse fluxo).
            confirm_btn = page.locator('button:has-text("确定"), button:has-text("完成"), button:has-text("确认")').first
            confirmed = False
            try:
                await confirm_btn.wait_for(state="visible", timeout=15000)
                await confirm_btn.click(timeout=8000)
                await page.wait_for_timeout(1000)
                confirmed = True
            except PWTimeoutError:
                baijiahao_logger.debug("botão de confirmar a capaãonão apareceu: talvez este fluxo não precise confirmar o corte")

            if confirmed:
                baijiahao_logger.success(_msg("🖼️", "capa enviada"))
            else:
                # o botão de confirmar não apareceuão: não confirma se a capa pegou, e não finge sucesso,
                # deixa para o mesmo tratamento do except abaixo "espera a capa automática" conferência de reserva.
                raise RuntimeError("botão de confirmar a capaãonão apareceu: não dá para confirmar se a capa pegou")
        except Exception as exc:
            baijiahao_logger.warning(_msg("⚠️", f"falha ao enviar a capa: {exc}, tenta esperar a capa automática"))
            # fallback: espera o site gerar
            await self._wait_cover_ready(page)

    async def _check_ai_declaration(self, page: Page) -> None:
        """escolher" contém conteúdo gerado por IA " declaração de criação.

        clica no campo da declaração de criação → abre a janela → escolhe "contém conteúdo gerado por IA" → confirma.
        """
        try:
            # clicao campo da declaração abre a janela
            trigger = page.locator('input[placeholder="请选择创作声明"]').first
            await trigger.scroll_into_view_if_needed()
            await trigger.click(force=True, timeout=8000)
            await page.wait_for_timeout(3000)

            # escolhe dentro da janela "contém conteúdo gerado por IA"
            ai_option = page.locator('.cheetah-modal-wrap :text("含AI生成内容")').first
            if not await ai_option.count():
                ai_option = page.locator('text="含AI生成内容"').first
            await ai_option.wait_for(state="visible", timeout=10000)
            await ai_option.click(timeout=5000)
            await page.wait_for_timeout(1000)

            # clica em confirmar e fecha a janela (ela pode continuar aberta depois da escolha)
            modal = page.locator('.cheetah-modal-wrap:visible').first
            if await modal.count():
                confirm_btn = modal.locator('button:has-text("确定")').first
                if await confirm_btn.count() and await confirm_btn.is_visible():
                    await confirm_btn.click(timeout=5000)
                    await page.wait_for_timeout(500)
                else:
                    # confirmarbotãoinvisível: tenta clique forçado ou fecha com Escape
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)

            baijiahao_logger.success(_msg("🏷️", "escolhi a opção de conteúdo gerado por IA"))
        except Exception as exc:
            # falhando, tenta fechar alguma janela que tenha sobrado
            try:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            except Exception:
                pass
            baijiahao_logger.warning(_msg("⚠️", f"escolher AI falha na declaração: {exc}"))

    async def _apply_collection(self, page: Page) -> None:
        """escolhercoletânea (cheetah-select busca da lista).

        placeholder: "escolhercoletâneas do mesmo tema costumam render mais visualizações"
        com collection_name, abre a lista → busca e seleciona a coletânea; se não houver, pula.
        """
        if not self.collection_name:
            return
        try:
            # acha a lista de coletâneas (pelo texto do placeholder)
            select_box = page.locator('.cheetah-select:has(.cheetah-select-selection-placeholder:has-text("选择同主题的合集"))').first
            if not await select_box.count():
                select_box = page.locator('.cheetah-select-selection-placeholder:has-text("合集")').locator('xpath=ancestor::div[contains(@class,"cheetah-select")]').first
            if not await select_box.count():
                baijiahao_logger.warning(_msg("⚠️", "não achei o seletor de coletânea; pulando"))
                return

            await select_box.scroll_into_view_if_needed()
            await select_box.click(timeout=8000)
            await page.wait_for_timeout(1500)

            # digita o nome da coletânea na busca (dispara o filtro da busca)
            search_input = select_box.locator('input.cheetah-select-selection-search-input').first
            if await search_input.count():
                await search_input.fill(self.collection_name)
                await page.wait_for_timeout(1500)

            # seleciona a coletânea na lista
            option = page.locator(f'[role="option"]:has-text("{self.collection_name}"), .cheetah-select-item:has-text("{self.collection_name}")').first
            if await option.count():
                await option.click(timeout=5000)
                await page.wait_for_timeout(500)
                baijiahao_logger.success(_msg("🥳", f"coletânea escolhida: {self.collection_name}"))
            else:
                baijiahao_logger.warning(_msg("⚠️", f"a conta não tem a coletânea '{self.collection_name}': pulando"))
                await page.keyboard.press("Escape")
        except Exception as exc:
            baijiahao_logger.warning(_msg("⚠️", f"escolherfalhou na coletânea; pulando: {exc}"))

    async def _wait_cover_ready(self, page: Page, timeout: int = 120) -> None:
        """espera o Baijiahao gerar a capa."""
        start = time.monotonic()
        while True:
            if time.monotonic() - start > timeout:
                baijiahao_logger.warning(_msg("⚠️", "tempo esgotado esperando a capa ser gerada; seguindo a publicação"))
                return
            if await page.locator("div.cheetah-spin-container img").count():
                baijiahao_logger.info(_msg("🖼️", "capa gerada"))
                return
            baijiahao_logger.info(_msg("🏃", "esperando a capa ser gerada..."))
            await asyncio.sleep(3)

    async def _submit_publish(self, page: Page) -> None:
        """clicabotão de publicare confirma o sucesso."""
        # garante que nenhuma janela ficou cobrindo
        modal = page.locator('.cheetah-modal-wrap:visible').first
        if await modal.count():
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

        # botão de publicar do Baijiahaoãotem data-testid="publish-btn"
        publish_btn = page.locator('[data-testid="publish-btn"]').first
        if not await publish_btn.count():
            publish_btn = page.locator('button:text-is("发布")').first
        if not await publish_btn.count():
            publish_btn = page.locator('button:has-text("发布")').last
        await publish_btn.wait_for(state="visible", timeout=15000)
        await publish_btn.click(force=True)
        baijiahao_logger.info(_msg("🏃", "cliquei no botão de publicar"))

        # espera a navegação ou a mensagem de sucesso (no máximo 30 s)
        start = time.monotonic()
        while time.monotonic() - start < 30:
            url = page.url
            # publicado, navegando
            if BAIJIAHAO_SUCCESS_URL_PREFIX in url or "/rc/content" in url or "/rc/home" in url:
                baijiahao_logger.success(_msg("🥳", "vídeo publicado"))
                return
            # vê se apareceu a verificação de segurança do Baidução
            if await page.locator('text="百度安全验证"').count():
                raise RuntimeError("apareceuverificação de segurança do Baidução, precisa de intervenção manual")
            # vê se algum aviso de erro impede a publicação
            error_toast = page.locator('.cheetah-message-error, .cheetah-message-warning').first
            if await error_toast.count() and await error_toast.is_visible():
                err_text = await error_toast.inner_text()
                baijiahao_logger.warning(_msg("⚠️", f"aviso de publicação: {err_text}"))
            await page.wait_for_timeout(1000)

        # tempo esgotado; confere de novo
        if BAIJIAHAO_SUCCESS_URL_PREFIX in page.url or "/rc/content" in page.url:
            baijiahao_logger.success(_msg("🥳", "vídeo publicado"))
        else:
            raise RuntimeError(f"publiquei e não fui para a página de sucesso (30s), URL atual: {page.url}")

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
