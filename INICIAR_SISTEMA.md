# 🚀 Como Iniciar o TicketSphere

## Opção 1: Iniciar tudo facilmente (Windows)

### Terminal 1 - Backend
```
Double-click: START_BACKEND.bat
```
O backend começará a correr em `http://localhost:8000`

### Terminal 2 - Frontend
```
Double-click: START_FRONTEND.bat
```
O frontend começará a correr em `http://localhost:5173`

---

## Opção 2: Iniciar manualmente

### Backend (PowerShell ou CMD)
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate     # Ativar ambiente virtual
pip install -r requirements.txt
python -m app.db.seed       # Criar BD e seed data
uvicorn app.main:app --reload --port 8000
```

### Frontend (Nova janela)
```powershell
cd frontend
python server.py
```

---

## 📱 Aceder à aplicação

1. Abrir browser: **http://localhost:5173**
2. Fazer login com uma destas credenciais:

| Email | Password | Papel |
|-------|----------|-------|
| admin@empresa.pt | admin123 | Administrador |
| tecnico@empresa.pt | tecnico123 | Técnico |
| utilizador@empresa.pt | user123 | Utilizador |

---

## ✅ Tudo funcionando?

Se ver a página de login: **Sistema está pronto!**

### Se não funcionar:
- ❌ "ERR_CONNECTION_REFUSED" → Backend não está a correr
  - Execute `START_BACKEND.bat` primeiro
  
- ❌ Erros de CSS → Frontend não encontra assets
  - Verifique se `http://localhost:5173` está a abrir a pasta `frontend/`

---

## 📊 Swagger API (desenvolvimento)

Documentação interativa: **http://localhost:8000/docs**

---

## 🧪 Testar a API com cURL

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@empresa.pt","password":"admin123"}'

# Listar tickets (usar token do login acima)
curl http://localhost:8000/tickets \
  -H "Authorization: Bearer <TOKEN_AQUI>"
```
