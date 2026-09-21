# Treino Express · Guia completo

## 1. Resumo do sistema

O Treino Express é uma plataforma multi-tenant para academias. O aluno recebe um
treino curto e personalizado, acompanha o descanso entre exercícios e pode usar
uma jukebox social. A academia acompanha alunos, telas, receitas, anúncios,
ranking e lembretes de reativação.

O sistema é dividido em:

```text
Navegador (Next.js)
        │ REST / WebSocket
        ▼
API FastAPI ─── PostgreSQL + RLS
        │
        ├── Redis (fila, eventos da TV e estado em tempo real)
        ├── Spotify Web API (busca e metadados)
        └── WhatsApp Cloud API (lembretes, quando configurada)
```

O PostgreSQL é a fonte de verdade. Redis acelera eventos em tempo real, mas não
substitui os registros persistidos.

## 2. Recursos atuais

### Aplicativo do aluno

- Geração de treino por duração e foco muscular.
- Execução exercício a exercício, cronômetro de descanso e anúncios.
- Ajuste de exercício, carga, séries e descanso.
- Resumo e avaliação do treino.
- Progresso, volume, frequência e metas por exercício.
- Ranking por treinos ou volume, somente para alunos que optarem por participar.
- Jukebox da academia: busca, pedido e fila de músicas para a TV.
- Biblioteca pessoal de músicas do Spotify.
- Busca de playlists públicas do Spotify.
- Histórico persistente de playlists salvas, com seleção e remoção.
- Player oficial do Spotify, interativo e persistente ao navegar para o treino.

### Painel da academia

- Resumo operacional e financeiro.
- Lista de alunos e situação de pagamento.
- Telas pareadas e fila da jukebox.
- Página de lembretes de sequência.
- Envio real pelo WhatsApp ou modo simulado quando as credenciais estão vazias.

### TV da academia

- Recebe anúncios, fila e música atual por WebSocket.
- Confirma impressões de anúncios.
- Exibe QR Codes de cupons e atualiza o estado da jukebox em tempo real.

### Painel do anunciante

- Campanhas, métricas, cupons e faturamento.

## 3. Tecnologias e segurança

| Camada | Tecnologia |
| --- | --- |
| API | FastAPI, Pydantic, SQLAlchemy assíncrono |
| Banco | PostgreSQL 16 |
| Isolamento | Row Level Security (RLS) por academia |
| Tempo real | Redis e WebSocket |
| Web | Next.js, React, TypeScript e CSS Modules |
| Música | Spotify Web API + Spotify Embed |
| Deploy web | Vercel |
| Deploy API | Docker Compose + Cloudflare Tunnel |

Existem duas roles de banco:

- `treino_app`: usada pela API e sujeita ao RLS.
- `treino`: superusuário usado somente por migrations e seeds.

Nunca configure a API para usar a role de migrations.

## 4. Como o Spotify funciona

A API usa Client Credentials para pesquisar faixas e playlists públicas e ler
metadados. Ela não recebe a senha do aluno e não funciona como proxy de áudio.

O áudio é reproduzido pelo player oficial incorporado do Spotify. Por isso:

- o aluno precisa clicar em Play;
- uma conta Spotify e, em alguns casos, Premium podem ser necessários;
- playlists privadas não aparecem na busca pública;
- o player continua montado no layout do aluno ao navegar entre jukebox e treino;
- fechar a aba ou recarregar a página pode interromper a reprodução;
- uma playlist pode ser salva no histórico, mas músicas individuais são salvas
  pela busca de músicas.

O player guarda a seleção atual no `localStorage` para recuperar a faixa ou
playlist na próxima navegação do mesmo navegador.

## 5. Rotas principais

### Aluno

