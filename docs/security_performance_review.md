# Avaliação de Segurança e Performance

## Segurança (Nota 8/10)

### Pontos Positivos
- **Hashing de senhas com bcrypt:** garante que credenciais comprometidas não sejam armazenadas em texto puro, reduzindo o impacto em caso de vazamento de banco de dados.
- **JWT com expiração curta:** tokens possuem validade limitada, o que diminui a janela de uso indevido caso um token seja interceptado.
- **Cookies `HttpOnly` e `Secure`:** o token de autenticação é enviado ao cliente em um cookie inacessível via JavaScript e apenas por HTTPS, bloqueando ataques básicos de XSS e sniffing.
- **Proteção dupla contra CSRF:** cada login/registro emite um token assinado armazenado em cookie dedicado e validado em cabeçalho nos endpoints mutáveis, blindando a aplicação contra requisições forjadas.

### Pontos Negativos
- **Tokens de sessão ainda dependem de segredo único:** embora a assinatura HMAC proteja o token, o segredo global permanece ponto único de falha.
- **Validações de entrada limitadas em payloads legados:** alguns fluxos antigos continuam aceitando campos livres sem validação rigorosa, abrindo espaço para comportamentos inesperados caso sejam expostos.

### Recomendações de Melhoria
- Rotacionar periodicamente o segredo JWT/CSRF e armazená-lo em cofre seguro para reduzir impacto de vazamentos.
- Reforçar validações de entrada com esquemas (p.ex. Pydantic) para garantir formatos esperados e bloquear dados maliciosos remanescentes.
- Auditar fluxos de autorização buscando privilégios excessivos ou respostas informativas demais em erros.

## Performance (Nota 8/10)

### Pontos Positivos
- **Paginação nos endpoints de trilhas e seções:** limita o volume de dados retornados em cada requisição, reduzindo tráfego e latência.
- **Paginação por itens de seção:** endpoints que retornam conteúdos extensos agora respeitam limites configuráveis por página, evitando explosão de carga em seções muito grandes.
- **Uso de `selectinload`/`joinedload`:** evita o problema de N+1 consultas em carregamento de relacionamentos, melhorando a eficiência no banco de dados.
- **Persistência leve em repositórios:** consultas utilizam filtros diretos sem lógica de negócios desnecessária, diminuindo overhead na camada de aplicação.

### Pontos Negativos
- **Monitoramento limitado:** ainda não há métricas de observabilidade em produção, dificultando detectar gargalos antes que afetem usuários.
- **Processamento síncrono pesado:** tarefas potencialmente demoradas (ex.: geração de relatórios ou uploads) seguem na thread principal, bloqueando o servidor.

### Recomendações de Melhoria
- Instrumentar métricas de latência e throughput, incluindo logs estruturados, para direcionar otimizações futuras e detectar regressões.
- Revisar e criar índices nas colunas mais consultadas, além de monitorar o banco com métricas de tempo de consulta e cache.
- Avaliar uso de filas/worker assíncrono para tarefas pesadas e considerar caching em camadas quentes (por exemplo, Redis) para respostas repetidas.
