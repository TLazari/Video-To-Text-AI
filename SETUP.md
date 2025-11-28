# Setup Completo - Video Analysis API

Guia passo a passo para começar a usar a API.

## 📋 Pré-requisitos

- **Docker & Docker Compose** instalados
- **OpenRouter API Key** (obtém em https://openrouter.ai)
- **curl** ou **Postman** para testar APIs
- **Pelo menos um vídeo de teste** em formato MP4, AVI, MOV, MKV ou WEBM

---

## 🚀 Instalação Rápida (Recomendado)

### Passo 1: Clonar/preparar o projeto

```bash
cd C:\Users\DEV2\Documents\projetos\video-to-text
```

### Passo 2: Obter API Key do OpenRouter

1. Acesse https://openrouter.ai
2. Crie uma conta ou faça login
3. Vá em **Chave API** (API Keys)
4. Crie uma nova chave (ex: `sk-or-xxxxx`)
5. Copie a chave

### Passo 3: Criar arquivo `.env`

```bash
# No diretório do projeto, crie o arquivo .env
cp .env.example .env
```

**Edite o arquivo `.env`:**

```env
OPENROUTER_API_KEY=sk-or-xxx-xxx-xxx
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
REDIS_HOST=redis
REDIS_PORT=6379
DEBUG=true
```

**⚠️ Importante:** Substitua `sk-or-xxx-xxx-xxx` pela sua chave real!

### Passo 4: Criar pasta de vídeos

```bash
mkdir videos
```

Coloque seus vídeos de teste nesta pasta (exemplo: `videos/sample.mp4`)

### Passo 5: Iniciar com Docker

```bash
# Inicia todos os containers (API, Worker, Redis, Flower)
docker-compose up -d

# Aguarde ~30 segundos para tudo iniciar
sleep 30

# Verifique que tudo está rodando
docker-compose ps
```

**Esperado:**
```
NAME                        STATUS
video-analysis-api          Up (healthy)
video-analysis-worker       Up
video-analysis-redis        Up (healthy)
video-analysis-flower       Up (healthy)
```

### Passo 6: Verificar health check

```bash
curl http://localhost:8000/health
```

**Resposta esperada:**
```json
{
  "status": "ok",
  "app": "Video Analysis API",
  "version": "1.0.0",
  "redis": "ok"
}
```

---

## 📚 Usando a API

### Opção A: Swagger UI Interativo (Recomendado para Testes)

Abra no navegador:
```
http://localhost:8000/docs
```

Lá você pode:
- ✅ Ver todos os endpoints
- ✅ Ler descrição completa
- ✅ Testar direto no navegador
- ✅ Ver exemplos de requisição/resposta

### Opção B: Command Line (cURL)

#### 1. Listar vídeos disponíveis

```bash
curl http://localhost:8000/api/v1/videos
```

**Resposta:**
```json
{
  "count": 1,
  "videos": [
    {
      "name": "sample.mp4",
      "size_mb": 45.2,
      "url": "http://localhost:8000/api/v1/videos/sample.mp4"
    }
  ]
}
```

#### 2. Submeter vídeo para análise

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "http://localhost:8000/api/v1/videos/sample.mp4",
    "options": {
      "analysis_depth": "detailed",
      "include_timestamps": true,
      "language": "pt-BR",
      "extract_entities": true,
      "detect_sentiment": false
    }
  }'
```

**Resposta (HTTP 202):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2025-11-28T10:30:00Z",
  "estimated_time_seconds": 180,
  "_links": {
    "self": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
    "status": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
    "cancel": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/cancel"
  }
}
```

**⚠️ Importante:** Copie o `job_id` para usar na próxima etapa!

#### 3. Consultar status da análise

```bash
# Substitua {job_id} pelo ID da resposta anterior
curl http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Enquanto processando (HTTP 200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2025-11-28T10:30:00Z"
}
```

