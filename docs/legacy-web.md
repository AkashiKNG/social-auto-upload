# A versão Web antiga

O código Web é basicamente:

- `sau_backend.py`
- `sau_backend/`
- `sau_frontend/`

Ele é de uma fase anterior do projeto e não é mais o caminho mantido.

## Onde isso se encaixa hoje

- fica como versão histórica
- serve de referência para a antiga forma de embrulhar a API e a Web
- não há garantia de que rode hoje
- não há garantia de que esteja em dia com o `uploader/` e o `sau_cli.py` atuais

## Por que explicar isso à parte

O projeto está sendo reestruturado, e o caminho atual é:

- `uploader/`: implementação central das plataformas
- `sau_cli.py`: entrada da CLI
- `skills/`: as skills voltadas a agentes

Por isso o README não apresenta mais a versão Web como entrada principal: assim ninguém novo pensa que ela é a forma mais estável de usar o projeto.

## Se você ainda quiser estudar a versão Web

Dá para olhar estes arquivos:

- `sau_backend/README.md`
- `sau_frontend/README.md`
- `sau_backend.py`

Mas espere o seguinte:

- o contrato dos endpoints pode não bater com o caminho atual
- a cobertura de plataformas pode estar atrás do `uploader/`
- as dependências e a forma de rodar podem exigir investigação sua

## Por onde começar hoje

Para usar o que o projeto faz hoje, veja:

- `uploader/`
- `sau_cli.py`
- `docs/CLI.md`
- `skills/douyin-upload/SKILL.md`
