# Avaliação de Segurança, Performance e Dimensionamento do Banco

## Segurança (Nota 8.5/10)

### Pontos positivos
- **Senhas com bcrypt e sessões assinadas:** o serviço usa `passlib.hash.bcrypt` para armazenar senhas e assina tokens JWT com expiração, reduzindo o impacto de vazamentos do banco ou interceptação de cookies.【F:app/services/security.py†L8-L52】
- **Cookies protegidos e verificação dupla de CSRF:** o cookie de sessão é marcado como `HttpOnly` e só fica `Secure` fora do ambiente de desenvolvimento, enquanto mutações exigem o token CSRF igualado entre cookie e cabeçalho, evitando requisições forjadas básicas.【F:app/services/security.py†L31-L91】【F:app/services/security.py†L99-L141】
- **Validações com Pydantic em rotas sensíveis:** fluxos como autenticação, fóruns e formulários validam payloads com modelos tipados antes de prosseguir, reduzindo risco de dados inesperados chegarem à camada de ORM.【F:app/routes/auth.py†L27-L86】【F:app/routes/forums.py†L55-L149】【F:app/routes/trail_items.py†L28-L179】

### Pontos de atenção
- **Rate limiting ainda volátil:** o bloqueio por IP vive em memória do processo; um pool com múltiplos workers/instâncias pode burlar o limite sem uma store centralizada.【F:app/services/rate_limiter.py†L8-L47】
- **Rotação e segregação de segredos:** apesar da chave CSRF dedicada, ainda não há política definida para renovação periódica ou armazenamento seguro (cofre) das chaves de aplicação.【F:app/services/security.py†L53-L66】
- **Superfícies adicionais sem sanitização:** descrições de trilhas, respostas de formulários e outros campos textuais continuam dependentes do front-end para escapar HTML.【F:app/routes/trail_items.py†L180-L334】
- **Ausência de MFA/refresh tokens curtos:** a plataforma ainda depende de um único cookie JWT de longa duração sem mecanismos extras de revogação ou autenticação forte.【F:app/services/security.py†L37-L91】

### Recomendações prioritárias
1. Persistir e compartilhar métricas de rate limiting (Redis/Memcached) entre instâncias para manter proteção sob escala horizontal.【F:app/services/rate_limiter.py†L8-L47】
2. Definir processo de rotação periódica para `JWT_SECRET` e `CSRF_SECRET` (ex.: semestral) e centralizar armazenamento em cofre (AWS Secrets Manager, HashiCorp Vault).【F:app/services/security.py†L53-L66】
3. Estender sanitização para demais superfícies de entrada textual (respostas de formulários, descrições de itens) ou garantir saída escapeada em todos os clientes.【F:app/services/sanitizer.py†L1-L35】【F:app/routes/trail_items.py†L180-L334】

### Recomendações adicionais
- Implementar logs estruturados e alertas para tentativas excessivas de login e respostas 4xx/5xx.
- Avaliar short-lived refresh tokens ou lista de revogação para invalidar sessões comprometidas.
- Documentar política de complexidade de senha e monitorar dependências de segurança (ex.: `passlib`).

## Performance (Nota 8/10)

### Pontos positivos
- **Paginação em listagens volumosas:** rotas de trilhas, seções, itens e fóruns limitam o número de registros retornados, mitigando respostas gigantes e uso de memória no servidor.【F:app/routes/trails.py†L75-L138】【F:app/routes/trails.py†L150-L193】【F:app/routes/forums.py†L160-L236】
- **Uso de carregamento seletivo no ORM:** `selectinload`, `joinedload` e `load_only` aparecem em consultas críticas, reduzindo N+1 e tráfego de dados desnecessários.【F:app/routes/me.py†L27-L56】【F:app/routes/trails.py†L17-L193】
- **Regras de progressão otimizadas:** cálculos de progresso reaproveitam registros existentes e limitam saltos em vídeos, evitando reprocessamento pesado e garantindo consistência de dados mesmo sob carga.【F:app/routes/trails.py†L199-L333】
- **QR Codes com cache LRU:** certificados reutilizam data URIs previamente gerados, amortizando custos de CPU/IO em acessos repetitivos.【F:app/routes/certificates.py†L1-L56】