**Quando completo (HTTP 200):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-11-28T10:30:00Z",
  "completed_at": "2025-11-28T10:32:30Z",
  "processing_time_seconds": 150.5,
  "result": {
    "video_metadata": {
      "duration_seconds": 180.0,
      "resolution": "1920x1080",
      "format": "mp4",
      "size_bytes": 45000000,
      "fps": 30.0,
      "codec": "h264"
    },
    "analysis": {
      "markdown": "# Análise do Vídeo\n\n## Resumo Executivo\n\n...",
      "summary": "Resumo conciso do vídeo...",
      "metadata": {
        "language_detected": "pt-BR",
        "topics": ["tecnologia", "programação"],
        "sentiment": "positive"
      }
    },
    "ai_provider": {
      "provider": "openrouter",
      "model": "nvidia/nemotron-nano-12b-v2-vl:free",
      "tokens_used": 1523,
      "processing_time_ms": 3200
    }
  }
}
```

#### 4. Cancelar análise (opcional)

```bash
curl -X DELETE http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
```

---

## 🔍 Monitoramento

### Celery Flower Dashboard

Para ver workers, tasks e progresso em tempo real:

```
http://localhost:5555
```

Lá você pode:
- Ver tasks em execução
- Ver histórico de tasks
- Monitorar workers
- Debug de problemas

### Logs em Tempo Real

```bash
# Logs da API
docker-compose logs api -f

# Logs do Worker
docker-compose logs celery_worker -f

# Logs do Redis
docker-compose logs redis -f

# Todos os logs
docker-compose logs -f
```

---

## ❌ Troubleshooting

### "Redis connection refused"

```bash
# Verifique se Redis está rodando
docker-compose ps redis

# Se não está, inicie
docker-compose up -d redis
```

### "OPENROUTER_API_KEY not found"

Verifique se `.env` existe e tem a chave:
```bash
cat .env | grep OPENROUTER_API_KEY
```

Se não tiver, edite o arquivo e adicione.

### "Video not found"

Verifique se existe a pasta `/videos` com o vídeo:
```bash
docker-compose exec api ls /videos/
```

Se não existir:
```bash
mkdir videos
cp ~/seu-video.mp4 videos/
```

### "Socket timeout" ou "Connection refused"

Aguarde alguns segundos para os containers iniciarem completamente. Verifique com:
```bash
docker-compose logs
```

### "Vídeo muito grande" (413 Payload Too Large)

Valor padrão é 500 MB. Edite `app/config.py`:
```python
MAX_VIDEO_SIZE_MB: int = 1000  # Aumentar para 1GB
```

Depois reinicie:
```bash
docker-compose restart api
```

---

## 📊 Casos de Uso Comuns

### Analisar Um Vídeo Simples

```bash
# 1. Listar disponíveis
curl http://localhost:8000/api/v1/videos | jq '.videos[0].url'

# 2. Submeter para análise
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "http://localhost:8000/api/v1/videos/sample.mp4",
    "options": {"analysis_depth": "quick"}
  }' | jq -r '.job_id'

# 3. Salvar job_id e verificar status periodicamente
JOB_ID="..." # copiar do resultado acima
while true; do
  curl http://localhost:8000/api/v1/jobs/$JOB_ID | jq '.status'
  sleep 5
done
```

### Análise Detalhada com Todas as Opções

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "http://localhost:8000/api/v1/videos/sample.mp4",
    "options": {
      "analysis_depth": "detailed",
      "include_timestamps": true,
      "language": "pt-BR",
      "extract_entities": true,
      "detect_sentiment": true
    }
  }'
```

### Salvar Resultado em Arquivo

```bash
JOB_ID="550e8400-e29b-41d4-a716-446655440000"

curl http://localhost:8000/api/v1/jobs/$JOB_ID | \
  jq '.result.analysis.markdown' > resultado.md
```

---

## 🛑 Parar os Containers

```bash
# Parar todos
docker-compose down

# Parar e remover dados do Redis
docker-compose down -v

# Ver status
docker-compose ps
```

---

## 🔧 Desenvolvimento Local (Sem Docker)

Se quiser rodar sem Docker:

```bash
# 1. Cria virtual env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Instala dependências
pip install -r requirements.txt

# 3. Inicia Redis (se não tiver, instale via Docker)
# macOS: brew install redis && redis-server
# Windows: choco install redis-64 ou use Docker

# 4. Terminal 1 - API
uvicorn app.main:app --reload

# 5. Terminal 2 - Celery Worker
celery -A app.workers.tasks worker --loglevel=info

# 6. API estará em http://localhost:8000
```

---

## 📞 Suporte

Se encontrar problemas:

1. **Verifique logs**: `docker-compose logs -f`
2. **Health check**: `curl http://localhost:8000/health`
3. **Flower**: http://localhost:5555
4. **Documentação**: http://localhost:8000/docs

---

## ✨ Próximos Passos

Depois que tudo estiver funcionando:

- Teste com diferentes formatos de vídeo
- Experimente diferentes profundidades de análise
- Configure webhooks para notificações
- Implemente persistência em banco de dados
- Configure CI/CD para deployment

Bom uso! 🎉
