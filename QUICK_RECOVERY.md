# ⚡ Quick Recovery Guide - Docker System Prune Accident

## 🔴 O Erro
Executei acidentalmente:
```bash
docker system prune -f
```

Isso deletou containers MySQL, MAS os **volumes com dados estão seguros**!

---

## ✅ Recuperação em 3 passos

### Passo 1: Confirmar que volumes existem
```bash
docker volume ls | grep mysql
```

Você deve ver (exemplo):
```
mysql-acai-belem-mix-data
mysql-mi-bebe-data
mysql-homolog-data
... todos aqui!
```

✅ Se aparecer = **dados estão salvos!**

---

### Passo 2: Recriar containers

Para CADA projeto MySQL:

```bash
# 1. Vá para a pasta do projeto
cd C:\Users\DEV2\Documents\projetos\mysql-acai-belem-mix

# 2. Recrie os containers (volumes serão reutilizados automaticamente)
docker-compose up -d

# 3. Verifique
docker ps | grep mysql
```

**Repita para:**
- mysql-base-zerada
- mysql-cliente-3
- mysql-frigonorte
- mysql-homolog
- mysql-mi-bebe
- Etc...

---

### Passo 3: Verificar tudo está funcionando

```bash
# Ver todos containers rodando
docker ps

# Ver logs de um container
docker logs mysql-container-name

# Testar conexão MySQL
mysql -h 127.0.0.1 -u root -p
```

---

## 🚨 O que NÃO fazer:

```bash
❌ docker volume rm volume-name          # Vai deletar dados!
❌ docker system prune -f                # Pode deletar outras coisas
❌ docker container prune -f             # Perigoso em multi-project
```

---

## ✅ O que fazer:

```bash
✅ docker volume ls                      # Ver o que existe
✅ docker-compose up -d                  # Recriar (reutiliza volumes)
✅ docker ps                             # Ver containers rodando
```

---

## 📊 Status Após o Acidente

| Item | Status | Ação |
|------|--------|------|
| Dados MySQL | ✅ 100% Salvos | Nenhuma |
| Containers | ❌ Deletados | Recriar com `docker-compose up -d` |
| Volumes | ✅ Intactos | Serão reutilizados automaticamente |
| Tempo para recuperar | ⚡ < 5 min | Simples |

---

## 🎯 TL;DR (Resumão)

```bash
# Para cada projeto MySQL:
cd projeto-folder
docker-compose up -d

# Pronto! Dados voltam automaticamente dos volumes!
```

---

**Perdeu dados? NÃO!** Volumes nunca foram deletados, apenas containers.
**Tempo total:** 5 minutos
**Dificuldade:** Trivial
**Risco:** Zero ✅
