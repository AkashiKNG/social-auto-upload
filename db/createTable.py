import sqlite3
import json
import os

# caminho do arquivo do banco (criado sozinho se não existir)
db_file = './database.db'

# se o banco já existir, dá para apagar as tabelas antigas (opcional)
# if os.path.exists(db_file):
#     os.remove(db_file)

# conecta ao SQLite (o arquivo é criado se não existir)
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# tabela de contas
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,  -- caminho do arquivo
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0
)
''')

# tabela de arquivos
cursor.execute('''CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- identificador de cada registro
    filename TEXT NOT NULL,               -- nome do arquivo
    filesize REAL,                     -- tamanho do arquivo (em MB)
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- data do envio, agora por padrão
    file_path TEXT                        -- caminho do arquivo
)
''')


# grava as mudanças
conn.commit()
print("✅ tabelas criadas")
# fecha a conexão
conn.close()
