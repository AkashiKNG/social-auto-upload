# Browser CLI Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** unificar o contrato da CLI `sau` nas três plataformas de navegador — Douyin, Kuaishou e Xiaohongshu `sau` CLI unificar o contrato, dar ao Xiaohongshu CLI e skill, e padronizar a descrição do vídeo como `desc`, o texto do post passa a se chamar `note`.

**Architecture:** manter o atual `sau_cli.py` como entrada única num só arquivo, sem trazer um framework de CLI novo.`sau_cli.py` cuida do parser, dos dataclasses de requisição, do dispatch e da resolução dos arquivos de conta; cada uploader só recebe a ligação mínima de campos; skills, README, documentos de CLI/install/update e exemplos mudam juntos para o contrato unificado, para não haver dois nomes públicos ao mesmo tempo.

**Tech Stack:** Python 3.10+, `argparse`, `asyncio`, `dataclasses`, `pathlib`, `unittest`, existing Patchright-based uploaders, repository markdown docs

---

## File Structure

### New files

- `tests/test_sau_browser_cli.py`
  - cobre o parser, o dispatch e o mapeamento de requisição unificados das três plataformas de navegador
- `skills/xiaohongshu-upload/SKILL.md`
  - explicação principal da skill da CLI do Xiaohongshu
- `skills/xiaohongshu-upload/references/runtime-requirements.md`
  - pré-requisitos do Xiaohongshu
- `skills/xiaohongshu-upload/references/cli-contract.md`
  - contrato da CLI do Xiaohongshu
- `skills/xiaohongshu-upload/references/troubleshooting.md`
  - guia de problemas do Xiaohongshu
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.ps1`
  - PowerShell comandos de exemplo
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.sh`
  - shell comandos de exemplo
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_cli_template.py`
  - Python modelo de comandos

### Modified files

- `sau_cli.py`
  - novo `xiaohongshu` parser / dispatch
  - reformar os dataclasses de requisição e o modelo de parâmetros de Douyin e Kuaishou
- `uploader/douyin_uploader/main.py`
  - ligar no vídeo o `desc`
  - ligar no post o `title + note`
- `uploader/ks_uploader/main.py`
  - ligar no vídeo o `desc`
  - ligar no post o `title + note`
- `uploader/xiaohongshu_uploader/main.py`
  - só a adaptação mínima de campos que a ligação com a CLI exige
- `README.md`
  - acrescentar CLI e skill do Xiaohongshu e unificar a explicação de parâmetros das três
- `docs/CLI.md`
  - unificar o contrato de comandos das três plataformas de navegador
- `docs/install.md`
  - acrescentar o exemplo de CLI do Xiaohongshu e a explicação unificada de parâmetros
- `docs/update.md`
  - acrescentar os itens de conferência e o caminho da skill do Xiaohongshu
- `skills/douyin-upload/SKILL.md`
- `skills/douyin-upload/references/cli-contract.md`
- `skills/douyin-upload/scripts/examples/douyin_commands.ps1`
- `skills/douyin-upload/scripts/examples/douyin_commands.sh`
- `skills/douyin-upload/scripts/examples/douyin_cli_template.py`
- `skills/kuaishou-upload/SKILL.md`
- `skills/kuaishou-upload/references/cli-contract.md`
- `skills/kuaishou-upload/scripts/examples/kuaishou_commands.ps1`
- `skills/kuaishou-upload/scripts/examples/kuaishou_commands.sh`
- `skills/kuaishou-upload/scripts/examples/kuaishou_cli_template.py`
- `examples/get_xiaohongshu_cookie.py`
- `examples/upload_video_to_xiaohongshu.py`

## Task 1: fixar o contrato unificado da CLI com testes

**Files:**
- Create: `tests/test_sau_browser_cli.py`
- Reference: `sau_cli.py`

- [ ] **Step 1: escrever os testes do parser unificado da CLI**

Em `tests/test_sau_browser_cli.py`, cobrir o contrato mínimo de comandos:

```python
import asyncio
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import sau_cli


