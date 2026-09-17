# Bilibili CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dar ao Bilibili o mesmo nível de Douyin e Kuaishou: a CLI `sau`, um runtime que atualiza o `biliup` sozinho, a skill correspondente e a documentação completa, com o agradecimento ao projeto de origem.

**Architecture:** manter leve, sem criar um framework grande. Entra um módulo de execução do Bilibili para conferir o GitHub Release, baixar e atualizar o `biliup` e executar os comandos; o `sau_cli.py` só ganha o subcomando `bilibili` e o mapeamento de parâmetros; skill, exemplo e os documentos README/CLI/install/update seguem a estrutura que Douyin e Kuaishou já têm.

**Tech Stack:** Python 3.10+, `requests`, `argparse`, `asyncio`, `subprocess`, `pathlib`, `unittest`, GitHub Releases, existing `biliup` integration

---

## File Structure

### New files

- `uploader/bilibili_uploader/runtime.py`
  - Bilibili entrada do runtime
  - responsável por conferir, baixar, atualizar e executar o `biliup` automaticamente
- `tests/__init__.py`
  - inicialização do pacote de testes
- `tests/test_bilibili_runtime.py`
  - testa a atualização automática, o download, o reaproveitamento do cache e o comportamento do executor
- `tests/test_sau_bilibili_cli.py`
  - testes `sau bilibili` parser  e do dispatch
- `skills/bilibili-upload/SKILL.md`
  - explicação principal da skill da CLI do Bilibili
- `skills/bilibili-upload/references/runtime-requirements.md`
  - pré-requisitos e explicação do download automático
- `skills/bilibili-upload/references/cli-contract.md`
  - `sau bilibili ...` contrato dos comandos
- `skills/bilibili-upload/references/troubleshooting.md`
  - problemas comuns e investigação
- `skills/bilibili-upload/scripts/examples/bilibili_commands.ps1`
  - PowerShell comandos de exemplo
- `skills/bilibili-upload/scripts/examples/bilibili_commands.sh`
  - shell comandos de exemplo
- `skills/bilibili-upload/scripts/examples/bilibili_cli_template.py`
  - Python modelo de chamada

### Modified files

- `sau_cli.py`
  - acrescenta o subcomando `bilibili`
  - reaproveita `resolve_account_file()`, `parse_tags()` e `parse_schedule()`
- `examples/get_bilibili_cookie.py`
  - alinhar com o novo `sau bilibili login` uso
- `examples/upload_video_to_bilibili.py`
  - alinhar com a nova convenção de CLI e de arquivo de conta
- `README.md`
  - acrescentar o uso da CLI do Bilibili, a explicação do download automático e o agradecimento
- `docs/CLI.md`
  - acrescenta `sau bilibili login/check/upload-video`
- `docs/install.md`
  - explicar o download automático e a primeira execução do Bilibili
- `docs/update.md`
  - explicar a atualização automática do Bilibili

## Task 1: Bilibili runtime com atualização automática

**Files:**
- Create: `uploader/bilibili_uploader/runtime.py`
- Create: `tests/__init__.py`
- Create: `tests/test_bilibili_runtime.py`

- [ ] **Step 1: escrever os testes do runtime do Bilibili**

usa `unittest`, cobrindo estes caminhos mínimos:

```python
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from uploader.bilibili_uploader.runtime import (
    build_biliup_runtime_path,
    ensure_biliup_binary,
    run_biliup_command,
)


class BiliupRuntimeTests(unittest.TestCase):
    def test_build_biliup_runtime_path_returns_platform_path(self):
        path = build_biliup_runtime_path("Windows")
        self.assertTrue(str(path).endswith("biliup.exe"))

    @patch("uploader.bilibili_uploader.runtime.fetch_latest_release")
    def test_ensure_biliup_binary_downloads_when_missing(self, mock_release):
        mock_release.return_value = {
            "tag_name": "v1.0.0",
            "asset_url": "https://example.invalid/biliup.exe",
            "asset_name": "biliup.exe",
        }
        with patch("uploader.bilibili_uploader.runtime.download_biliup_asset") as mock_download:
            ensure_biliup_binary(force_check=True)
        mock_download.assert_called_once()

    @patch("uploader.bilibili_uploader.runtime.fetch_latest_release")
    def test_ensure_biliup_binary_reuses_local_when_up_to_date(self, mock_release):
        mock_release.return_value = {
            "tag_name": "v1.0.0",
            "asset_url": "https://example.invalid/biliup.exe",
            "asset_name": "biliup.exe",
        }
        with patch("uploader.bilibili_uploader.runtime.read_local_biliup_version", return_value="v1.0.0"):
            with patch("uploader.bilibili_uploader.runtime.download_biliup_asset") as mock_download:
                ensure_biliup_binary(force_check=True)
        mock_download.assert_not_called()

    @patch("uploader.bilibili_uploader.runtime.subprocess.run")
    def test_run_biliup_command_returns_completed_process(self, mock_run):
        mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")
        result = run_biliup_command(["login"])
        self.assertEqual(result.returncode, 0)
```

