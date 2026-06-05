// Admin users management — list, create, change role.
const { ref, onMounted } = Vue;
import { api } from '../services/http.js';

const ROLE_LABELS = { admin: 'Administrador', tech: 'Técnico', user: 'Utilizador' };

export default {
  name: 'AdminUsersView',
  setup() {
    const users = ref([]);
    const loading = ref(true);
    const error = ref('');
    const showCreate = ref(false);
    const newUser = ref({ name: '', email: '', password: '', role: 'user' });
    const submitting = ref(false);
    const createError = ref('');

    async function load() {
      loading.value = true;
      try {
        users.value = await api.get('/users');
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    async function createUser() {
      createError.value = '';
      submitting.value = true;
      try {
        await api.post('/users', newUser.value);
        newUser.value = { name: '', email: '', password: '', role: 'user' };
        showCreate.value = false;
        await load();
      } catch (e) {
        createError.value = e.message;
      } finally {
        submitting.value = false;
      }
    }

    async function changeRole(user, newRole) {
      if (newRole === user.role) return;
      try {
        await api.put(`/users/${user.id}/role`, { role: newRole });
        await load();
      } catch (e) {
        alert(e.message);
        await load();
      }
    }

    async function softDeleteUser(user) {
      if (!confirm(`Desativar o utilizador "${user.name}"? Poderá reativá-lo depois.`)) return;
      try {
        await api.del(`/admin/users/${user.id}`);
        await load();
      } catch (e) { alert(e.message); }
    }

    async function reactivateUser(user) {
      try {
        await api.post(`/admin/trash/users/${user.id}/restore`);
        await load();
      } catch (e) { alert(e.message); }
    }

    onMounted(load);

    return { users, loading, error, showCreate, newUser, submitting, createError,
             createUser, changeRole, softDeleteUser, reactivateUser, ROLE_LABELS };
  },
  template: `
    <div>
      <div class="page-header">
        <div>
          <h1 class="page-title">Utilizadores</h1>
          <div class="page-subtitle">{{ users.length }} contas registadas</div>
        </div>
        <button class="btn btn-accent" @click="showCreate = !showCreate">+ Novo Utilizador</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="showCreate" class="drawer-backdrop" @click.self="showCreate = false">
        <div class="drawer" @click.stop>
          <h2>Novo Utilizador</h2>
          <div v-if="createError" class="alert alert-error">{{ createError }}</div>
          <form @submit.prevent="createUser">
            <div class="field">
              <label class="field-label">Nome</label>
              <input v-model="newUser.name" class="input" required minlength="2">
            </div>
            <div class="field">
              <label class="field-label">Email</label>
              <input v-model="newUser.email" type="email" class="input" required>
            </div>
            <div class="field">
              <label class="field-label">Palavra-passe inicial</label>
              <input v-model="newUser.password" type="password" class="input" required minlength="6">
            </div>
            <div class="field">
              <label class="field-label">Perfil</label>
              <select v-model="newUser.role" class="select">
                <option value="user">Utilizador</option>
                <option value="tech">Técnico</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
            <div class="mt-5 row" style="justify-content:flex-end;">
              <button type="button" class="btn btn-secondary" @click="showCreate = false">Cancelar</button>
              <button class="btn btn-accent" :disabled="submitting">
                <span v-if="submitting" class="spinner"></span>
                <span v-else>Criar</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      <div v-if="loading" class="spinner-block"><div class="spinner"></div></div>

      <table v-else class="ticket-table">
        <thead>
          <tr>
            <th style="width:70px;">ID</th>
            <th>Nome</th>
            <th>Email</th>
            <th>Perfil</th>
            <th>Estado</th>
            <th>Acções</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td><span class="ticket-id">#{{ u.id }}</span></td>
            <td>{{ u.name }}</td>
            <td><span class="text-mono">{{ u.email }}</span></td>
            <td><span class="pill pill-medium">{{ ROLE_LABELS[u.role] || u.role }}</span></td>
            <td>
              <span v-if="u.active" class="pill pill-resolved">Activo</span>
              <span v-else class="pill pill-closed">Inactivo</span>
            </td>
            <td>
              <div class="row" style="gap:6px; align-items:center;">
                <select class="select" style="padding:6px 8px; font-size:12px;"
                        :value="u.role" @change="changeRole(u, $event.target.value)">
                  <option value="user">Utilizador</option>
                  <option value="tech">Técnico</option>
                  <option value="admin">Administrador</option>
                </select>
                <button v-if="u.active" class="btn btn-danger btn-sm" @click="softDeleteUser(u)" title="Desativar (mover para a lixeira)">Desativar</button>
                <button v-else class="btn btn-secondary btn-sm" @click="reactivateUser(u)" title="Reativar utilizador">Reativar</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
};
