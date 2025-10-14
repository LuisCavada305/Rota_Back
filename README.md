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
5. Suba o servidor: `flask --app app.main run` (ou use o `make run` disponibilizado).

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
