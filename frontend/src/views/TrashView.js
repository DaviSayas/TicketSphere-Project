// Trash (Lixeira) — admin view: deleted tickets and deactivated users.
// Supports restore and permanent delete. Backend endpoints under /admin/trash/*.
const { ref, onMounted } = Vue;
import { api } from '../services/http.js';

const STATUS_LABELS = {
  open: 'Aberto', assigned: 'Atribuído', in_progress: 'Em Curso',
  awaiting: 'Aguarda', resolved: 'Resolvido', reopened: 'Reaberto', closed: 'Fechado',
};
const PRIORITY_LABELS = {
  urgent: 'Urgente', high: 'Alta', medium: 'Média', low: 'Baixa',
};
const ROLE_LABELS = { admin: 'Administrador', tech: 'Técnico', user: 'Utilizador' };

export default {
  name: 'TrashView',
  setup() {
    const tab = ref('tickets');
    const tickets = ref([]);
    const users = ref([]);
    const loading = ref(true);
    const error = ref('');

    async function load() {
      loading.value = true;
      error.value = '';
      try {
        const [t, u] = await Promise.all([
          api.get('/admin/trash/tickets'),
          api.get('/admin/trash/users'),
        ]);
        tickets.value = t;
        users.value = u;
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    async function restoreTicket(t) {
      try {
        await api.post(`/admin/trash/tickets/${t.id}/restore`);
        await load();
      } catch (e) { alert(e.message); }
    }

    async function purgeTicket(t) {
      if (!confirm(`Apagar DEFINITIVAMENTE o ticket #${t.id}? Esta ação é irreversível.`)) return;
      try {
        await api.del(`/admin/trash/tickets/${t.id}/permanent`);
        await load();
      } catch (e) { alert(e.message); }
    }

    async function restoreUser(u) {
      try {
        await api.post(`/admin/trash/users/${u.id}/restore`);
        await load();
      } catch (e) { alert(e.message); }
    }

    async function purgeUser(u) {
      if (!confirm(`Apagar DEFINITIVAMENTE o utilizador "${u.name}"? Esta ação é irreversível.`)) return;
      try {
        await api.del(`/admin/trash/users/${u.id}/permanent`);
        await load();
      } catch (e) { alert(e.message); }
    }

    function formatTime(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleString('pt-PT', { dateStyle: 'short', timeStyle: 'short' });
    }

    onMounted(load);

    return {
      tab, tickets, users, loading, error,
      restoreTicket, purgeTicket, restoreUser, purgeUser, formatTime,
      STATUS_LABELS, PRIORITY_LABELS, ROLE_LABELS,
    };
  },
  template: `
    <div>
      <div class="page-header">
        <div>
          <h1 class="page-title">Lixeira</h1>
          <div class="page-subtitle">Tickets removidos e utilizadores desativados</div>
        </div>
        <button class="btn btn-ghost btn-sm" @click="load">↻ Atualizar</button>
      </div>

      <div class="row" style="background: rgba(255,255,255,0.04); padding: 4px; border-radius: 8px; border: 1px solid var(--border); display:inline-flex; margin-bottom: 16px;">
        <button class="btn btn-sm" :class="tab === 'tickets' ? 'btn-accent' : 'btn-ghost'" @click="tab = 'tickets'" style="padding: 6px 12px; border-radius: 6px;">
          Tickets ({{ tickets.length }})
        </button>
        <button class="btn btn-sm" :class="tab === 'users' ? 'btn-accent' : 'btn-ghost'" @click="tab = 'users'" style="padding: 6px 12px; border-radius: 6px;">
          Utilizadores ({{ users.length }})
        </button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="loading" class="spinner-block"><div class="spinner"></div></div>

      <!-- TICKETS -->
      <template v-else-if="tab === 'tickets'">
        <div v-if="tickets.length === 0" class="empty-state panel">
          <div class="empty-state-title">Lixeira vazia</div>
          <p class="text-mute">Nenhum ticket na lixeira.</p>
        </div>
        <table v-else class="ticket-table">
          <thead>
            <tr>
              <th style="width:70px;">ID</th>
              <th>Título</th>
              <th>Estado</th>
              <th>Prioridade</th>
              <th>Técnico</th>
              <th style="width:220px;">Acções</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tickets" :key="t.id">
              <td><span class="ticket-id">#{{ t.id }}</span></td>
              <td class="ticket-title-cell">{{ t.title }}</td>
              <td><span class="pill" :class="'pill-' + t.status">{{ STATUS_LABELS[t.status] || t.status }}</span></td>
              <td><span class="pill" :class="'pill-' + t.priority">{{ PRIORITY_LABELS[t.priority] || t.priority }}</span></td>
              <td>{{ t.assignee_name || '—' }}</td>
              <td>
                <div class="row" style="gap:6px;">
                  <button class="btn btn-secondary btn-sm" @click="restoreTicket(t)">↩ Restaurar</button>
                  <button class="btn btn-danger btn-sm" @click="purgeTicket(t)">Apagar definitivo</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </template>

      <!-- USERS -->
      <template v-else-if="tab === 'users'">
        <div v-if="users.length === 0" class="empty-state panel">
          <div class="empty-state-title">Lixeira vazia</div>
          <p class="text-mute">Nenhum utilizador desativado.</p>
        </div>
        <table v-else class="ticket-table">
          <thead>
            <tr>
              <th style="width:70px;">ID</th>
              <th>Nome</th>
              <th>Email</th>
              <th>Perfil</th>
              <th style="width:220px;">Acções</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td><span class="ticket-id">#{{ u.id }}</span></td>
              <td>{{ u.name }}</td>
              <td><span class="text-mono">{{ u.email }}</span></td>
              <td><span class="pill pill-medium">{{ ROLE_LABELS[u.role] || u.role }}</span></td>
              <td>
                <div class="row" style="gap:6px;">
                  <button class="btn btn-secondary btn-sm" @click="restoreUser(u)">↩ Reativar</button>
                  <button class="btn btn-danger btn-sm" @click="purgeUser(u)">Apagar definitivo</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>
  `,
};
