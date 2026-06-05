# Sistema de Gestão de Tickets

Plataforma de helpdesk interno (Web Full-Stack) — recebe pedidos de suporte por formulário web ou ingestão de email, atribui técnicos, gere SLAs e mantém histórico completo de resolução.

> **Plano de Estágio — 300 Horas** • FastAPI + SQLite + Vue 3

---

## Arquitectura

```
┌──────────────────────────────┐         ┌──────────────────────────────┐
│         Frontend             │  HTTP   │          Backend             │
│  Vue 3 (Composition API)     │ ◄─────► │  FastAPI + SQLAlchemy        │
│  Vue Router + fetch wrapper  │   JWT   │  JWT (python-jose) + RBAC    │
└──────────────────────────────┘         │                              │
                                         │  ┌────────────────────────┐  │
                                         │  │  APScheduler (background)│  │
                                         │  │  • IMAP poll (2 min)    │  │
                                         │  │  • SLA checker (5 min)  │  │
                                         │  └────────────────────────┘  │
                                         │                              │
                                         │  ┌────────────────────────┐  │
                                         │  │  SQLite (SQLAlchemy ORM)│  │
                                         │  └────────────────────────┘  │
                                         │                              │
                                         │  ┌────────────────────────┐  │
                                         │  │  SMTP (Mailpit) / IMAP │  │
                                         │  └────────────────────────┘  │
                                         └──────────────────────────────┘
```

### Perfis (RBAC)

- **Admin** — acesso total, gestão de utilizadores, dashboard, relatórios
- **Técnico** — vê todos os tickets, edita só os seus (ou os atribuídos)
- **Utilizador** — só cria e vê os seus próprios tickets

### Workflow do Ticket

```
Aberto ──► Em Curso ──► Aguarda Resposta ──► Resolvido ──► Fechado
   │           │               │                  │
   └───────────┴───────────────┴──────────────────┘
            (validações de transição na API)
```

---

## Instalação em 5 passos

```bash
# 1. Clone & entrar no projecto
cd backend

# 2. Criar venv e activar
python3.12 -m venv venv
source venv/bin/activate         # Linux/Mac
# venv\Scripts\activate          # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Inicializar a base de dados (cria tabelas + seed data)
python -m app.db.seed

# 5. Arrancar o servidor
uvicorn app.main:app --reload --port 8000
```

O Swagger UI fica em `http://localhost:8000/docs`.

### Frontend

O frontend é Vue 3 **sem build tools** — abre directamente no browser via CDN.

```bash
cd frontend
# servir com qualquer servidor estático, ex:
python -m http.server 5173
```

Abrir `http://localhost:5173`.

### Mailpit (SMTP/IMAP de teste)

```bash
# Linux/Mac (binário)
./mailpit
# UI: http://localhost:8025
# SMTP: localhost:1025  •  IMAP: localhost:1143
```

---

## Variáveis de Ambiente

Copiar `backend/.env.example` para `backend/.env` e ajustar:

| Variável             | Default                  | Descrição                           |
|----------------------|--------------------------|-------------------------------------|
| `DATABASE_URL`       | `sqlite:///./tickets.db` | URL da BD                           |
| `JWT_SECRET`         | (alterar!)               | Chave para assinar tokens           |
| `JWT_ALGORITHM`      | `HS256`                  | Algoritmo JWT                       |
| `JWT_EXPIRE_MINUTES` | `1440` (24h)             | Validade do token                   |
| `SMTP_HOST`          | `localhost`              | Servidor SMTP (Mailpit)             |
| `SMTP_PORT`          | `1025`                   | Porto SMTP                          |
| `IMAP_HOST`          | `localhost`              | Servidor IMAP                       |
| `IMAP_PORT`          | `1143`                   | Porto IMAP                          |
| `IMAP_USER`          | `support@local`          | Caixa de suporte                    |
| `IMAP_PASSWORD`      | `password`               | Password IMAP                       |
| `ENABLE_SCHEDULER`   | `true`                   | Activar/desactivar jobs background  |

---

## Credenciais de Teste (Seed Data)

| Email                 | Password    | Perfil   |
|-----------------------|-------------|----------|
| admin@empresa.pt      | admin123    | admin    |
| tecnico@empresa.pt    | tecnico123  | tech     |
| utilizador@empresa.pt | user123     | user     |

---

## Endpoints Principais

| Método | URL                               | Perfil    | Descrição                       |
|--------|-----------------------------------|-----------|---------------------------------|
| POST   | `/auth/login`                     | público   | Login → JWT                     |
| GET    | `/auth/me`                        | autenticado | Perfil actual                 |
| GET    | `/users`                          | admin     | Listar utilizadores             |
| POST   | `/users`                          | admin     | Criar utilizador                |
| PUT    | `/users/{id}/role`                | admin     | Alterar perfil                  |
| GET    | `/tickets`                        | autenticado | Listar (com filtros)          |
| POST   | `/tickets`                        | autenticado | Criar ticket                  |
| GET    | `/tickets/{id}`                   | autenticado | Detalhe + comentários + histórico |
| PUT    | `/tickets/{id}/status`            | tech/admin | Transição de estado            |
| PUT    | `/tickets/{id}/assign`            | tech/admin | Atribuir técnico               |
| POST   | `/tickets/{id}/comments`          | autenticado | Adicionar comentário          |
| GET    | `/admin/dashboard`                | admin     | Métricas (últimos 30 dias)      |
| GET    | `/admin/reports/monthly`          | admin     | CSV mensal                      |

Documentação completa em `/docs` (Swagger UI).

---

## Estrutura de Pastas

```
ticket-system/
├── backend/
│   ├── app/
│   │   ├── api/              # Routers FastAPI
│   │   ├── core/             # config, segurança, deps
│   │   ├── db/               # session, base, seed
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # lógica de negócio (email, sla)
│   │   ├── scheduler/        # APScheduler jobs
│   │   ├── templates/        # templates de email
│   │   └── main.py
│   ├── tests/                # pytest + httpx
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   └── src/
│       ├── views/            # páginas
│       ├── components/       # componentes reutilizáveis
│       ├── services/         # http wrapper, auth
│       ├── router/           # vue-router
│       └── assets/           # CSS
└── docs/
    ├── ARCHITECTURE.md       # decisões de design
    └── ER-DIAGRAM.md         # diagrama entidade-relação
```

---

## Testes

```bash
cd backend
pytest                        # todos os testes
pytest -v                     # verbose
pytest tests/test_tickets.py  # ficheiro específico
```

Cobertura:
- Autenticação e JWT
- RBAC (técnico não acede a rota admin → 403)
- Transições de estado válidas e inválidas (→ 400)
- CRUD de tickets, comentários, histórico
- Fixture com seed data para testes reprodutíveis

---

## Decisões de Design

Ver `docs/ARCHITECTURE.md` para discussão das escolhas técnicas, trade-offs, e melhorias futuras.

---

## Licença

Projecto académico — estágio.
