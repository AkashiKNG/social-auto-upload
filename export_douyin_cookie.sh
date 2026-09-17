#!/bin/bash
# export_douyin_cookie.sh
# exporta o cookie do Douyin de um Chrome já logado para douyin_{8 caracteres aleatórios}.json
# usa curl direto na API HTTP do Chrome DevTools

set -e

# lê os parâmetros
USERNAME=""
while [ $# -gt 0 ]; do
    case "$1" in
        --account)
            USERNAME="$2"
            shift 2
            ;;
        *)
            echo "uso: $0 --account <nome-da-conta>"
            exit 1
            ;;
    esac
done

if [ -z "$USERNAME" ]; then
    echo "nenhuma conta informada; o nome do arquivo será aleatório"
fi

DEBUG_PORT=9222

echo "=========================================="
echo "   Exportador de cookie do Douyin"
echo "=========================================="
echo ""

# dependências: curl, python3, websocket-client

echo "conferindo o Chrome remote debugging..."
RESPONSE=$(curl -s "http://localhost:${DEBUG_PORT}/json" 2>/dev/null) || true

if ! echo "$RESPONSE" | grep -q "webSocketDebuggerUrl"; then
    echo "o Chrome remote debugging não está rodando"
    echo "abra o Chrome antes: chromium --remote-debugging-port=9222 ..."
    exit 1
fi

echo "Chrome remote debugging rodando"
echo ""
echo "pegando o cookie do Douyin..."

USERNAME="$USERNAME" python3 << 'PYEOF'
import json
import os
import uuid
import sys

# o shell passa USERNAME como variável de ambiente; o Python precisa lê-la
USERNAME = os.environ.get('USERNAME', '')

DEBUG_PORT = 9222
if USERNAME:
    COOKIE_FILE = f"cookies/douyin_{USERNAME}.json"
else:
    COOKIE_FILE = f"cookies/douyin_{uuid.uuid4().hex[:8]}.json"

def get_douyin_cookies():
    import urllib.request
    import websocket

    # lista as páginas abertas
    url = f"http://localhost:{DEBUG_PORT}/json"
    with urllib.request.urlopen(url, timeout=10) as response:
        pages = json.loads(response.read().decode())

    # procura a página da central do criador do Douyin
    douyin_page = None
    for page in pages:
        page_url = page.get("url", "")
        if "creator.douyin.com" in page_url:
            douyin_page = page
            break

    if not douyin_page:
        print("não achei a página da plataforma de criação do Douyin")
        print("abra e entre em https://creator.douyin.com no Chrome antes")
        return False

    page_url = douyin_page["url"]
    ws_url = douyin_page.get("webSocketDebuggerUrl", "")

    print(f"página encontrada: {page_url}")

    # conecta no WebSocket da página
    print(f"conectando no WebSocket da página...")
    ws = websocket.create_connection(ws_url, timeout=30)

    # pega todos os cookies
    ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
    response = json.loads(ws.recv())

    cookies = response.get("result", {}).get("cookies", [])

    # filtra os cookies do Douyin
    douyin_cookies = [
        c for c in cookies
        if "douyin.com" in c.get("domain", "") or ".douyin.com" in c.get("domain", "")
    ]

    print(f"peguei {len(douyin_cookies)} cookies do Douyin")

    if len(douyin_cookies) == 0:
        print("nenhum cookie do Douyin; provavelmente a conta não está logada")
        return False

    # pega o localStorage (origins)
    print(f"pegando o localStorage...")
    local_storage_by_origin = {}

    # pega a árvore de frames da página
    ws.send(json.dumps({"id": 2, "method": "Page.getResourceTree"}))
    resp = json.loads(ws.recv())
    frames = resp.get("result", {}).get("frameTree", {}).get("childFrames", [])
    all_frames = [resp.get("result", {}).get("frameTree", {})] + frames

    for frame in all_frames:
        frame_url = frame.get("url", "")
        frame_id = frame.get("id", "")
        if "douyin.com" in frame_url or "bytedance.com" in frame_url:
            # roda JavaScript para pegar o localStorage do frame
            script = """
            (function() {
                var result = [];
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    result.push([key, localStorage.getItem(key)]);
                }
                return result;
            })()
            """
            ws.send(json.dumps({
                "id": 3,
                "method": "Runtime.evaluate",
                "params": {"expression": script, "contextId": frame.get("id")}
            }))
            resp = json.loads(ws.recv())
            result_eval = resp.get("result", {})
            if result_eval.get("result", {}).get("type") == "array":
                items = result_eval.get("result", {}).get("value", [])
                if items:
                    origin = frame_url.rsplit("/", 2)[0] + "//" + frame_url.split("/")[2]
                    local_storage_by_origin[origin] = items

    # pega o localStorage do documento principal
    script_main = """
    (function() {
        var result = [];
        try {
            for (var i = 0; i < localStorage.length; i++) {
                var key = localStorage.key(i);
                result.push([key, localStorage.getItem(key)]);
            }
        } catch(e) {}
        return result;
    })()
    """
    ws.send(json.dumps({
        "id": 4,
        "method": "Runtime.evaluate",
        "params": {"expression": script_main}
    }))
    resp = json.loads(ws.recv())
    result_eval = resp.get("result", {})
    if result_eval.get("result", {}).get("type") == "array":
        items = result_eval.get("result", {}).get("value", [])
        if items:
            origin = page_url.rsplit("/", 2)[0] + "//" + page_url.split("/")[2]
            local_storage_by_origin[origin] = items

    ws.close()

    # monta o JSON
    result = {
        "cookies": [],
        "origins": []
    }

    for c in douyin_cookies:
        result["cookies"].append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "expires": c.get("expires", -1),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", True),
            "sameSite": c.get("sameSite", "Lax")
        })

    # acrescenta os origins
    for origin, items in local_storage_by_origin.items():
        origin_entry = {
            "origin": origin,
            "localStorage": [{"name": name, "value": value} for name, value in items]
        }
        result["origins"].append(origin_entry)

    # salva
    os.makedirs("cookies", exist_ok=True)
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"cookie salvo em: {COOKIE_FILE}")
    print("")

    # mostra os cookies principais
    key_cookies = ["sessionid", "uid_tt", "ssid", "ttwid"]
    print("cookies principais:")
    for c in douyin_cookies:
        if c.get("name") in key_cookies:
            val = c.get("value", "")
            if len(val) > 30:
                val = val[:30] + "..."
            print(f"   {c.get('name')}: {val}")

    return True

if __name__ == "__main__":
    if not get_douyin_cookies():
        sys.exit(1)
PYEOF

echo ""
echo "=========================================="
echo "   pronto! arquivo exportado para $COOKIE_FILE"
echo "=========================================="