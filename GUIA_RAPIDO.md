# 🚀 Guia Rápido - Helpdesk

## Executar na PowerShell (VS Code)

### Terminal 1 - Backend
```powershell
cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\backend
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
```

### Terminal 2 - Frontend
```powershell
cd C:\Users\Liionforce\Downloads\ticket-system-enhanced\frontend
python server.py
```

### Abrir no Navegador
```
http://localhost:5000
```

---

## 📱 Novo: Funcionalidade de Download

**Criado:**
- PWA (Web App - offline, notificações)
- Componente de instalação reutilizável
- Múltiplas localizações de acesso

**Ficheiros:**
- `manifest.json` - PWA metadata
- `service-worker.js` - Cache offline
- `src/components/DownloadApp.js` - Componente Vue
- `src/components/download-app.css` - Estilos

**Como integrar:**
```javascript
import { DownloadApp } from './components/DownloadApp.js'
import './components/download-app.css'
app.component('DownloadApp', DownloadApp)
```

**Usar:**
```vue
<DownloadApp />
```

---

## 🔗 Links de Acesso

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:5000 |
| Backend/API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

---

**Mais detalhes: Veja `INSTRUCOES_POWERSHELL.md`**
