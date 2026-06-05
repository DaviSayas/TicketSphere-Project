# 🚀 Como Executar o Helpdesk na PowerShell do VS Code

## 📋 Instruções Passo-a-Passo

### **Método 1: Dois Terminais Separados (Recomendado)**

#### Terminal 1 - Backend

```powershell
cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\backend
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
```

**O que esperar:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

#### Terminal 2 - Frontend

```powershell
cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\frontend
python server.py
```

**O que esperar:**
```
Serving on http://0.0.0.0:5000
```

---

### **Método 2: Um Só Terminal (Sequencial)**

```powershell
# Backend
cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\backend
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000

# (Em outro terminal, enquanto backend está rodando:)
cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\frontend
python server.py
```

---

### **Método 3: Script PowerShell Automático**

Crie um arquivo `iniciar-helpdesk.ps1`:

```powershell
# iniciar-helpdesk.ps1

$backendPath = "C:\Users\Liionforce\Downloads\ticket-system-enhanced\backend"
$frontendPath = "C:\Users\Liionforce\Downloads\ticket-system-enhanced\frontend"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  INICIANDO HELPDESK" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Terminal 1: Backend
Write-Host "[1] Iniciando Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
  cd '$backendPath'
  .\venv\Scripts\activate
  python -m uvicorn app.main:app --reload --port 8000
"

Start-Sleep -Seconds 3

# Terminal 2: Frontend
Write-Host "[2] Iniciando Frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
  cd '$frontendPath'
  python server.py
"

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  ✓ PROGRAMA INICIADO!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Acesso:" -ForegroundColor Cyan
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "   Frontend: http://localhost:5000" -ForegroundColor White
Write-Host ""
Write-Host "📚 Documentação API:" -ForegroundColor Cyan
Write-Host "   http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
```

**Para executar:**
```powershell
# Permitir scripts (executar uma vez):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Depois executar o script:
.\iniciar-helpdesk.ps1
```

---

## ✅ Verificar se está funcionando

### Backend (API):
```powershell
curl http://localhost:8000/docs
# Deve abrir a documentação Swagger
```

### Frontend (Web):
```powershell
start http://localhost:5000
# Deve abrir no navegador
```

---

## 🛠️ Troubleshooting

### Erro: "O venv não está ativado"
```powershell
# Solução:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\backend
.\venv\Scripts\activate
```

### Erro: "Porta 8000 já está em uso"
```powershell
# Mudar porta:
python -m uvicorn app.main:app --reload --port 8001
```

### Erro: "Python não encontrado"
```powershell
# Instalar Python ou adicionar ao PATH
python --version
```

---

## 📊 Estrutura de Portas

| Serviço | Porta | URL | Função |
|---------|-------|-----|--------|
| Backend | 8000 | http://localhost:8000 | API FastAPI |
| Frontend | 5000 | http://localhost:5000 | Web Interface |
| Swagger | 8000 | http://localhost:8000/docs | API Docs |

---

## 🎯 Guia Rápido

**Opção mais simples no VS Code:**

1. **Abra dois terminais** (Ctrl + Shift + `)
2. **Terminal 1:**
   ```powershell
   cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\backend
   .\venv\Scripts\activate
   python -m uvicorn app.main:app --reload --port 8000
   ```

3. **Terminal 2:**
   ```powershell
   cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\frontend
   python server.py
   ```

4. **Abra no navegador:**
   ```
   http://localhost:5000
   ```

---

**Tudo pronto! O programa deve estar rodando agora.** ✓