- [ ] **Step 2: rodar os testes e confirmar que falham primeiro**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_bilibili_runtime -v
```

Expected:

- porque `uploader.bilibili_uploader.runtime` ainda não existe

- [ ] **Step 3: escrever a implementação mínima do runtime**

Em `uploader/bilibili_uploader/runtime.py`, acrescentar estas funções mínimas:

```python
def get_biliup_runtime_root() -> Path: ...
def build_biliup_runtime_path(system_name: str | None = None) -> Path: ...
def fetch_latest_release() -> dict: ...
def read_local_biliup_version() -> str | None: ...
def write_local_biliup_version(version: str) -> None: ...
def download_biliup_asset(release: dict, destination: Path) -> Path: ...
def ensure_biliup_binary(force_check: bool = True) -> Path: ...
def run_biliup_command(arguments: list[str]) -> subprocess.CompletedProcess[str]: ...
```

Restrições:

- sem manifesto complicado
- apontar direto para a release mais nova no GitHub
- na máquina ficam só a string da versão atual e o binário
- manter simples a lógica de caminho, rede e substituição

- [ ] **Step 4: rodar os testes do runtime de novo e confirmar que passam**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_bilibili_runtime -v
```

Expected:

- todos os `BiliupRuntimeTests` passam

- [ ] **Step 5: commitar este passo**

```powershell
git add uploader/bilibili_uploader/runtime.py tests/__init__.py tests/test_bilibili_runtime.py
git commit -m "feat: add biliup runtime bootstrap"
```

## Task 2: integrar a CLI `sau bilibili`

**Files:**
- Modify: `sau_cli.py`
- Create: `tests/test_sau_bilibili_cli.py`
- Reference: `uploader/bilibili_uploader/main.py`
- Reference: `utils/constant.py`

- [ ] **Step 1: escrever os testes do parser e do dispatch da CLI**

Em `tests/test_sau_bilibili_cli.py`, cobrir:

```python
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import sau_cli


class BilibiliCliTests(unittest.TestCase):
    def test_build_parser_accepts_bilibili_login(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["bilibili", "login", "--account", "creator"])
        self.assertEqual(args.platform, "bilibili")
        self.assertEqual(args.action, "login")

    def test_build_parser_requires_tid_for_upload_video(self):
        parser = sau_cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "bilibili", "upload-video",
                "--account", "creator",
                "--file", "demo.mp4",
                "--title", "hello",
                "--desc", "hello",
            ])

    def test_dispatch_bilibili_check_prints_valid(self):
        args = Namespace(platform="bilibili", action="check", account="creator")
        with patch("sau_cli.check_bilibili_account", new=AsyncMock(return_value=True)):
            code = asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(code, 0)
```

- [ ] **Step 2: rodar os testes e confirmar que falham primeiro**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sau_bilibili_cli -v
```

Expected:

- porque o `sau_cli.py` ainda não tem a ramificação de parser e dispatch do `bilibili`

- [ ] **Step 3: acrescentar no `sau_cli.py` o modelo de requisição e os comandos do Bilibili**

fazer só o mínimo, no mesmo estilo de Douyin e Kuaishou:

```python
@dataclass(slots=True)
class BilibiliVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tid: int
    tags: list[str]
    publish_date: datetime | int
    debug: bool = True


async def login_bilibili_account(account_name: str) -> dict: ...
async def check_bilibili_account(account_name: str) -> bool: ...
async def upload_bilibili_video(request: BilibiliVideoUploadRequest) -> Path: ...
```

Requisitos mínimos do parser:

- `sau bilibili login --account <name>`
- `sau bilibili check --account <name>`
- `sau bilibili upload-video --account ... --file ... --title ... --desc ... --tid ... [--tags] [--schedule]`

Requisitos mínimos do dispatch:

- imprime como as outras plataformas `valid` / `invalid`
- depois do envio bem-sucedido, imprime um resumo curto

- [ ] **Step 4: reaproveitar a semântica de parâmetros do Bilibili que já existe**

no wrapper do Bilibili, reaproveitar os conceitos que o projeto já tem:

- `tid` obrigatório
- `tags` usa o `parse_tags()`
- `schedule` continua usando `parse_schedule()`
- `account` continua resolvendo por `resolve_account_file("bilibili", account_name)` resolve o caminho do arquivo de conta dentro do projeto

- [ ] **Step 5: rodar os testes da CLI de novo e confirmar que passam**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sau_bilibili_cli -v
```

Expected:

- `BilibiliCliTests` passam

- [ ] **Step 6: fazer um teste conjunto**

Run:

```powershell
.\.venv\Scripts\python.exe sau_cli.py bilibili --help
.\.venv\Scripts\python.exe sau_cli.py bilibili upload-video --help
```

Expected:

- dá para ver `login` / `check` / `upload-video`
- em `upload-video`, o `--tid` aparece como obrigatório

- [ ] **Step 7: commitar este passo**

```powershell
git add sau_cli.py tests/test_sau_bilibili_cli.py
git commit -m "feat: add bilibili cli commands"
```

## Task 3: criar a skill e o exemplo

