# Quick Start Script para Windows PowerShell
# Video Analysis API

Write-Host "🎯 Video Analysis API - Quick Start (Windows)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se está no diretório correto
if (-Not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ Erro: docker-compose.yml não encontrado!" -ForegroundColor Red
    Write-Host "Execute este script do diretório raiz do projeto" -ForegroundColor Yellow
    exit 1
}

# Step 1: Verificar se Docker está instalado
Write-Host "1️⃣  Verificando Docker..." -ForegroundColor Green
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker encontrado: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker não encontrado! Instale em https://www.docker.com" -ForegroundColor Red
    exit 1
}

# Step 2: Verificar .env
Write-Host ""
Write-Host "2️⃣  Verificando configuração..." -ForegroundColor Green
if (-Not (Test-Path ".env")) {
    Write-Host "⚠️  .env não encontrado, criando a partir do template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Arquivo .env criado" -ForegroundColor Green
    Write-Host "   ⚠️  EDITE o arquivo .env e adicione sua OPENROUTER_API_KEY!" -ForegroundColor Yellow
    Invoke-Item ".env"  # Abre o arquivo no editor padrão
    Read-Host "Pressione ENTER após editar e salvar o arquivo"
} else {
    Write-Host "✅ Arquivo .env encontrado" -ForegroundColor Green
}

# Step 3: Criar pasta de vídeos
Write-Host ""
Write-Host "3️⃣  Preparando pasta de vídeos..." -ForegroundColor Green
if (-Not (Test-Path "videos")) {
    New-Item -ItemType Directory -Path "videos" -ErrorAction SilentlyContinue | Out-Null
    Write-Host "✅ Pasta './videos' criada" -ForegroundColor Green
    Write-Host "   📝 Coloque seus vídeos em: ./videos/" -ForegroundColor Yellow
}

# Step 4: Iniciar Docker Compose
Write-Host ""
Write-Host "4️⃣  Iniciando containers..." -ForegroundColor Green
Write-Host "   (Isto pode levar alguns segundos)" -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Containers iniciados com sucesso!" -ForegroundColor Green
} else {
    Write-Host "❌ Erro ao iniciar containers" -ForegroundColor Red
    Write-Host "   Execute 'docker-compose logs' para ver detalhes" -ForegroundColor Yellow
    exit 1
}

# Step 5: Aguardar inicialização
Write-Host ""
Write-Host "5️⃣  Aguardando inicialização (30 segundos)..." -ForegroundColor Green
for ($i = 30; $i -gt 0; $i--) {
    Write-Host -NoNewline "`r   ⏳ Aguardando... ${i}s  "
    Start-Sleep -Seconds 1
}
Write-Host ""

# Step 6: Verificar health
Write-Host ""
Write-Host "6️⃣  Verificando saúde da aplicação..." -ForegroundColor Green
$maxRetries = 5
$retryCount = 0

while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -ErrorAction Stop
        Write-Host "✅ API está saudável!" -ForegroundColor Green
        Write-Host "   Status: $($response.status)" -ForegroundColor Green
        break
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "   ⏳ Tentativa $retryCount/$maxRetries..."
            Start-Sleep -Seconds 2
        } else {
            Write-Host "❌ Não foi possível conectar à API" -ForegroundColor Red
            Write-Host "   Execute 'docker-compose logs' para ver detalhes" -ForegroundColor Yellow
            exit 1
        }
    }
}

# Step 7: Listar videos
Write-Host ""
Write-Host "7️⃣  Listando vídeos disponíveis..." -ForegroundColor Green
try {
    $videos = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/videos" -Method Get
    Write-Host "   📊 Vídeos encontrados: $($videos.count)" -ForegroundColor Green

    if ($videos.count -eq 0) {
        Write-Host ""
        Write-Host "   ⚠️  Nenhum vídeo encontrado na pasta ./videos/" -ForegroundColor Yellow
        Write-Host "   📝 Coloque um arquivo de vídeo (MP4, AVI, MOV, MKV) em ./videos/" -ForegroundColor Yellow
    } else {
        foreach ($video in $videos.videos) {
            Write-Host "      • $($video.name) ($($video.size_mb) MB)" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "   ⚠️  Não foi possível listar vídeos" -ForegroundColor Yellow
}

# Step 8: Resumo e próximos passos
Write-Host ""
Write-Host "✨ SETUP COMPLETO! ✨" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Próximos Passos:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1️⃣  Documentação Interativa (Swagger UI):" -ForegroundColor White
Write-Host "   🌐 http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "2️⃣  Monitoramento de Tasks (Flower):" -ForegroundColor White
Write-Host "   🌐 http://localhost:5555" -ForegroundColor Cyan
Write-Host ""
Write-Host "3️⃣  Health Check:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "4️⃣  Listar Vídeos Disponíveis:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/api/v1/videos" -ForegroundColor Cyan
Write-Host ""
Write-Host "5️⃣  Submeter Vídeo para Análise:" -ForegroundColor White
Write-Host "   curl -X POST http://localhost:8000/api/v1/jobs \" -ForegroundColor Cyan
Write-Host "     -H 'Content-Type: application/json' \" -ForegroundColor Cyan
Write-Host "     -d '{" -ForegroundColor Cyan
Write-Host "       ""video_url"": ""http://localhost:8000/api/v1/videos/seu-video.mp4"" " -ForegroundColor Cyan
Write-Host "     }'" -ForegroundColor Cyan
Write-Host ""
Write-Host "6️⃣  Consultar Status (substitua JOB_ID):" -ForegroundColor White
Write-Host "   curl http://localhost:8000/api/v1/jobs/JOB_ID" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 Documentação Completa:" -ForegroundColor White
Write-Host "   • README.md - Visão geral" -ForegroundColor Cyan
Write-Host "   • SETUP.md - Guia detalhado de setup" -ForegroundColor Cyan
Write-Host "   • IMPLEMENTATION_SUMMARY.md - Resumo técnico" -ForegroundColor Cyan
Write-Host ""
Write-Host "🛠️  Comandos Úteis:" -ForegroundColor White
Write-Host "   docker-compose ps              # Ver status dos containers" -ForegroundColor Cyan
Write-Host "   docker-compose logs -f         # Ver logs em tempo real" -ForegroundColor Cyan
Write-Host "   docker-compose down            # Parar todos os containers" -ForegroundColor Cyan
Write-Host "   docker-compose restart         # Reiniciar containers" -ForegroundColor Cyan
Write-Host ""
Write-Host "Happy analyzing! 🎉" -ForegroundColor Green
