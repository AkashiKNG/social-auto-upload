import asyncio
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from queue import Queue
from flask_cors import CORS
from myUtils.auth import check_cookie
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from werkzeug.utils import secure_filename
from conf import BASE_DIR
from myUtils.login import get_tencent_cookie, douyin_cookie_gen, get_ks_cookie, xiaohongshu_cookie_gen
from myUtils.postVideo import post_video_tencent, post_video_DouYin, post_video_ks, post_video_xhs

active_queues = {}
app = Flask(__name__)

# libera CORS para qualquer origem
CORS(app)

# limite de 160 MB por upload
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024

# pasta atual (onde ficam index.html e assets)
current_dir = os.path.dirname(os.path.abspath(__file__))

# serve os arquivos estáticos (para quando virar um pacote)
@app.route('/assets/<filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), filename)

# serve o favicon.ico (para quando virar um pacote)
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

@app.route('/vite.svg')
def vite_svg():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

# (para quando virar um pacote)
@app.route('/')
def index():  # put application's code here
    return send_from_directory(current_dir, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400
    try:
        # salva o arquivo no lugar certo
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        safe_name = secure_filename(file.filename)
        if not safe_name:
            return jsonify({"code": 400, "data": None, "msg": "Invalid filename"}), 400
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{safe_name}")
        file.save(filepath)
        return jsonify({"code":200,"msg": "File uploaded successfully", "data": f"{uuid_v1}_{safe_name}"}), 200
    except Exception as e:
        return jsonify({"code":500,"msg": str(e),"data":None}), 500

@app.route('/getFile', methods=['GET'])
def get_file():
    # lê o parâmetro filename
    filename = request.args.get('filename')

    if not filename:
        return jsonify({"code": 400, "msg": "filename is required", "data": None}), 400

    # evita path traversal
    if '..' in filename or filename.startswith('/'):
        return jsonify({"code": 400, "msg": "Invalid filename", "data": None}), 400

    # monta o caminho completo
    file_path = str(Path(BASE_DIR / "videoFile"))

    # devolve o arquivo
    return send_from_directory(file_path,filename)


@app.route('/uploadSave', methods=['POST'])
def upload_save():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400

    # nome personalizado vindo do formulário (opcional)
    custom_filename = request.form.get('filename', None)
    if custom_filename:
        filename = secure_filename(custom_filename + "." + file.filename.split('.')[-1])
    else:
        filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"code": 400, "data": None, "msg": "Invalid filename"}), 400

    try:
        # gera um UUID v1
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")

        # monta nome e caminho do arquivo
        final_filename = f"{uuid_v1}_{filename}"
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{filename}")

        # salva o arquivo
        file.save(filepath)

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO file_records (filename, filesize, file_path)
            VALUES (?, ?, ?)
                                ''', (filename, round(float(os.path.getsize(filepath)) / (1024 * 1024),2), final_filename))
            conn.commit()
            print("✅ upload registrado")

        return jsonify({
            "code": 200,
            "msg": "File uploaded and saved successfully",
            "data": {
                "filename": filename,
                "filepath": final_filename
            }
        }), 200

    except Exception as e:
        print(f"Upload failed: {e}")
        return jsonify({
            "code": 500,
            "msg": f"upload failed: {e}",
            "data": None
        }), 500

@app.route('/getFiles', methods=['GET'])
def get_all_files():
    try:
        # with cuida de fechar a conexão com o banco
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row  # permite acessar o resultado pelo nome da coluna
            cursor = conn.cursor()

            # busca todos os registros
            cursor.execute("SELECT * FROM file_records")
            rows = cursor.fetchall()

            # transforma em lista de dicionários e separa o UUID
            data = []
            for row in rows:
                row_dict = dict(row)
                # tira o UUID do file_path (primeira parte do nome, antes do _)
                if row_dict.get('file_path'):
                    file_path_parts = row_dict['file_path'].split('_', 1)  # quebra só no primeiro _
                    if len(file_path_parts) > 0:
                        row_dict['uuid'] = file_path_parts[0]  # parte do UUID
                    else:
                        row_dict['uuid'] = ''
                else:
                    row_dict['uuid'] = ''
                data.append(row_dict)

            return jsonify({
                "code": 200,
                "msg": "success",
                "data": data
            }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("get file failed!"),
            "data": None
        }), 500


@app.route("/getAccounts", methods=['GET'])
def getAccounts():
    """Lista as contas rapidamente, sem validar os cookies."""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM user_info''')
            rows = cursor.fetchall()
            rows_list = [list(row) for row in rows]

            print("\n📋 conteúdo atual da tabela (consulta rápida):")
            for row in rows:
                print(row)

            return jsonify(
                {
                    "code": 200,
                    "msg": None,
                    "data": rows_list
                }), 200
    except Exception as e:
        print(f"erro ao listar as contas: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"não consegui listar as contas: {str(e)}",
            "data": None
        }), 500


