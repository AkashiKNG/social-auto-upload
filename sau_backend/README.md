## Como rodar o projeto

Versão do Python: 3.10

1. Instale as dependências

    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

2. Apague o `database.db` da pasta `db` (se ele não existir, é só rodar o `createTable.py`) e rode o `createTable.py` para recriar o banco, evitando dados sujos
3. Ajuste o `LOCAL_CHROME_PATH`, no fim do `conf.py`, para o caminho do Chrome na sua máquina
4. Rode o `sau_backend.py` da raiz
5. Campo `type` (identificador da plataforma): 1 Xiaohongshu, 2 Channels, 3 Douyin, 4 Kuaishou

## Endpoints

1. `/upload` (post)
    endpoint de envio; quando dá certo, devolve o id único do arquivo, usado depois para publicar o vídeo
2. `/login`, com os parâmetros `id` (nome de usuário) e `type` (identificador da plataforma): fluxo de login — o front e o back abrem uma conexão SSE, o back devolve a imagem em base64 ao front, e depois que o QR code é escaneado o back grava no banco e responde 200; o front fecha a conexão e chama o `/getValidAccounts` para listar as contas disponíveis
3. `/getValidAccounts` devolve todos os cookies válidos no momento; é lento, porque valida um por um. `status` 1 é válido, 0 é cookie inválido
4. `/postVideo` publica o vídeo; post com JSON
    file_list      o identificador único devolvido pelo `/upload`
    account_list   o campo `filePath` devolvido pelo `/getValidAccounts`
    type           identificador da plataforma
    title          título do vídeo
    tags           lista de tags do vídeo, sem o `#`
    category       segundo o autor original, indica conteúdo próprio: 0 é não original e qualquer outro valor é original — mas nos testes esse campo não teve efeito
    enableTimer    liga a publicação agendada; desligado por padrão, passe True para ligar. Ligado, os três campos abaixo são obrigatórios; desligado, não envie nenhum deles
    videos_per_day quantos vídeos publicar por dia
    daily_times    horários de publicação no dia, lista de inteiros, do mesmo tamanho da lista acima
    start_days     dia de início: 0 começa amanhã, 1 começa depois de amanhã
    os três campos acima são o meu entendimento; não sei se está certo nem por que o autor original os montou assim

## Banco de dados

Veja a pasta `db` aqui do lado: o arquivo `.py` é o script de criação e o arquivo `.db` é o banco SQLite.

## Arquivos

- pasta `cookiesFile`: guarda os arquivos de cookie
- pasta `myUtils`: módulos Python próprios
- pasta `videoFile`: onde os arquivos enviados ficam
- pasta `web`: as rotas web
- `conf.py`: configuração geral; lembre de ajustar o `LOCAL_CHROME_PATH` para o navegador da sua máquina
