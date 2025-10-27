# Rota Back-end

Serviço Flask responsável pelas operações de autenticação, fóruns e trilhas do projeto
Rota. Esta versão recebeu ajustes para operar em ambiente de produção mantendo os
parâmetros seguros configuráveis por variáveis de ambiente.

## Requisitos

- Python 3.12+
- PostgreSQL 13+ (para desenvolvimento rápido é possível usar SQLite)
- Redis 6+ para rate limiting distribuído (opcional, recomendado em produção)

## Configuração rápida

1. Crie e ative um virtualenv.
2. Instale as dependências: `pip install -r requirements.txt`
3. Copie o arquivo `.env.example` para `.env` e ajuste os valores.
4. Execute as migrações/tabelas iniciais conforme scripts existentes.
5. Suba o servidor: `flask --app app.main run` (ou simplesmente `make`, que roda o alvo `run`).

> O `make` já lê as variáveis do arquivo `.env`; se ele não existir, copie o `.env.example`.

## Variáveis de ambiente principais

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `DATABASE_URL` | opcional | URL completa do banco. Se ausente, o app monta usando as chaves `DB_*`. |
| `DB_ENGINE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS` | opcional | Componentes para montar a URL do banco. Em produção não utilize os valores padrão. |
| `JWT_SECRET` | **sim** | Chave usada para assinar sessões e tokens. Deve ter >=16 caracteres e não pode ser trivial. |
| `CSRF_SECRET` | recomendado | Segredo dedicado para assinar tokens CSRF. Obrigatório em produção. |
| `CORS_ALLOWED_ORIGINS` | opcional | Lista separada por vírgulas de origens permitidas. Defaults seguros para `localhost`. |
| `REDIS_URL` | recomendado | URL do Redis (`redis://user:pass@host:6379/0`). Se não informado cai no limitador em memória. |
| `AUTH_RATE_LIMIT_MAX_ATTEMPTS` | opcional | Tentativas permitidas por janela (default `10`). |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | opcional | Duração da janela de rate limiting (default `60`). |
| `SMTP_*` | opcional | Configurações de e-mail transactional. |
| `ENV` | opcional | Define o ambiente (`dev`, `staging`, `prod`). Em `prod` validações extras são aplicadas. |

> **Importante:** ao definir `ENV=prod` o aplicativo bloqueia o uso das credenciais padrão
> e exige `CSRF_SECRET`. Configure também HTTPS terminado no proxy ou load balancer
> para que os cookies seguros sejam ativados automaticamente.

### HTTPS com proxy Nginx

O `docker-compose.yml` inclui o serviço `proxy`, que termina TLS nas portas 80/443 e repassa o tráfego para a API Flask.
Para habilitar HTTPS coloque os certificados em `certs/` (diretório não versionado) com os nomes:

```
certs/
 ├─ server.crt   # certificado público (cadeia completa)
 └─ server.key   # chave privada correspondente
```

Depois suba (ou recrie) a stack:

```bash
docker compose -p rota_backend --env-file ../.env up -d --build --remove-orphans
```

Se utilizar a pipeline do GitHub Actions, certifique-se de que esses arquivos já existam na VPS antes de executar o deploy. Para ambientes públicos, use certificados válidos (ex.: Let's Encrypt) e mantenha o healthcheck interno em `http://127.0.0.1:8000/healthz`, expondo externamente `https://seu-dominio`.

### Servindo o front-end com o mesmo proxy

O serviço `proxy` também entrega o build do Vite. O arquivo `docker/proxy/nginx.conf` define dois hosts virtuais:

- `api.*` → proxy para a API Flask (`http://api:8000`)
- `app.*` → arquivos estáticos em `/usr/share/nginx/html`

Para publicar o front:

1. Gere/renove o certificado incluindo ambos os domínios (ex.: `api.72-61-32-2.nip.io` e `app.72-61-32-2.nip.io`). O `nip.io` é aceito pela Let's Encrypt e evita o limite que atingimos com `sslip.io`:
   ```bash
   sudo certbot certonly --standalone \
     -d api.72-61-32-2.nip.io \
     -d app.72-61-32-2.nip.io
   sudo cp /etc/letsencrypt/live/api.72-61-32-2.nip.io/fullchain.pem /opt/rota/backend/certs/server.crt
   sudo cp /etc/letsencrypt/live/api.72-61-32-2.nip.io/privkey.pem   /opt/rota/backend/certs/server.key
   sudo chmod 600 /opt/rota/backend/certs/server.key
   ```

2. Faça o build do front (no repositório `rota-frontend`):
   ```bash
   npm install
   npm run build
   ```
   Copie o resultado para `ROTA_Back/frontend_dist/` (diretório ignorado pelo git). Exemplo:
   ```bash
   rm -rf ../ROTA_Back/frontend_dist
   mkdir -p ../ROTA_Back/frontend_dist
   cp -r dist/* ../ROTA_Back/frontend_dist/
   ```
   No servidor, basta sincronizar a pasta `frontend_dist/` antes do deploy (ex.: `rsync -az dist/ usuario@servidor:/opt/rota/backend/releases/<release>/frontend_dist/`).

3. Reinicie os containers:
   ```bash
   cd ../ROTA_Back
   docker compose -p rota_backend --env-file ../.env up -d --build --remove-orphans
   ```

4. Atualize o backend (`CORS_ALLOWED_ORIGENS`) para incluir `https://app.72-61-32-2.nip.io` e configure o front (`VITE_API_BASE_URL`/`apiHost.json`) apontando para `https://api.72-61-32-2.nip.io`.

Com isso o portal fica acessível em `https://app.seu-dominio` e a API em `https://api.seu-dominio`, ambos servidos pelo mesmo Nginx com TLS.

## Rate limiting

O serviço aplica rate limiting nas rotas sensíveis (login, registro, reset de senha). Por
padrão utiliza um limitador em memória adequado para desenvolvimento. Quando `REDIS_URL`
está configurado, o backend usa uma janela fixa com `ZSET` em Redis, permitindo múltiplas
instâncias da aplicação sem perder o controle de tentativas.

## CORS e cookies

As origens permitidas agora são configuráveis e a aplicação ajusta automaticamente os
headers `Access-Control-Allow-*` e as flags de cookie (Secure/SameSite) conforme o
ambiente. Para produção, mantenha a lista de origens restrita aos domínios da aplicação
web.

## Testes

Execute a suíte com:

```bash
pytest -v --disable-warnings --maxfail=1
```

Considere rodar os testes em CI antes de todo deploy. Há também targets no `makefile`
para execução com `uvicorn`/`waitress` quando necessário.

### Testes de performance (k6)

O alvo `make k6` prepara e executa o teste de carga definido em
`performance/k6/performance.test.js`. Por padrão, os cenários que exercitam o
rate limit de login ficam desativados para evitar falhas decorrentes das
respostas `429` esperadas. Basta rodar:

```bash
make k6
```

Caso seja necessário validar o comportamento do rate limit, habilite o cenário
extra configurando a variável de ambiente `ENABLE_RATE_LIMIT_SCENARIOS`:

```bash
ENABLE_RATE_LIMIT_SCENARIOS=true make k6
```