**Files:**
- Create: `skills/bilibili-upload/SKILL.md`
- Create: `skills/bilibili-upload/references/runtime-requirements.md`
- Create: `skills/bilibili-upload/references/cli-contract.md`
- Create: `skills/bilibili-upload/references/troubleshooting.md`
- Create: `skills/bilibili-upload/scripts/examples/bilibili_commands.ps1`
- Create: `skills/bilibili-upload/scripts/examples/bilibili_commands.sh`
- Create: `skills/bilibili-upload/scripts/examples/bilibili_cli_template.py`
- Modify: `examples/get_bilibili_cookie.py`
- Modify: `examples/upload_video_to_bilibili.py`

- [ ] **Step 1: montar a skill do Bilibili seguindo a estrutura das skills de Douyin e Kuaishou**

requisitos:

- `SKILL.md` no mesmo estilo das duas skills que já existem
- por padrão, usar primeiro `sau bilibili ...`
- deixar escrito que o programa prepara o `biliup` sozinho

- [ ] **Step 2: escrever os arquivos de comandos de exemplo**

os comandos de exemplo incluem pelo menos:

```powershell
sau bilibili login --account creator
sau bilibili check --account creator
sau bilibili upload-video --account creator --file .\videos\demo.mp4 --title "demo" --desc "demo" --tid 249 --tags futebol,testes
```

- [ ] **Step 3: ajustar os exemplos locais**

fazer estes exemplos apontarem claramente para a entrada e a convenção novas:

- `examples/get_bilibili_cookie.py`
- `examples/upload_video_to_bilibili.py`

requisitos:

- o usuário não precisa mais adivinhar o caminho do `biliup.exe`
- deixar claro que agora o recomendado é usar `sau bilibili ...`
- manter `VideoZoneTypes`  como exemplo de uso

- [ ] **Step 4: conferir os arquivos**

Run:

```powershell
Get-ChildItem skills\bilibili-upload -Recurse
Get-Content examples\get_bilibili_cookie.py
Get-Content examples\upload_video_to_bilibili.py
```

Expected:

- a pasta da skill do Bilibili está completa
- o conteúdo dos exemplos já aponta para a nova CLI e a nova explicação

- [ ] **Step 5: commitar este passo**

```powershell
git add skills/bilibili-upload examples/get_bilibili_cookie.py examples/upload_video_to_bilibili.py
git commit -m "feat: add bilibili upload skill"
```

## Task 4: documentação e agradecimento ao projeto de origem

**Files:**
- Modify: `README.md`
- Modify: `docs/CLI.md`
- Modify: `docs/install.md`
- Modify: `docs/update.md`

- [ ] **Step 1: acrescentar o uso da CLI do Bilibili no README**

deixar claro pelo menos:

- `sau bilibili login`
- `sau bilibili check`
- `sau bilibili upload-video`
- download e atualização automáticos do `biliup`

- [ ] **Step 2: acrescentar o contrato dos comandos na documentação da CLI**

escrever a seção do Bilibili no mesmo estilo das de Douyin e Kuaishou:

- tabela de parâmetros
- `tid` obrigatório
- `schedule`  e seu comportamento

- [ ] **Step 3: deixar claro o mecanismo de download automático nos documentos de instalação e atualização**

acrescentar ao menos estas explicações:

- o usuário não precisa instalar o `biliup`
- a primeira execução baixa sozinha
- as execuções seguintes conferem se há atualização

- [ ] **Step 4: incluir na documentação o agradecimento e a menção ao projeto de origem**

acrescentar ao menos um parágrafo claro no README:

- Bilibili a capacidade vem do `biliup`
- agradecer e creditar o projeto de origem
- informar o endereço do projeto

texto sugerido:

```markdown
## Agradecimentos

A capacidade de envio ao Bilibili deste projeto é construída sobre o projeto de código aberto `biliup`.
Obrigado ao projeto `biliup` e a quem contribui com ele pela base oferecida:

- https://github.com/biliup/biliup
```

- [ ] **Step 5: conferir a documentação**

Run:

```powershell
Get-Content README.md | Select-String -Pattern "bilibili|biliup|Agradecimentos" -Context 1,2
Get-Content docs\CLI.md | Select-String -Pattern "bilibili" -Context 1,3
Get-Content docs\install.md | Select-String -Pattern "bilibili|biliup" -Context 1,2
Get-Content docs\update.md | Select-String -Pattern "bilibili|biliup" -Context 1,2
```

Expected:

- README, CLI, install e update trazem o conteúdo novo do Bilibili
- README traz o agradecimento explícito ao projeto de origem

- [ ] **Step 6: rodar a verificação final**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_bilibili_runtime tests.test_sau_bilibili_cli -v
.\.venv\Scripts\python.exe sau_cli.py bilibili --help
.\.venv\Scripts\python.exe sau_cli.py bilibili upload-video --help
```

Expected:

- os testes unitários passam
- Bilibili CLI a ajuda funciona
- o `upload-video` mostra o `--tid` como obrigatório

- [ ] **Step 7: commit de encerramento**

```powershell
git add README.md docs/CLI.md docs/install.md docs/update.md
git commit -m "docs: add bilibili cli guidance and attribution"
```