| Método | Rota | Função |
| --- | --- | --- |
| `POST` | `/v1/treinos/gerar` | Gera um treino |
| `POST` | `/v1/treinos/{id}/descanso` | Inicia um descanso |
| `POST` | `/v1/treinos/{id}/exercicio/{ordem}/concluir` | Conclui exercício |
| `GET` | `/v1/progresso` | Retorna evolução e metas |
| `PUT` | `/v1/progresso/metas` | Cria ou altera uma meta |
| `GET` | `/v1/ranking` | Consulta o ranking |
| `GET` | `/v1/jukebox/busca?q=...` | Busca músicas |
| `GET` | `/v1/jukebox/playlists?q=...` | Busca playlists públicas |
| `GET` | `/v1/jukebox/biblioteca` | Lista músicas salvas |
| `POST` | `/v1/jukebox/biblioteca` | Salva uma música |
| `DELETE` | `/v1/jukebox/biblioteca/{spotify_id}` | Remove uma música |
| `GET` | `/v1/jukebox/biblioteca/playlists` | Lista playlists salvas |
| `POST` | `/v1/jukebox/biblioteca/playlists` | Salva uma playlist |
| `DELETE` | `/v1/jukebox/biblioteca/playlists/{spotify_id}` | Remove uma playlist |
| `POST` | `/v1/jukebox/pedidos` | Pede música para a TV |
| `GET` | `/v1/jukebox/fila` | Consulta a fila da academia |

### Academia e tempo real

O painel usa as rotas de `/v1/academia`. A TV conecta em:

```text
WSS /ws/tv/{academia_id}?token=<jwt-da-tela>
```

Eventos importantes: `ad.show`, `ad.impression`, `jukebox.now`,
`jukebox.queue`, `screen.pause` e heartbeat.

## 6. Banco de dados e migrations

As migrations ficam em `alembic/versions/`:

- `0001`: schema inicial.
- `0002`–`0007`: roles, RLS, TV, treino e progresso.
- `0008`: metas, ranking e lembretes.
- `0009`: biblioteca pessoal de músicas.
- `0010`: histórico de playlists salvas.

Depois de qualquer alteração de schema:

```bash
uv run alembic upgrade head
```

Em produção, o `docker-compose.prod.yml` executa esse comando antes de iniciar
a API.

## 7. Instalação local

Pré-requisitos: Docker, Python 3.12, `uv`, Node.js e npm.

```bash
# Banco e Redis do ambiente local
cd ../treino-express-handoff/infra
docker compose up -d

# API
cd ../../treino-express-app
uv sync
cp .env.example .env
uv run alembic upgrade head
PYTHONPATH=. uv run python scripts/seed_catalogo_exercicios.py
make dev
```

Em outro terminal:

```bash
cd web
npm install
cp .env.local.example .env.local  # se o arquivo de exemplo existir
npm run dev
```

Se não houver arquivo de exemplo, crie `web/.env.local`:

```dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Acesse:

- Web: `http://localhost:3000`
- Swagger: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Para testes manuais com login demo, ative `ENABLE_DEMO_LOGIN=true` somente no
ambiente local. O token também pode ser gerado por:

```bash
PYTHONPATH=. uv run python scripts/gerar_token_dev.py <academia_id> <aluno_id>
```

## 8. Configuração do Spotify

1. Crie um app em `developer.spotify.com/dashboard`.
2. Copie o Client ID e Client Secret.
3. Preencha somente no `.env` da API:

```dotenv
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_MARKET=BR
```

4. Verifique a integração:

```bash
PYTHONPATH=. uv run python scripts/testar_spotify.py
```

Nunca faça commit do Client Secret.

## 9. Deploy

### API

Em um servidor com Docker:

```bash
cp .env.prod.example .env.prod
# Preencha senhas, JWT_SECRET, CORS_ORIGINS e token do Cloudflare Tunnel
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

O serviço da API aplica migrations automaticamente e sobe na porta interna
8000. O Cloudflare Tunnel é o ponto público de entrada.

### Frontend

O projeto web está conectado à Vercel. Cada push na branch `main` dispara um
deploy automático.

Configure na Vercel:

```dotenv
NEXT_PUBLIC_API_URL=https://api.seu-dominio.com
```

Esse valor deve apontar para uma API estável. Túneis `trycloudflare.com`
temporários são úteis para teste, mas não são adequados para produção porque
podem mudar ou ficar indisponíveis.

## 10. Testes e qualidade

```bash
make test
make lint

