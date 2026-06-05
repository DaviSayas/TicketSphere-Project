// Login page — split layout with editorial aside.
const { ref } = Vue;
const { useRouter } = VueRouter;
import { api } from '../services/http.js';
import { auth } from '../services/auth.js';

export default {
  name: 'LoginView',
  setup() {
    const router = useRouter();
    const email = ref('');
    const password = ref('');
    const error = ref('');
    const loading = ref(false);

    async function submit() {
      error.value = '';
      loading.value = true;
      try {
        const res = await api.post('/auth/login', {
          email: email.value.trim().toLowerCase(),
          password: password.value,
        });
        auth.setSession(res.access_token, res.user);
        router.push('/tickets');
      } catch (e) {
        error.value = e.message || 'Falha no login';
      } finally {
        loading.value = false;
      }
    }

    return { email, password, error, loading, submit };
  },
  template: `
    <div class="login-screen">
      <aside class="login-aside">
        <div class="login-aside-content">
          <h1>TicketSphere<br><em>Pro</em></h1>
          <p>Plataforma de gestão de tickets para equipas de suporte. Recebe pedidos por formulário web ou email, atribui técnicos, monitoriza SLAs e exporta relatórios.</p>
        </div>
        <div class="login-aside-foot">Sistema de Gestão · v1.0</div>
      </aside>

      <div class="login-form-wrap">
        <div class="login-card">
          <h2>Entrar</h2>
          <p class="muted">Use as suas credenciais para aceder ao portal.</p>

          <div v-if="error" class="alert alert-error">{{ error }}</div>

          <form @submit.prevent="submit">
            <div class="field">
              <label class="field-label">Email</label>
              <input v-model="email" type="email" class="input" required autocomplete="email" placeholder="utilizador@empresa.pt">
            </div>
            <div class="field">
              <label class="field-label">Palavra-passe</label>
              <input v-model="password" type="password" class="input" required autocomplete="current-password" placeholder="••••••••">
            </div>
            <button class="btn btn-accent btn-block" :disabled="loading">
              <span v-if="loading" class="spinner"></span>
              <span v-else>Entrar →</span>
            </button>
          </form>

        </div>
      </div>
    </div>
  `,
};
