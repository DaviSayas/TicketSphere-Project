// Tickets list — table & Kanban board with filters, live SLA countdown, and quick stats.
const { ref, onMounted, onBeforeUnmount, watch, computed } = Vue;
const { useRouter, useRoute } = VueRouter;
import { api } from '../services/http.js';
import { auth } from '../services/auth.js';

const STATUS_LABELS = {
  open: 'Aberto', in_progress: 'Em Curso',
  awaiting: 'Aguarda', resolved: 'Resolvido', closed: 'Fechado',
};
const PRIORITY_LABELS = {
  urgent: 'Urgente', high: 'Alta', medium: 'Média', low: 'Baixa',
};

const ALLOWED_TRANSITIONS = {
  open:        ['in_progress', 'resolved', 'closed'],
  in_progress: ['awaiting', 'resolved', 'closed'],
  awaiting:    ['in_progress', 'resolved', 'closed'],
  resolved:    ['closed', 'in_progress'],
  closed:      [],
};

export default {
  name: 'TicketsView',
  setup() {
    const router = useRouter();
    const route = useRoute();
    const loading = ref(true);
    const error = ref('');
    const items = ref([]);
    const total = ref(0);
    const page = ref(1);
    const pageSize = 25;
    const categories = ref([]);
    
    // View Mode: 'table' or 'kanban'
    const viewMode = ref('table');

    // Real-time SLA clock
    const now = ref(Date.now());
    let timerId = null;

    const filters = ref({
      status: route.query.status || '',
      priority: route.query.priority || '',
      category_id: route.query.category_id || '',
      q: route.query.q || '',
      only_mine: false,
    });

    const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
    const canFilterMine = computed(() => auth.hasRole('tech', 'admin'));
    const isTechOrAdmin = computed(() => auth.hasRole('tech', 'admin'));

    // Top quick statistics based on currently fetched items
    const stats = computed(() => {
      const uId = auth.state.user?.id;
      return {
        myOpen: items.value.filter(t => t.assignee_id === uId && t.status !== 'resolved' && t.status !== 'closed').length,
        inProgress: items.value.filter(t => t.status === 'in_progress').length,
        urgent: items.value.filter(t => t.priority === 'urgent' || t.priority === 'high').length,
        breached: items.value.filter(t => t.sla_status === 'breached').length,
      };
    });

    // Group items for Kanban columns
    const kanbanColumns = [
      { key: 'open', label: 'Aberto' },
      { key: 'in_progress', label: 'Em Curso' },
      { key: 'awaiting', label: 'Aguarda Resposta' },
      { key: 'resolved', label: 'Resolvido' },
      { key: 'closed', label: 'Fechado' }
    ];

    const kanbanGroups = computed(() => {
      const groups = { open: [], in_progress: [], awaiting: [], resolved: [], closed: [] };
      items.value.forEach(item => {
        if (groups[item.status] !== undefined) {
          groups[item.status].push(item);
        }
      });
      return groups;
    });

    async function load() {
      loading.value = true;
      error.value = '';
      try {
        // If in Kanban view, fetch a larger batch of items so it looks complete
        const actualPageSize = viewMode.value === 'kanban' ? 100 : pageSize;
        const params = { page: page.value, page_size: actualPageSize };
        for (const [k, v] of Object.entries(filters.value)) {
          if (v !== '' && v !== false && v !== null) params[k] = v;
        }
        const data = await api.get('/tickets', params);
        items.value = data.items;
        total.value = data.total;
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    async function loadCategories() {
      try { categories.value = await api.get('/categories'); } catch { /* non-fatal */ }
    }

    function openTicket(id) { router.push(`/tickets/${id}`); }
    
    function resetFilters() {
      filters.value = { status: '', priority: '', category_id: '', q: '', only_mine: false };
      page.value = 1;
      load();
    }
    
    function applyFilters() { page.value = 1; load(); }

    function prevPage() { if (page.value > 1) { page.value--; load(); } }
    function nextPage() { if (page.value < totalPages.value) { page.value++; load(); } }

    function relativeTime(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      const mins = Math.floor((Date.now() - d.getTime()) / 60000);
      if (mins < 1) return 'agora';
      if (mins < 60) return mins + 'm';
      if (mins < 1440) return Math.floor(mins / 60) + 'h';
      return Math.floor(mins / 1440) + 'd';
    }

    // Real-time SLA Countdown calculation
    function getSlaTimer(t) {
      if (!t.sla_deadline) return { text: '—', status: 'ok' };
      const target = new Date(t.sla_deadline).getTime();
      const diff = target - now.value;
      const isBreached = diff < 0;
      const absDiff = Math.abs(diff);

      const hours = Math.floor(absDiff / 3600000);
      const minutes = Math.floor((absDiff % 3600000) / 60000);

      if (isBreached) {
        return { text: `Excedido ${hours}h ${minutes}m`, status: 'breached' };
      }
      
      let status = 'ok';
      if (diff < 4 * 3600000) { // under 4 hours
        status = 'warning';
      }
      return { text: `${hours}h ${minutes}m`, status };
    }

    function slaTip(t) {
      if (!t.sla_deadline) return 'Sem prazo';
      const d = new Date(t.sla_deadline);
      return 'Prazo: ' + d.toLocaleString('pt-PT');
    }

    // Kanban quick transition
    async function quickTransition(ticket, newStatus) {
      try {
        await api.put(`/tickets/${ticket.id}/status`, { status: newStatus });
        await load();
      } catch (e) {
        alert('Erro ao alterar estado: ' + e.message);
      }
    }

    function getTransitions(status) {
      return ALLOWED_TRANSITIONS[status] || [];
    }

    // ---- Drag & Drop (Kanban) ----
    const draggedTicket = ref(null);
    const dragOverCol = ref(null);

    function isValidDrop(colKey) {
      if (!draggedTicket.value) return false;
      if (draggedTicket.value.status === colKey) return false;
      return getTransitions(draggedTicket.value.status).includes(colKey);
    }

    function onDragStart(ticket, evt) {
      if (!isTechOrAdmin.value) { evt.preventDefault(); return; }
      draggedTicket.value = ticket;
      if (evt.dataTransfer) {
        evt.dataTransfer.effectAllowed = 'move';
        evt.dataTransfer.setData('text/plain', String(ticket.id));
      }
    }

    function onDragEnd() {
      draggedTicket.value = null;
      dragOverCol.value = null;
    }

    function onDragOver(colKey, evt) {
      if (!draggedTicket.value) return;
      evt.preventDefault();
      dragOverCol.value = colKey;
      if (evt.dataTransfer) {
        evt.dataTransfer.dropEffect = isValidDrop(colKey) ? 'move' : 'none';
      }
    }

    function onDragLeave(colKey) {
      if (dragOverCol.value === colKey) dragOverCol.value = null;
    }

    async function onDrop(colKey) {
      const ticket = draggedTicket.value;
      dragOverCol.value = null;
      draggedTicket.value = null;
      if (!ticket || ticket.status === colKey) return; // same column = no-op
      if (!getTransitions(ticket.status).includes(colKey)) {
        error.value = `Transição inválida: "${STATUS_LABELS[ticket.status]}" → "${STATUS_LABELS[colKey]}"`;
        setTimeout(() => { error.value = ''; }, 3000);
        return;
      }
      await quickTransition(ticket, colKey);
    }

    onMounted(() => {
      loadCategories();
      load();
      timerId = setInterval(() => {
        now.value = Date.now();
      }, 10000); // update timers every 10 seconds
    });

    onBeforeUnmount(() => {
      if (timerId) clearInterval(timerId);
    });

    // Reload list when viewMode changes
    watch(viewMode, () => {
      page.value = 1;
      load();
    });

    return {
      loading, error, items, total, page, totalPages,
      filters, categories, canFilterMine, isTechOrAdmin,
      viewMode, stats, kanbanColumns, kanbanGroups,
      load, resetFilters, applyFilters, openTicket,
      prevPage, nextPage, relativeTime, getSlaTimer, slaTip,
      quickTransition, getTransitions,
      draggedTicket, dragOverCol, isValidDrop,
      onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop,
      STATUS_LABELS, PRIORITY_LABELS,
    };
  },
  template: `
    <div>
      <div class="page-header">
        <div>
          <h1 class="page-title">Tickets</h1>
          <div class="page-subtitle">{{ total }} pedidos no total · página {{ page }} de {{ totalPages }}</div>
        </div>
        <div class="row">
          <!-- View Switcher -->
          <div class="row" style="background: rgba(255,255,255,0.04); padding: 4px; border-radius: 8px; border: 1px solid var(--border);">
            <button class="btn btn-sm" :class="viewMode === 'table' ? 'btn-accent' : 'btn-ghost'" @click="viewMode = 'table'" style="padding: 6px 12px; border-radius: 6px;">
              Tabela
            </button>
            <button class="btn btn-sm" :class="viewMode === 'kanban' ? 'btn-accent' : 'btn-ghost'" @click="viewMode = 'kanban'" style="padding: 6px 12px; border-radius: 6px;">
              Kanban
            </button>
          </div>
          <button class="btn btn-accent" @click="$router.push('/tickets/new')">+ Novo Ticket</button>
        </div>
      </div>

      <!-- Quick Statistics Widgets -->
      <div class="metric-grid">
        <div class="metric">
          <div class="metric-label">Os meus abertos</div>
          <div class="metric-value">{{ stats.myOpen }}</div>
        </div>
        <div class="metric info">
          <div class="metric-label">Em curso na página</div>
          <div class="metric-value">{{ stats.inProgress }}</div>
        </div>
        <div class="metric warn">
          <div class="metric-label">Urgentes na página</div>
          <div class="metric-value">{{ stats.urgent }}</div>
        </div>
        <div class="metric danger">
          <div class="metric-label">SLA Excedido na página</div>
          <div class="metric-value">{{ stats.breached }}</div>
        </div>
      </div>

      <div class="list-toolbar">
        <input v-model="filters.q" class="input" placeholder="🔍 Pesquisar título..." @keyup.enter="applyFilters" style="min-width:240px;">

        <select v-model="filters.status" class="select" @change="applyFilters">
          <option value="">Todos os estados</option>
          <option v-for="(label, key) in STATUS_LABELS" :key="key" :value="key">{{ label }}</option>
        </select>

        <select v-model="filters.priority" class="select" @change="applyFilters">
          <option value="">Todas as prioridades</option>
          <option v-for="(label, key) in PRIORITY_LABELS" :key="key" :value="key">{{ label }}</option>
        </select>

        <select v-model="filters.category_id" class="select" @change="applyFilters">
          <option value="">Todas as categorias</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>

        <label v-if="canFilterMine" class="row text-mono" style="font-size:12px; cursor:pointer;">
          <input type="checkbox" v-model="filters.only_mine" @change="applyFilters"> Só meus
        </label>

        <div class="toolbar-spacer"></div>
        <button class="btn btn-ghost btn-sm" @click="resetFilters">Limpar filtros</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="loading" class="spinner-block"><div class="spinner"></div></div>

      <div v-else-if="items.length === 0" class="empty-state panel">
        <div class="empty-state-title">Sem tickets</div>
        <p class="text-mute">Nenhum ticket corresponde aos filtros aplicados.</p>
      </div>

      <!-- TABLE VIEW -->
      <table v-else-if="viewMode === 'table'" class="ticket-table">
        <thead>
          <tr>
            <th style="width:140px;">SLA</th>
            <th style="width:70px;">ID</th>
            <th>Título</th>
            <th>Estado</th>
            <th>Prioridade</th>
            <th>Categoria</th>
            <th>Técnico</th>
            <th>Criado</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in items" :key="t.id" class="clickable" @click="openTicket(t.id)">
            <td>
              <div class="sla-cell">
                <span class="sla-dot" :class="t.sla_status"></span>
                <span class="sla-text" :class="getSlaTimer(t).status">{{ getSlaTimer(t).text }}</span>
                <span class="tip">{{ slaTip(t) }}</span>
              </div>
            </td>
            <td><span class="ticket-id">#{{ t.id }}</span></td>
            <td class="ticket-title-cell">
              {{ t.title }}
              <span v-if="t.source === 'email'" class="source-tag">✉ email</span>
            </td>
            <td><span class="pill" :class="'pill-' + t.status">{{ STATUS_LABELS[t.status] }}</span></td>
            <td><span class="pill" :class="'pill-' + t.priority">{{ PRIORITY_LABELS[t.priority] }}</span></td>
            <td>{{ t.category_name || '—' }}</td>
            <td>{{ t.assignee_name || '—' }}</td>
            <td><span class="text-mono">{{ relativeTime(t.created_at) }}</span></td>
          </tr>
        </tbody>
      </table>

      <!-- KANBAN VIEW -->
      <template v-else-if="viewMode === 'kanban'">
      <div v-if="isTechOrAdmin" class="kanban-hint">💡 Arraste os cartões entre colunas para mudar o estado, ou use os botões "Mover".</div>
      <div class="kanban-board">
        <div v-for="col in kanbanColumns" :key="col.key" class="kanban-col"
             :class="{ 'drag-over': dragOverCol === col.key && isValidDrop(col.key), 'drag-invalid': dragOverCol === col.key && draggedTicket && !isValidDrop(col.key) }"
             @dragover="onDragOver(col.key, $event)" @dragleave="onDragLeave(col.key)" @drop="onDrop(col.key)">
          <div class="kanban-col-header">
            <span class="kanban-col-title">{{ col.label }}</span>
            <span class="kanban-col-count">{{ kanbanGroups[col.key].length }}</span>
          </div>
          
          <div v-if="kanbanGroups[col.key].length === 0" class="text-mute" style="text-align:center; padding: 20px 0; font-size:12px;">
            Vazio
          </div>

          <div v-for="t in kanbanGroups[col.key]" :key="t.id" class="kanban-card"
               :class="{ dragging: draggedTicket && draggedTicket.id === t.id }"
               :draggable="isTechOrAdmin"
               @dragstart="onDragStart(t, $event)" @dragend="onDragEnd"
               @click.self="openTicket(t.id)">
            <div class="kanban-card-title" @click="openTicket(t.id)">{{ t.title }}</div>
            
            <div class="row-between" style="margin-top: 8px;">
              <span class="ticket-id" @click="openTicket(t.id)">#{{ t.id }}</span>
              <span class="pill" :class="'pill-' + t.priority" style="font-size:8px; padding: 2px 6px;">{{ t.priority }}</span>
            </div>

            <div class="kanban-card-meta">
              <span>👤 {{ t.assignee_name || 'Não atribuído' }}</span>
            </div>

            <!-- Real-time SLA Countdown inside Kanban Card -->
            <div class="row" style="margin-top:6px; font-size:11px;">
              <span class="sla-dot" :class="t.sla_status" style="width:8px; height:8px;"></span>
              <span class="sla-text" :class="getSlaTimer(t).status" style="font-size:10px;">{{ getSlaTimer(t).text }}</span>
            </div>

            <!-- Quick transitions for techs/admins -->
            <div v-if="isTechOrAdmin && getTransitions(t.status).length" class="kanban-card-foot">
              <span class="text-mute" style="font-size:9px; font-family:var(--font-mono)">Mover:</span>
              <div class="kanban-card-actions">
                <button v-for="nextS in getTransitions(t.status)" :key="nextS" 
                        class="kanban-btn" @click.stop="quickTransition(t, nextS)">
                  {{ STATUS_LABELS[nextS] }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      </template>

      <div v-if="viewMode === 'table' && totalPages > 1" class="pagination">
        <button class="btn btn-secondary btn-sm" :disabled="page <= 1" @click="prevPage">← Anterior</button>
        <span class="info">Página {{ page }} / {{ totalPages }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="page >= totalPages" @click="nextPage">Seguinte →</button>
      </div>
    </div>
  `,
};