class BrowserCliParserTests(unittest.TestCase):
    def test_build_parser_accepts_xiaohongshu_login(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["xiaohongshu", "login", "--account", "creator"])
        self.assertEqual(args.platform, "xiaohongshu")
        self.assertEqual(args.action, "login")

    def test_douyin_upload_video_accepts_desc(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args([
            "douyin", "upload-video",
            "--account", "creator",
            "--file", "demo.mp4",
            "--title", "título",
            "--desc", "descrição do vídeo",
        ])
        self.assertEqual(args.desc, "descrição do vídeo")

    def test_kuaishou_upload_note_accepts_title_and_note(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args([
            "kuaishou", "upload-note",
            "--account", "creator",
            "--images", "1.png",
            "--title", "título do post",
            "--note", "texto do post",
        ])
        self.assertEqual(args.title, "título do post")
        self.assertEqual(args.note, "texto do post")
```

- [ ] **Step 2: escrever os testes de roteamento do dispatch**

continua em `tests/test_sau_browser_cli.py` , acrescentar a verificação mínima do dispatch:

```python
class BrowserCliDispatchTests(unittest.TestCase):
    def test_dispatch_xiaohongshu_check_prints_valid(self):
        args = Namespace(platform="xiaohongshu", action="check", account="creator")
        with patch("sau_cli.check_xiaohongshu_account", new=AsyncMock(return_value=True)):
            code = asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(code, 0)

    def test_dispatch_douyin_upload_note_uses_new_request_fields(self):
        args = Namespace(
            platform="douyin",
            action="upload-note",
            account="creator",
            images=[Path("1.png")],
            title="título do post",
            note="texto do post",
            tags="testes,post de imagens",
            schedule=0,
            debug=False,
            headless=True,
        )
        with patch("sau_cli.upload_note", new=AsyncMock()) as mock_upload:
            asyncio.run(sau_cli.dispatch(args))
        request = mock_upload.await_args.args[0]
        self.assertEqual(request.title, "título do post")
        self.assertEqual(request.note, "texto do post")
```

- [ ] **Step 3: rodar os testes antes e confirmar que falham**

Run:

```powershell
py -3 -m unittest tests.test_sau_browser_cli -v
```

Expected:

- porque `sau_cli.py`  ainda não tem `xiaohongshu` a ramificação e os campos unificados ainda não existem

- [ ] **Step 4: commitar a estrutura de testes**

```powershell
git add tests/test_sau_browser_cli.py
git commit -m "test: define browser cli unification contract"
```

## Task 2: ajustar o `sau_cli.py` e completar os parâmetros unificados e as rotas do Xiaohongshu

**Files:**
- Modify: `sau_cli.py`
- Reference: `uploader/xiaohongshu_uploader/main.py`
- Reference: `uploader/douyin_uploader/main.py`
- Reference: `uploader/ks_uploader/main.py`

- [ ] **Step 1: acrescentar os dataclasses de requisição do Xiaohongshu**

Em `sau_cli.py`, acrescentar:

```python
@dataclass(slots=True)
class XiaohongshuVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class XiaohongshuNoteUploadRequest:
    account_name: str
    image_files: list[Path]
    title: str
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
```

- [ ] **Step 2: reformar os dataclasses de requisição de Douyin e Kuaishou**

padronizar os campos neste modelo:

```python
class DouyinVideoUploadRequest:
    title: str
    description: str

class DouyinNoteUploadRequest:
    title: str
    note: str

class KuaishouVideoUploadRequest:
    title: str
    description: str

class KuaishouNoteUploadRequest:
    title: str
    note: str
```

requisitos:

- o vídeo usa `description`
- o post usa `note`
- a requisição de post deixa de ter só o campo histórico `note` semântica, mas sem `title`

- [ ] **Step 3: ajustar o parser**

Em `build_parser()`, concluir:

- `douyin upload-video` acrescentar `--desc`
- `kuaishou upload-video` acrescentar `--desc`
- `douyin upload-note` passa a ser `--title --note`
- `kuaishou upload-note` passa a ser `--title --note`
- criar o conjunto completo `xiaohongshu`: 
  - `login`
  - `check`
  - `upload-video --title --desc --tags --thumbnail`
  - `upload-note --images --title --note --tags`

- [ ] **Step 4: acrescentar as funções de conta do Xiaohongshu**

Em `sau_cli.py`, acrescentar:

```python
async def login_xiaohongshu_account(account_name: str, headless: bool = True) -> dict: ...
async def check_xiaohongshu_account(account_name: str) -> bool: ...
async def upload_xiaohongshu_video(request: XiaohongshuVideoUploadRequest) -> Path: ...
async def upload_xiaohongshu_note(request: XiaohongshuNoteUploadRequest) -> Path: ...
```

requisitos:

- o caminho da conta continua vindo de `resolve_account_file("xiaohongshu", account_name)`
- login e checagem reaproveitam, respectivamente, `xiaohongshu_setup` e `cookie_auth`
- antes de enviar, faz `setup(handle=False)` validação

- [ ] **Step 5: ajustar o dispatch**

requisitos:

- as três plataformas de navegador imprimem o mesmo:
  - `login` quando dá certo, imprime o caminho do arquivo de conta
  - `check` saída `valid` / `invalid`
  - `upload-video` imprime um resumo curto
  - `upload-note` imprime um resumo com a quantidade de imagens
- request montar o mapeamento unificado:
  - vídeo: `title + description`
  - post: `title + note`

- [ ] **Step 6: rodar os testes da CLI e confirmar que passam**

Run:

```powershell
py -3 -m unittest tests.test_sau_browser_cli -v
```

Expected:

- `BrowserCliParserTests`
- `BrowserCliDispatchTests`

tudo passa

- [ ] **Step 7: rodar a conferência mínima da ajuda**

Run:

```powershell
py -3 sau_cli.py douyin --help
py -3 sau_cli.py kuaishou --help
py -3 sau_cli.py xiaohongshu --help
py -3 sau_cli.py xiaohongshu upload-note --help
```

Expected:

- o subcomando do Xiaohongshu existe
- o comando de post mostra `--title`, `--note`
- o comando de vídeo mostra `--desc`

- [ ] **Step 8: commitar a CLI principal**

```powershell
git add sau_cli.py tests/test_sau_browser_cli.py
git commit -m "feat: unify browser cli contracts"
```

## Task 3: fazer a ligação mínima de campos nos uploaders

**Files:**
- Modify: `uploader/douyin_uploader/main.py`
- Modify: `uploader/ks_uploader/main.py`
- Modify: `uploader/xiaohongshu_uploader/main.py`
- Modify: `tests/test_xiaohongshu_uploader.py`

- [ ] **Step 1: ligar no vídeo do Douyin o `desc`**

Em `DouYinVideo.__init__()`, acrescentar o parâmetro `desc` e o `self.desc`; a lógica de preenchimento da página de publicação passa a ser:

```python
await self.fill_title_and_description(page, self.title, self.desc or self.title, self.tags)
```

- [ ] **Step 2: ligar no post do Douyin o `title + note`**

Em `DouYinNote.__init__()`, acrescentar o parâmetro `title` e manter o `note` como texto do post; o preenchimento da página de publicação passa a ser:

```python
await self.fill_title_and_description(page, self.title, self.note, self.tags)
```

requisitos:

- `title` obrigatório
- `note` opcional, mas convém não ficar vazio; se a lógica atual exigir valor, mantenha a validação

- [ ] **Step 3: ligar no vídeo do Kuaishou o `desc`**

Em `KSVideo.__init__()`, acrescentar o parâmetro `desc` e o `self.desc`; ao preencher a área de descrição, passa a ser:

```python
await page.keyboard.type(self.desc or self.title)
```

- [ ] **Step 4: ligar no post do Kuaishou o `title + note`**

Em `KSNote.__init__()`, acrescentar o parâmetro `title` e o `self.title`, mantendo o `self.note` como texto.

requisitos:

- na validação do envio de post, acrescentar `title` obrigatório
- se a página só tem a área do texto, sem campo de título separado, mesmo assim a CLI, a requisição e o construtor mantêm o `title` para as próximas plataformas ficarem alinhadas

- [ ] **Step 5: ver se a ligação da CLI do Xiaohongshu precisa de alguma adaptação**

confirmar `XiaoHongShuVideo` / `XiaoHongShuNote` basta este mapeamento:

```python
title=request.title
desc=request.description  # vídeo
desc=request.note         # post de imagens
```

se `XiaoHongShuNote`  ainda mantém o histórico `note` por compatibilidade: não apague, só faça a CLI usar primeiro o `title + note + tags`.

- [ ] **Step 6: acrescentar um teste de mapeamento do Xiaohongshu**

Em `tests/test_xiaohongshu_uploader.py`, acrescentar a asserção mínima:

```python
def test_note_title_defaults_do_not_override_explicit_title(self):
    app = xhs_main.XiaoHongShuNote(
        image_paths=["a.png"],
        note="texto",
        tags=[],
        publish_date=0,
        account_file="account.json",
        title="título explícito",
        desc="texto do post",
    )
    self.assertEqual(app.title, "título explícito")
    self.assertEqual(app.desc, "texto do post")
```

- [ ] **Step 7: rodar os testes dos uploaders**

Run:

```powershell
py -3 -m unittest tests.test_xiaohongshu_uploader -v
```

Expected:

- os testes unitários do uploader do Xiaohongshu passam

- [ ] **Step 8: commitar a ligação dos uploaders**

```powershell
git add uploader/douyin_uploader/main.py uploader/ks_uploader/main.py uploader/xiaohongshu_uploader/main.py tests/test_xiaohongshu_uploader.py
git commit -m "feat: align browser uploader metadata fields"
```

## Task 4: criar a skill do Xiaohongshu e atualizar junto as de Douyin e Kuaishou

**Files:**
- Create: `skills/xiaohongshu-upload/SKILL.md`
- Create: `skills/xiaohongshu-upload/references/runtime-requirements.md`
- Create: `skills/xiaohongshu-upload/references/cli-contract.md`
- Create: `skills/xiaohongshu-upload/references/troubleshooting.md`
- Create: `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.ps1`
- Create: `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.sh`
- Create: `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_cli_template.py`
- Modify: `skills/douyin-upload/SKILL.md`
- Modify: `skills/douyin-upload/references/cli-contract.md`
- Modify: `skills/douyin-upload/scripts/examples/douyin_commands.ps1`
- Modify: `skills/douyin-upload/scripts/examples/douyin_commands.sh`
- Modify: `skills/douyin-upload/scripts/examples/douyin_cli_template.py`
- Modify: `skills/kuaishou-upload/SKILL.md`
- Modify: `skills/kuaishou-upload/references/cli-contract.md`
- Modify: `skills/kuaishou-upload/scripts/examples/kuaishou_commands.ps1`
- Modify: `skills/kuaishou-upload/scripts/examples/kuaishou_commands.sh`
- Modify: `skills/kuaishou-upload/scripts/examples/kuaishou_cli_template.py`

- [ ] **Step 1: copiar a estrutura de pastas de uma skill existente como esqueleto do Xiaohongshu**

requisitos:

- no mesmo estilo `skills/douyin-upload/`
- por padrão, usar `sau xiaohongshu ...`
- deixar claro o que o Xiaohongshu aceita:
  - `login`
  - `check`
  - `upload-video`
  - `upload-note`

- [ ] **Step 2: escrever o contrato da CLI do Xiaohongshu**

deixar claro pelo menos:

```bash
sau xiaohongshu login --account <account>
sau xiaohongshu check --account <account>
sau xiaohongshu upload-video --account <account> --file <video> --title "<title>" [--desc "..."] [--tags ...]
sau xiaohongshu upload-note --account <account> --images <img...> --title "<title>" [--note "..."] [--tags ...]
```

- [ ] **Step 3: atualizar os contratos das skills de Douyin e Kuaishou**

requisitos:

- o comando de exemplo do vídeo ganha o `--desc`
- o comando de exemplo do post passa a ser `--title --note`
- todos os modelos mudam junto; não mude só a documentação e deixe os scripts para trás

- [ ] **Step 4: conferir os arquivos das skills**

Run:

```powershell
Get-ChildItem skills\xiaohongshu-upload -Recurse
Get-Content skills\douyin-upload\references\cli-contract.md
Get-Content skills\kuaishou-upload\references\cli-contract.md
```

Expected:

- a pasta da skill do Xiaohongshu está completa
- os contratos das skills de Douyin e Kuaishou já usam o novo modelo de parâmetros

- [ ] **Step 5: commitar as mudanças das skills**

```powershell
git add skills/xiaohongshu-upload skills/douyin-upload skills/kuaishou-upload
git commit -m "feat: add xiaohongshu skill and align browser skill contracts"
```

## Task 5: atualizar exemplos, README e documentação

**Files:**
- Modify: `examples/get_xiaohongshu_cookie.py`
- Modify: `examples/upload_video_to_xiaohongshu.py`
- Modify: `README.md`
- Modify: `docs/CLI.md`
- Modify: `docs/install.md`
- Modify: `docs/update.md`

- [ ] **Step 1: ajustar os exemplos do Xiaohongshu**

requisitos:

- `examples/get_xiaohongshu_cookie.py` apontando claramente para `sau xiaohongshu login --account <account_name>`  como caminho principal
- `examples/upload_video_to_xiaohongshu.py` explicar que o caminho atual é a CLI
- se o exemplo que chama o uploader direto for mantido, diga no comentário que é entrada de depuração / caminho histórico

- [ ] **Step 2: atualizar a tabela de plataformas e o início rápido do README**

README mudar pelo menos estes pontos:

- na tabela de capacidades, o Xiaohongshu passa a ser:
  - `CLI ✅`
  - `Skill ✅`
- os comandos das plataformas de navegador no início rápido passam para o contrato unificado
- os exemplos de post de Douyin e Kuaishou passam a ser:

```bash
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "título do post" --note "texto do post"
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png --title "título do post" --note "texto do post"
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png --title "título do post" --note "texto do post"
```

- [ ] **Step 3: atualizar `docs/CLI.md`**

requisitos:

- acrescentar a seção do `xiaohongshu`
- deixar a explicação das três plataformas de navegador igual:
  - vídeo: `title + desc + tags`
  - post: `title + note + tags`
- acrescentar o Xiaohongshu à explicação do QR code de login

- [ ] **Step 4: atualizar `docs/install.md` e `docs/update.md`**

requisitos:

- no documento de instalação, acrescentar `sau xiaohongshu --help`
- no documento de atualização, acrescentar os comandos de conferência e o caminho da skill do Xiaohongshu
- a documentação escreve sempre `account_name`

- [ ] **Step 5: conferir documentação e exemplos**

Run:

```powershell
Get-Content README.md | Select-String -Pattern "xiaohongshu|upload-note|--note|--desc" -Context 1,2
Get-Content docs\CLI.md | Select-String -Pattern "xiaohongshu|--note|--desc" -Context 1,2
Get-Content docs\install.md | Select-String -Pattern "xiaohongshu" -Context 1,2
Get-Content docs\update.md | Select-String -Pattern "xiaohongshu" -Context 1,2
```

Expected:

- README, CLI, install, update todos mostram a CLI do Xiaohongshu
- o texto do post é escrito como `--note`
- a descrição do vídeo é escrita como `--desc`

- [ ] **Step 6: rodar a verificação final mínima**

Run:

```powershell
py -3 -m unittest tests.test_sau_browser_cli tests.test_xiaohongshu_uploader -v
py -3 sau_cli.py xiaohongshu --help
py -3 sau_cli.py xiaohongshu upload-video --help
py -3 sau_cli.py xiaohongshu upload-note --help
```

Expected:

- os testes unitários passam
- a ajuda da CLI do Xiaohongshu existe
- o comando de vídeo mostra `--desc`
- o comando de post mostra `--note`

- [ ] **Step 7: commit de encerramento**

```powershell
git add examples/get_xiaohongshu_cookie.py examples/upload_video_to_xiaohongshu.py README.md docs/CLI.md docs/install.md docs/update.md
git commit -m "docs: align browser cli docs and examples"
```
