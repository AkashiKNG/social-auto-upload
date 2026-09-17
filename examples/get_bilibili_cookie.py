from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conf import BASE_DIR


if __name__ == "__main__":
    # o melhor é rodar este script num terminal de verdade.
    # se o QR code sair cortado no terminal, abra o qrcode.png da pasta atual.
    cli_path = Path(BASE_DIR) / "sau_cli.py"
    subprocess.run(
        [
            sys.executable,
            str(cli_path),
            "bilibili",
            "login",
            "--account",
            "creator",
        ],
        check=True,
    )
