# Controle de Estoque (Controle de Ovos)

Aplicação Flask para gestão de estoque de ovos, entradas/saídas e relatórios.

## Como rodar localmente (Windows)

1. Instalar Python 3.11
2. No terminal:
   - `cd "C:\\Users\\lucas\\Desktop\\Controle de Ovos"`
   - `python -m venv venv`
   - `venv\\Scripts\\activate`
   - `pip install -r requirements.txt`
   - `set SECRET_KEY=uma_chave_secreta_forte` (ou definir no painel do Windows)
   - `python app.py`

3. Abrir `http://localhost:5000` no navegador (desktop ou celular na mesma rede).

## Empacotar como executável (Windows)

1. `pip install pyinstaller`
2. `pyinstaller --onefile app.py`
3. Vai gerar `dist\\app.exe`
4. Execute `dist\\app.exe` e abra `http://localhost:5000`

## Rodar em Docker (recomendado para servidor)

1. `docker build -t controle-estoque .`
2. `docker run -d -p 5000:5000 controle-estoque`
3. Acesse `http://localhost:5000` ou `http://<IP_do_servidor>:5000` no celular.

## Hospedar com domínio (controledeestoque.com)

1. Configure servidor (VPS/Droplet/EC2) com Docker ou Python.
2. Use Nginx de proxy reverso de `80/443` para `localhost:5000`.
3. Use `certbot` para HTTPS.
4. Configure domínio apontando A para IP do servidor.

## Tornar PWA (adicionar à tela inicial)

1. Criar `manifest.json` e `service-worker.js`.
2. Incluir no HTML:
   - `<link rel="manifest" href="/manifest.json">`
   - `<meta name="theme-color" content="#667eea">`
3. O navegador oferecerá opção `Adicionar à tela inicial` em mobile.
