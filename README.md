# Video Analysis API

API para análise de vídeos usando OpenRouter e processamento assíncrono com Celery + Redis.

## 🚀 Quick Start

### Pré-requisitos

- Docker & Docker Compose instalados
- OpenRouter API Key (obtém em https://openrouter.ai)

### Setup

1. **Clone o repositório ou navegue até o diretório**

```bash
cd video-to-text
```

2. **Crie arquivo `.env` com sua API key**

```bash
cp .env.example .env
# Edite .env e adicione sua OPENROUTER_API_KEY
```

**Arquivo `.env`:**
```env
OPENROUTER_API_KEY=sk-or-xxxxx-xxxxx
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
REDIS_HOST=redis
DEBUG=true
```

3. **Inicie os containers**

```bash
docker-compose up -d
```

Isso vai iniciar:
- **Redis** (porta 6379) - Cache e message broker
- **FastAPI** (porta 8000) - API principal
- **Celery Worker** - Processamento de vídeos em background
- **Flower** (porta 5555) - Dashboard de monitoramento (opcional)

4. **Verifique que tudo está rodando**

```bash
# Health check da API
curl http://localhost:8000/health

# Documentação da API
# Abra: http://localhost:8000/docs
```

---

## 📚 Uso

### 1. Submeter vídeo para análise

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "file:///C:/videos/sample.mp4",
    "options": {
      "analysis_depth": "detailed",
      "include_timestamps": true,
      "language": "pt-BR",
      "extract_entities": true,
      "detect_sentiment": false
    }
  }'
```

**Resposta:**
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

### 2. Consultar status/resultado

```bash
curl http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Resposta (quando processing):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2025-11-28T10:30:00Z",
  ...
}
```

**Resposta (quando completed):**
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
      "markdown": "# Análise do Vídeo\n\n## Resumo\n\n...",
      "summary": "Vídeo tutorial sobre programação...",
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
  },
  "_links": { ... }
}
```

### 3. Cancelar análise

```bash
curl -X DELETE http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
```

### 4. Listar jobs

```bash
curl http://localhost:8000/api/v1/jobs
```

---

## 📖 Documentação Interativa

Acesse a documentação interativa em:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔍 Monitoramento

### Celery Flower

Para monitorar workers e tasks em tempo real:

```
http://localhost:5555
```

### Logs

```bash
# Logs da API
docker-compose logs api -f

# Logs do worker
docker-compose logs celery_worker -f

# Logs do Redis
docker-compose logs redis -f
```

---

## 🛠️ Desenvolvimento

### Instalar localmente (sem Docker)

```bash
# Cria virtual env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instala dependências
pip install -r requirements.txt

# Instala redis (macOS): brew install redis
# Windows: choco install redis-64 ou use docker pull redis

# Inicia Redis (se local)
redis-server

# Inicia API (terminal 1)
uvicorn app.main:app --reload

# Inicia Celery worker (terminal 2)
celery -A app.workers.tasks worker --loglevel=info
```

### Estrutura do Projeto

```
video-to-text/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configurações
│   ├── core/
│   │   ├── exceptions.py       # Exceções customizadas
│   │   └── circuit_breaker.py # Circuit breaker
│   ├── models/
│   │   ├── requests.py         # Schemas de entrada
│   │   └── responses.py        # Schemas de saída
│   ├── services/
│   │   ├── openrouter_client.py    # Cliente OpenRouter
│   │   └── video_processor.py      # Processamento de vídeo
│   ├── api/
│   │   └── v1/
│   │       └── routes/
│   │           └── videos.py   # Endpoints
│   └── workers/
│       ├── celery_app.py       # Config Celery
│       └── tasks.py            # Tasks assíncronas
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OPENROUTER_API_KEY` | - | Sua chave da API OpenRouter (obrigatório) |
| `OPENROUTER_MODEL` | `nvidia/nemotron-nano-12b-v2-vl:free` | Modelo a usar |
| `REDIS_HOST` | `redis` | Host do Redis |
| `REDIS_PORT` | `6379` | Porta do Redis |
| `DEBUG` | `true` | Modo debug |
| `MAX_VIDEO_SIZE_MB` | `500` | Tamanho máximo de vídeo |

---

## ⚠️ Problemas Comuns

### "Redis connection failed"

Certifique-se que o Redis está rodando:
```bash
docker-compose up redis -d
```

### "OPENROUTER_API_KEY não configurada"

Adicione sua API key no arquivo `.env`:
```bash
OPENROUTER_API_KEY=sk-or-xxxxx-xxxxx
```

### "OpenCV not installed"

Instale através de pip:
```bash
pip install opencv-python
```

### Vídeo não encontrado

Verifique o caminho do vídeo. Deve usar protocolo `file:///`:
- ✅ `file:///C:/videos/sample.mp4`
- ✅ `file:////home/user/videos/sample.mp4`
- ❌ `C:/videos/sample.mp4`
- ❌ `/home/user/videos/sample.mp4`

---

## 🔄 Fluxo de Processamento

```
1. Cliente submete vídeo → POST /api/v1/jobs
                ↓
2. API enfileira task → Celery + Redis
                ↓
3. Retorna job_id → HTTP 202 (Accepted)
                ↓
4. Worker processa em background:
   a. Valida vídeo
   b. Extrai metadados
   c. Chama OpenRouter API
   d. Armazena resultado no Redis
                ↓
5. Cliente consulta → GET /api/v1/jobs/{job_id}
                ↓
6. Retorna resultado quando pronto
```

---

## 📝 Notas Importantes

### URLs de Vídeo Local

⚠️ **Importante**: Atualmente, a API espera URLs locais no formato `file://`. Para vídeos remotos, será necessário fazer download primeiro.

### Limite de Tokens

O modelo `nvidia/nemotron-nano-12b-v2-vl` tem limite de tokens. Vídeos muito longos podem ter limite de análise.

### Processamento

- Vídeos pequenos (< 30s): ~30-60 segundos
- Vídeos médios (30s-5m): 1-3 minutos
- Vídeos grandes (> 5m): 3-10 minutos

---

## 🤝 Contribuindo

Sinta-se livre para abrir issues ou PRs para melhorias!

---

## 📄 Licença

MIT
