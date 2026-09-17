# Login
# O melhor é o próprio usuário rodar num terminal de verdade.
# Se o QR code sair cortado no terminal, abra o qrcode.png da pasta atual.
$account = "account_a"
# account_name is user-defined. One account_name maps to one account file.
# You can prepare multiple account names and run them in parallel.

sau bilibili login --account $account

# Checagem
sau bilibili check --account $account

# Envio de vídeo
sau bilibili upload-video `
  --account $account `
  --file .\videos\demo.mp4 `
  --title "Bilibili CLI Demo" `
  --desc "Bilibili CLI Demo" `
  --tid 249 `
  --tags futebol,teste `
  --schedule "2026-03-26 16:00"
