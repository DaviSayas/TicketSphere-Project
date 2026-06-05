// Create-ticket form.
const { ref, onMounted } = Vue;
const { useRouter } = VueRouter;
import { api } from '../services/http.js';

export default {
  name: 'NewTicketView',
  setup() {
    const router = useRouter();
    const form = ref({ title: '', description: '', priority: 'medium', category_id: '' });
    const categories = ref([]);
    const error = ref('');
    const submitting = ref(false);

    onMounted(async () => {
      try { categories.value = await api.get('/categories'); } catch (e) { error.value = e.message; }
    });

    async function submit() {
      error.value = '';
      submitting.value = true;
      try {
        const payload = { ...form.value };
        if (payload.category_id === '') payload.category_id = null;
        const created = await api.post('/tickets', payload);
        router.push(`/tickets/${created.id}`);
      } catch (e) {
        error.value = e.message;
      } finally {
        submitting.value = false;
      }
    }

    return { form, categories, error, submitting, submit };
  },
  template: `
    <div>
      <div class="page-header">
        <div>
          <h1 class="page-title">Novo Ticket</h1>
          <div class="page-subtitle">Submeter um pedido de suporte</div>
        </div>
        <button class="btn btn-ghost" @click="$router.push('/tickets')">← Cancelar</button>
      </div>

      <div class="panel" style="max-width:680px;">
        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <form @submit.prevent="submit">
          <div class="field">
            <label class="field-label">Título</label>
            <input v-model="form.title" class="input" required minlength="3" maxlength="200" placeholder="Descrição breve do problema">
          </div>

          <div class="field">
            <label class="field-label">Descrição</label>
            <textarea v-model="form.description" class="textarea" rows="6" placeholder="Forneça contexto detalhado: passos para reproduzir, mensagens de erro, comportamento esperado..."></textarea>
          </div>

          <div class="row" style="gap:16px;">
            <div class="field" style="flex:1;">
              <label class="field-label">Prioridade</label>
              <select v-model="form.priority" class="select">
                <option value="low">Baixa</option>
                <option value="medium">Média</option>
                <option value="high">Alta</option>
                <option value="urgent">Urgente</option>
              </select>
            </div>
            <div class="field" style="flex:1;">
              <label class="field-label">Categoria</label>
              <select v-model="form.category_id" class="select">
                <option value="">— sem categoria —</option>
                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
          </div>

          <div class="mt-5 row" style="justify-content:flex-end;">
            <button type="button" class="btn btn-secondary" @click="$router.push('/tickets')">Cancelar</button>
            <button class="btn btn-accent" :disabled="submitting">
              <span v-if="submitting" class="spinner"></span>
              <span v-else>Criar Ticket</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
};
