// Ticket detail — shows ticket info, comments thread, history. Actions panel on right.
const { ref, computed, onMounted } = Vue;
const { useRoute, useRouter } = VueRouter;
import { api } from '../services/http.js';
import { auth } from '../services/auth.js';

const STATUS_LABELS = {
  open: 'Aberto', assigned: 'Atribuído', in_progress: 'Em Curso',
  awaiting: 'Aguarda', resolved: 'Resolvido', reopened: 'Reaberto', closed: 'Fechado',
};
const PRIORITY_LABELS = {
  urgent: 'Urgente', high: 'Alta', medium: 'Média', low: 'Baixa',
};

// Mirror of backend ALLOWED_TRANSITIONS — used to show only valid next states in the UI.
// (Server is authoritative; this just keeps the UX clean.)
const ALLOWED_TRANSITIONS = {
  open:        ['assigned', 'in_progress', 'closed'],
  assigned:    ['in_progress', 'open', 'closed'],
  in_progress: ['awaiting', 'resolved', 'assigned', 'closed'],
  awaiting:    ['in_progress', 'resolved', 'closed'],
  resolved:    ['closed', 'reopened'],
  reopened:    ['assigned', 'in_progress', 'closed'],
  closed:      [],
};

export default {
  name: 'TicketDetailView',
  setup() {
    const route = useRoute();
    const router = useRouter();
    const ticket = ref(null);
    const techs = ref([]);
    const loading = ref(true);
    const error = ref('');
    const newComment = ref({ body: '', is_internal: false });
    const posting = ref(false);

    const ticketId = computed(() => route.params.id);
    const isTechOrAdmin = computed(() => auth.hasRole('tech', 'admin'));
    const isAdmin = computed(() => auth.hasRole('admin'));
    const nextStatuses = computed(() => {
      if (!ticket.value) return [];
      return ALLOWED_TRANSITIONS[ticket.value.status] || [];
    });

    async function load() {
      loading.value = true;
      error.value = '';
      try {
        ticket.value = await api.get(`/tickets/${ticketId.value}`);
        if (isTechOrAdmin.value && techs.value.length === 0) {
          techs.value = await api.get('/users/techs');
        }
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    async function changeStatus(newStatus) {
      try {
        ticket.value = await api.put(`/tickets/${ticketId.value}/status`, { status: newStatus });
      } catch (e) { alert(e.message); }
    }

    async function changeAssignee(event) {
      const value = event.target.value;
      const assignee_id = value === '' ? null : parseInt(value);
      try {
        ticket.value = await api.put(`/tickets/${ticketId.value}/assign`, { assignee_id });
      } catch (e) {
        alert(e.message);
        // Restore select value
        event.target.value = ticket.value.assignee_id ?? '';
      }
    }

    async function deleteTicket() {
      if (!confirm('Mover este ticket para a lixeira? Poderá restaurá-lo na Lixeira (Admin).')) return;
      try {
        await api.del(`/admin/tickets/${ticketId.value}`);
        router.push('/tickets');
      } catch (e) { alert(e.message); }
    }

    async function submitComment() {
      if (!newComment.value.body.trim()) return;
      posting.value = true;
      try {
        await api.post(`/tickets/${ticketId.value}/comments`, {
          body: newComment.value.body,
          is_internal: newComment.value.is_internal,
        });
        newComment.value = { body: '', is_internal: false };
        await load();
      } catch (e) {
        alert(e.message);
      } finally {
        posting.value = false;
      }
    }

    function formatTime(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleString('pt-PT', { dateStyle: 'short', timeStyle: 'short' });
    }
    function formatDateOnly(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleDateString('pt-PT');
    }

    onMounted(load);

    return {
      ticket, techs, loading, error, newComment, posting,
      isTechOrAdmin, isAdmin, nextStatuses,
      changeStatus, changeAssignee, submitComment, deleteTicket,
      formatTime, formatDateOnly,
      STATUS_LABELS, PRIORITY_LABELS,
    };
  },
  template: `
    <div>
      <div v-if="loading" class="spinner-block"><div class="spinner"></div></div>
      <div v-else-if="error" class="alert alert-error">{{ error }}</div>
      <template v-else-if="ticket">
        <div class="page-header">
          <div>
            <div class="page-subtitle"><span class="text-mono">#{{ ticket.id }}</span> · criado {{ formatTime(ticket.created_at) }}</div>
            <h1 class="detail-title">{{ ticket.title }}</h1>
            <div class="detail-meta">
              <span class="pill" :class="'pill-' + ticket.status">{{ STATUS_LABELS[ticket.status] }}</span>
              <span class="pill" :class="'pill-' + ticket.priority">{{ PRIORITY_LABELS[ticket.priority] }}</span>
              <span class="sla-cell">
                <span class="sla-dot" :class="ticket.sla_status"></span>
                <span class="text-mono" style="font-size:11px;">SLA: {{ ticket.sla_status }}</span>
              </span>
            </div>
          </div>
          <button class="btn btn-ghost" @click="$router.push('/tickets')">← Voltar</button>
        </div>

        <div class="detail-grid">
          <div>
            <div class="detail-section">
              <div class="detail-section-title">Descrição</div>
              <div class="detail-description">{{ ticket.description || '(sem descrição)' }}</div>
            </div>

            <div class="detail-section">
              <div class="detail-section-title">Comentários ({{ ticket.comments.length }})</div>
              <div v-if="ticket.comments.length === 0" class="text-mute" style="padding:12px 0;">Sem comentários.</div>
              <div v-for="c in ticket.comments" :key="c.id" class="comment" :class="{internal: c.is_internal}">
                <div class="comment-head">
                  <div class="comment-author">
                    {{ c.user_name || 'Sistema' }}
                    <span v-if="c.is_internal" class="tag-internal">interno</span>
                  </div>
                  <div class="comment-time">{{ formatTime(c.created_at) }}</div>
                </div>
                <div class="comment-body">{{ c.body }}</div>
              </div>

              <form class="mt-4" @submit.prevent="submitComment">
                <div class="field">
                  <textarea v-model="newComment.body" class="textarea" rows="3"
                            placeholder="Escreva um comentário..."></textarea>
                </div>
                <div class="row-between">
                  <label v-if="isTechOrAdmin" class="row text-mono" style="font-size:12px;">
                    <input type="checkbox" v-model="newComment.is_internal"> Nota interna (não visível ao requerente)
                  </label>
                  <div v-else></div>
                  <button class="btn btn-accent btn-sm" :disabled="posting || !newComment.body.trim()">
                    <span v-if="posting" class="spinner"></span>
                    <span v-else>Publicar comentário</span>
                  </button>
                </div>
              </form>
            </div>

            <div class="detail-section">
              <div class="detail-section-title">Histórico</div>
              <div class="history-list">
                <div v-if="ticket.history.length === 0" class="text-mute">Sem entradas de histórico.</div>
                <div v-for="h in ticket.history" :key="h.id" class="history-row">
                  <span class="history-time">{{ formatTime(h.changed_at) }}</span>
                  <span><strong>{{ h.user_name || 'Sistema' }}</strong> · {{ h.field }}: {{ h.old_value || '∅' }} → {{ h.new_value || '∅' }}</span>
                </div>
              </div>
            </div>
          </div>

          <aside>
            <div class="aside-block">
              <h3>Detalhes</h3>
              <div class="aside-row"><span class="lbl">Categoria</span><span class="val">{{ ticket.category_name || '—' }}</span></div>
              <div class="aside-row"><span class="lbl">Requerente</span><span class="val">{{ ticket.creator_name }}</span></div>
              <div class="aside-row"><span class="lbl">Técnico</span><span class="val">{{ ticket.assignee_name || '—' }}</span></div>
              <div class="aside-row"><span class="lbl">Origem</span><span class="val text-mono">{{ ticket.source }}</span></div>
              <div class="aside-row"><span class="lbl">Prazo SLA</span><span class="val">{{ formatDateOnly(ticket.sla_deadline) }}</span></div>
              <div v-if="ticket.resolved_at" class="aside-row"><span class="lbl">Resolvido</span><span class="val">{{ formatTime(ticket.resolved_at) }}</span></div>
            </div>

            <div v-if="isTechOrAdmin" class="aside-block">
              <h3>Acções</h3>
              <div class="field">
                <label class="field-label">Alterar estado</label>
                <div class="row" style="gap:6px; flex-wrap:wrap;">
                  <button v-for="s in nextStatuses" :key="s" class="btn btn-secondary btn-sm" @click="changeStatus(s)">
                    → {{ STATUS_LABELS[s] }}
                  </button>
                  <div v-if="nextStatuses.length === 0" class="text-mute text-mono" style="font-size:11px;">Estado terminal.</div>
                </div>
              </div>

              <div class="field">
                <label class="field-label">Atribuir técnico</label>
                <select class="select" :value="ticket.assignee_id ?? ''" @change="changeAssignee">
                  <option value="">— não atribuído —</option>
                  <option v-for="t in techs" :key="t.id" :value="t.id">{{ t.name }} ({{ t.role }})</option>
                </select>
              </div>
            </div>

            <div v-if="isAdmin" class="aside-block">
              <h3>Zona de perigo</h3>
              <button class="btn btn-danger btn-sm" @click="deleteTicket" style="width:100%;">🗑 Mover para a lixeira</button>
            </div>
          </aside>
        </div>
      </template>
    </div>
  `,
};