cd web
npm run lint
npm run build
```

Os testes de API usam PostgreSQL real para validar RLS e isolamento entre
academias. Não substitua esses testes por SQLite.

## 11. Tutorial de uso

### Aluno: fazer um treino

1. Abra `/aluno`.
2. Escolha a duração e o foco muscular.
3. Clique em **Gerar Treino**.
4. Execute o exercício atual.
5. Use o cronômetro de descanso e clique em **Próximo exercício**.
6. Ao terminar, avalie o treino no resumo.

### Aluno: salvar e ouvir uma música

1. Abra **Jukebox**.
2. Na aba **Músicas**, pesquise por título ou artista.
3. Clique em **Salvar na biblioteca**.
4. Clique em **Ouvir** ou selecione a música em **Minha biblioteca**.
5. Pressione Play no player do Spotify.
6. Volte para **Treino**. O player permanece montado e o áudio continua,
   enquanto o treino fica em primeiro plano.

### Aluno: salvar uma playlist

1. Abra **Jukebox** e selecione **Playlists do Spotify**.
2. Pesquise o nome da playlist.
3. Clique em **Salvar playlist**.
4. Em **Playlists salvas**, clique em **Ouvir novamente** para selecioná-la.
5. Pressione Play no player incorporado.
6. Use **Remover** quando não quiser mais mantê-la no histórico.

### Academia: enviar um lembrete

1. Abra o painel da academia.
2. Entre em **Lembretes**.
3. Confira a sequência quebrada e o consentimento do aluno.
4. Envie o lembrete.
5. O sistema respeita a sequência mínima, o consentimento e o cooldown.

### Gestor: parear uma TV

1. Abra **Academia > Telas**.
2. Gere o código de pareamento.
3. Abra `/tv` no dispositivo da TV.
4. Digite o código ou use `/tv?demo` apenas no ambiente local.

## 12. Vantagens

- Isolamento forte entre academias com RLS no banco.
- Fluxo de treino simples e orientado por tempo.
- Música pessoal não interfere na música exibida para a academia.
- Biblioteca e histórico persistem por aluno.
- Player oficial do Spotify reduz risco jurídico e técnico de distribuir áudio.
- WebSocket atualiza TV e fila sem polling pesado.
- Migrations reproduzíveis e deploy automatizado da API.
- Testes cobrem regras de negócio, consentimento, cooldown, RLS e jukebox.

## 13. Desvantagens e limitações

- O player incorporado depende de internet, cookies permitidos e políticas do
  Spotify.
- A reprodução não pode ser iniciada automaticamente de forma confiável; o
  aluno precisa interagir com o player.
- Algumas funções dependem de Spotify Premium.
- A API de playlists públicas pode bloquear determinados conteúdos; por isso a
  playlist é reproduzida pelo Embed, e não copiada para o servidor.
- Um túnel temporário não é uma URL de produção confiável.
- Client Credentials não dá acesso à biblioteca privada do usuário nem ao
  controle completo da conta Spotify.
- WhatsApp fica simulado enquanto as credenciais e o template aprovado não
  estiverem configurados.
- Workers de cobrança, pacing avançado de anúncios e Stripe Connect ainda são
  trabalho futuro.

## 14. Problemas comuns

### “Não foi possível conectar à API”

Confira `NEXT_PUBLIC_API_URL`, o health check `/health`, o processo da API e o
Cloudflare Tunnel. Em produção, não use `127.0.0.1` no frontend.

### Erro CORS

Adicione o domínio real do frontend em `CORS_ORIGINS` ou ajuste
`CORS_ORIGIN_REGEX`. Confirme também que a resposta veio da API, e não de uma
página 502 do túnel.

### Biblioteca retorna 500

Execute:

```bash
uv run alembic upgrade head
```

A versão necessária para músicas é `0009`; para playlists, `0010`.

### Playlist não abre

Verifique se ela é pública, se o Client ID está configurado e se o Spotify
permite o Embed. Playlists privadas não são retornadas pela busca pública.

### Player aparece vazio ou “Page not found”

Atualize o frontend para a versão mais recente e selecione novamente a faixa ou
playlist. O player diferencia IDs de `track` e `playlist`; tratar uma playlist
como faixa gera esse erro.

## 15. Próximos passos recomendados

1. Configurar um domínio estável para a API e remover dependência de túnel
   temporário.
2. Implementar login real do aluno e autorização Spotify opcional por OAuth.
3. Adicionar observabilidade, logs centralizados e alertas de disponibilidade.
4. Finalizar Stripe Connect, workers de anúncios e cobrança por pedido.
5. Criar testes de navegador para o fluxo biblioteca → player → treino.