### Pontos de atenção
- **Contagens agregadas frequentes nos fóruns:** múltiplos `COUNT` correlacionados por requisição podem degradar sob alto volume; índices específicos e cache curto podem ser necessários.【F:app/repositories/ForumsRepository.py†L54-L174】
- **Cache de QR Codes ainda local:** o LRU vive em memória de cada worker; reinícios ou múltiplas instâncias perdem o benefício sem um backend compartilhado.【F:app/routes/certificates.py†L1-L56】
- **Tarefas de escrita seguem síncronas:** atualizações de progresso, matrículas e submissões de formulários ocorrem na thread principal, sem filas/background para volumes grandes.【F:app/routes/trail_items.py†L212-L334】【F:app/routes/user_trails.py†L68-L115】

### Recomendações prioritárias
1. Criar índices compostos (ex.: `forum_id, created_at`) e materializar contagens em tabelas auxiliares ou cache in-memory para aliviar `COUNT` correlacionado.
2. Promover o cache de QR Codes para um backend compartilhado (Redis/CDN) e pré-geração via job assíncrono para certidões mais acessadas.【F:app/routes/certificates.py†L1-L56】
3. Monitorar latência por endpoint (APM, Prometheus) para identificar gargalos reais e dimensionar horizontalmente conforme necessário.

### Recomendações adicionais
- Revisar planos de execução periodicamente (explain analyze) e ajustar limites de paginação máximos conforme comportamento real.
- Avaliar compressão de payloads HTTP (gzip/br) para listas de itens/trilhas.
- Desacoplar atualizações de progresso em lote usando worker/cron se o número de usuários simultâneos crescer.

## Dimensionamento estimado do banco de dados

### Premissas utilizadas
- Plataforma com **5.000 alunos ativos**, cada um inscrito em média em **3 trilhas** com **40 itens** (vídeo/documento/formulário) e 5 sessões por trilha.
- Uso de PostgreSQL com armazenamento em blocos de 8 kB e sobrecarga ~30% para índices/TOAST.
- Campos textuais moderados (URLs, descrições curtas) e ausência de anexos binários no banco.

### Estimativa de volume
| Tabela | Linhas estimadas | Tamanho médio por linha | Espaço com índices |
| --- | --- | --- | --- |
| `users` | 5.000 | ~0,6 kB (dados + índices email/username) | **~4 MB** |
| `user_trails` | 15.000 | ~0,35 kB (FK + timestamps + índice composto) | **~8 MB** |
| `user_item_progress` | 200.000 | ~0,45 kB (FK + status + timestamps) | **~120 MB** |
| `trail_items` + metadados (sections, requirements etc.) | 1.200 | ~1,0 kB | **~2 MB** |
| Conteúdo de fóruns (`forum_topics`, `forum_posts`) | 50.000 | ~0,7 kB (conteúdo textual curto) | **~35 MB** |
| Formulários e respostas (`form_submissions` + respostas) | 20.000 | ~0,6 kB | **~12 MB** |
| **Total estimado** | — | — | **~181 MB** |

Adicionando 30% de folga para crescimento orgânico, autovacuum, índices extras e WAL, o banco deve permanecer **abaixo de ~240 MB** nesse cenário.

### O free tier é suficiente?
- Free tiers comuns de PostgreSQL (Render, Supabase, Railway, ElephantSQL) oferecem entre **250 MB e 1 GB** de armazenamento. Com as premissas acima, o consumo estimado (~240 MB) **encosta no limite inferior**.
- Explosões pontuais (ex.: picos de posts ou submissões) podem ultrapassar o teto rapidamente porque WAL/backups também contam para a cota. Além disso, free tiers limitam CPU/RAM e conexões, impactando a performance sob carga moderada.

**Conclusão:** para um piloto pequeno (até ~3.000 usuários ou menor engajamento), o free tier pode aguentar temporariamente. No entanto, para 5.000 usuários ativos como no cenário acima, recomenda-se migrar para um plano básico pago (>=1 GB) antes do lançamento para evitar bloqueios por falta de espaço e garantir recursos de CPU/IO suficientes.