@app.route("/getValidAccounts",methods=['GET'])
async def getValidAccounts():
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM user_info''')
        rows = cursor.fetchall()
        rows_list = [list(row) for row in rows]
        print("\n📋 conteúdo atual da tabela:")
        for row in rows:
            print(row)
        for row in rows_list:
            flag = await check_cookie(row[1],row[2])
            if not flag:
                row[4] = 0
                cursor.execute('''
                UPDATE user_info 
                SET status = ? 
                WHERE id = ?
                ''', (0,row[0]))
                conn.commit()
                print("✅ sessão do usuário atualizada")
        for row in rows:
            print(row)
        return jsonify(
                        {
                            "code": 200,
                            "msg": None,
                            "data": rows_list
                        }),200

@app.route('/deleteFile', methods=['GET'])
def delete_file():
    file_id = request.args.get('id')

    if not file_id or not file_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing file ID",
            "data": None
        }), 400

    try:
        # abre a conexão com o banco
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # busca o registro que será apagado
            cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found",
                    "data": None
                }), 404

            record = dict(record)

            # pega o caminho e apaga o arquivo de verdade
            file_path = Path(BASE_DIR / "videoFile" / record['file_path'])
            if file_path.exists():
                try:
                    file_path.unlink()  # apaga o arquivo
                    print(f"✅ arquivo apagado: {file_path}")
                except Exception as e:
                    print(f"⚠️ não consegui apagar o arquivo: {e}")
                    # mesmo sem apagar o arquivo, remove o registro para o banco não ficar inconsistente
            else:
                print(f"⚠️ o arquivo não existe: {file_path}")

            # apaga o registro do banco
            cursor.execute("DELETE FROM file_records WHERE id = ?", (file_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "File deleted successfully",
            "data": {
                "id": record['id'],
                "filename": record['filename']
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500

@app.route('/deleteAccount', methods=['GET'])
def delete_account():
    account_id = request.args.get('id')

    if not account_id or not account_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing account ID",
            "data": None
        }), 400

    account_id = int(account_id)

    try:
        # abre a conexão com o banco
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # busca o registro que será apagado
            cursor.execute("SELECT * FROM user_info WHERE id = ?", (account_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found",
                    "data": None
                }), 404

            record = dict(record)

            # apaga o arquivo de cookies da conta
            if record.get('filePath'):
                cookie_file_path = Path(BASE_DIR / "cookiesFile" / record['filePath'])
                if cookie_file_path.exists():
                    try:
                        cookie_file_path.unlink()
                        print(f"✅ arquivo de cookies apagado: {cookie_file_path}")
                    except Exception as e:
                        print(f"⚠️ não consegui apagar o arquivo de cookies: {e}")

            # apaga o registro do banco
            cursor.execute("DELETE FROM user_info WHERE id = ?", (account_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account deleted successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"delete failed: {str(e)}",
            "data": None
        }), 500


# endpoint de login por SSE
@app.route('/login')
def login():
    # 1 Xiaohongshu, 2 Canal do WeChat, 3 Douyin, 4 Kuaishou
    type = request.args.get('type')
    # nome da conta
    id = request.args.get('id')

    # fila usada para a comunicação assíncrona
    status_queue = Queue()
    active_queues[id] = status_queue

    def on_close():
        print(f"limpando a fila: {id}")
        del active_queues[id]
    # sobe a thread da tarefa assíncrona
    thread = threading.Thread(target=run_async_function, args=(type,id,status_queue), daemon=True)
    thread.start()
    response = Response(sse_stream(status_queue,), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # importante: desliga o buffer do Nginx
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/postVideo', methods=['POST'])
def postVideo():
    # lê o JSON da requisição
    data = request.get_json()

    if not data:
        return jsonify({"code": 400, "msg": "o corpo da requisição não pode ser vazio", "data": None}), 400

    # tira fileList e accountList do JSON
    file_list = data.get('fileList', [])
    account_list = data.get('accountList', [])
    type = data.get('type')
    title = data.get('title')
    tags = data.get('tags')
    category = data.get('category')
    enableTimer = data.get('enableTimer')
    if category == 0:
        category = None
    productLink = data.get('productLink', '')
    productTitle = data.get('productTitle', '')
    thumbnail_path = data.get('thumbnail', '')
    is_draft = data.get('isDraft', False)  # parâmetro novo: salvar como rascunho

    videos_per_day = data.get('videosPerDay')
    daily_times = data.get('dailyTimes')
    start_days = data.get('startDays')

    # validação dos parâmetros
    if not file_list:
        return jsonify({"code": 400, "msg": "a lista de arquivos não pode ser vazia", "data": None}), 400
    if not account_list:
        return jsonify({"code": 400, "msg": "a lista de contas não pode ser vazia", "data": None}), 400
    if not type:
        return jsonify({"code": 400, "msg": "o tipo de plataforma não pode ser vazio", "data": None}), 400
    if not title:
        return jsonify({"code": 400, "msg": "o título não pode ser vazio", "data": None}), 400

    # mostra os dados recebidos (só para acompanhar)
    print("File List:", file_list)
    print("Account List:", account_list)

    try:
        match type:
            case 1:
                post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days)
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days, is_draft)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, thumbnail_path, productLink, productTitle)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
            case _:
                return jsonify({"code": 400, "msg": f"tipo de plataforma não suportado: {type}", "data": None}), 400

        # responde ao cliente
        return jsonify(
            {
                "code": 200,
                "msg": "tarefa de publicação enviada",
                "data": None
            }), 200
    except Exception as e:
        print(f"erro ao publicar o vídeo: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"falha na publicação: {str(e)}",
            "data": None
        }), 500


@app.route('/updateUserinfo', methods=['POST'])
def updateUserinfo():
    # lê o JSON da requisição
    data = request.get_json()

    # tira type e userName do JSON
    user_id = data.get('id')
    type = data.get('type')
    userName = data.get('userName')
    try:
        # abre a conexão com o banco
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # atualiza o registro no banco
            cursor.execute('''
                           UPDATE user_info
                           SET type     = ?,
                               userName = ?
                           WHERE id = ?;
                           ''', (type, userName, user_id))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account update successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("update failed!"),
            "data": None
        }), 500

@app.route('/postVideoBatch', methods=['POST'])
def postVideoBatch():
    data_list = request.get_json()

    if not isinstance(data_list, list):
        return jsonify({"code": 400, "msg": "Expected a JSON array", "data": None}), 400
    for data in data_list:
        # tira fileList e accountList do JSON
        file_list = data.get('fileList', [])
        account_list = data.get('accountList', [])
        type = data.get('type')
        title = data.get('title')
        tags = data.get('tags')
        category = data.get('category')
        enableTimer = data.get('enableTimer')
        if category == 0:
            category = None
        productLink = data.get('productLink', '')
        productTitle = data.get('productTitle', '')
        is_draft = data.get('isDraft', False)

        videos_per_day = data.get('videosPerDay')
        daily_times = data.get('dailyTimes')
        start_days = data.get('startDays')
        # mostra os dados recebidos (só para acompanhar)
        print("File List:", file_list)
        print("Account List:", account_list)
        match type:
            case 1:
                post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                               start_days)
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days, is_draft)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, productLink, productTitle)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
    # responde ao cliente
    return jsonify(
        {
            "code": 200,
            "msg": None,
            "data": None
        }), 200

# API de envio do arquivo de cookies
@app.route('/uploadCookie', methods=['POST'])
def upload_cookie():
    try:
        if 'file' not in request.files:
            return jsonify({
                "code": 400,
                "msg": "não encontrei o arquivo de cookies",
                "data": None
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "code": 400,
                "msg": "o nome do arquivo de cookies não pode ser vazio",
                "data": None
            }), 400

        if not file.filename.endswith('.json'):
            return jsonify({
                "code": 400,
                "msg": "o arquivo de cookies precisa estar em JSON",
                "data": None
            }), 400

        # dados da conta
        account_id = request.form.get('id')
        platform = request.form.get('platform')

        if not account_id or not platform:
            return jsonify({
                "code": 400,
                "msg": "faltou o id da conta ou a plataforma",
                "data": None
            }), 400

        # caminho do arquivo da conta, vindo do banco
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT filePath FROM user_info WHERE id = ?', (account_id,))
            result = cursor.fetchone()

        if not result:
            return jsonify({
                "code": 500,
                "msg": "conta não encontrada",
                "data": None
            }), 404

        # salva o arquivo de cookies enviado no caminho certo
        cookie_file_path = Path(BASE_DIR / "cookiesFile" / result['filePath'])
        cookie_file_path.parent.mkdir(parents=True, exist_ok=True)

        file.save(str(cookie_file_path))

        # dá para atualizar a conta no banco aqui (data de atualização, por exemplo)
        # se precisar de mais alguma coisa, é aqui

        return jsonify({
            "code": 200,
            "msg": "arquivo de cookies enviado",
            "data": None
        }), 200

    except Exception as e:
        print(f"erro ao enviar o arquivo de cookies: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"não consegui enviar o arquivo de cookies: {str(e)}",
            "data": None
        }), 500


# API de download do arquivo de cookies
@app.route('/downloadCookie', methods=['GET'])
def download_cookie():
    try:
        file_path = request.args.get('filePath')
        if not file_path:
            return jsonify({
                "code": 500,
                "msg": "faltou o parâmetro com o caminho do arquivo",
                "data": None
            }), 400

        # confere o caminho para evitar path traversal
        cookie_file_path = Path(BASE_DIR / "cookiesFile" / file_path).resolve()
        base_path = Path(BASE_DIR / "cookiesFile").resolve()

        if not cookie_file_path.is_relative_to(base_path):
            return jsonify({
                "code": 500,
                "msg": "caminho de arquivo inválido",
                "data": None
            }), 400

        if not cookie_file_path.exists():
            return jsonify({
                "code": 500,
                "msg": "o arquivo de cookies não existe",
                "data": None
            }), 404

        # devolve o arquivo
        return send_from_directory(
            directory=str(cookie_file_path.parent),
            path=cookie_file_path.name,
            as_attachment=True
        )

    except Exception as e:
        print(f"erro ao baixar o arquivo de cookies: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"não consegui baixar o arquivo de cookies: {str(e)}",
            "data": None
        }), 500


# roda a função assíncrona dentro de uma thread
def run_async_function(type,id,status_queue):
    match type:
        case '1':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(xiaohongshu_cookie_gen(id, status_queue))
            loop.close()
        case '2':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_tencent_cookie(id,status_queue))
            loop.close()
        case '3':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(douyin_cookie_gen(id,status_queue))
            loop.close()
        case '4':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_ks_cookie(id,status_queue))
            loop.close()

# gerador do fluxo SSE
def sse_stream(status_queue):
    while True:
        if not status_queue.empty():
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
        else:
            # evita fritar a CPU
            time.sleep(0.1)

if __name__ == '__main__':
    app.run(host='0.0.0.0' ,port=5409)
