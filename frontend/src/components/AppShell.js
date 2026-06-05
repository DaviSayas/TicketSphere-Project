// AppShell — sidebar + main content area. Used by all authenticated routes.
const { computed } = Vue;
const { useRouter, useRoute } = VueRouter;
import { auth } from '../services/auth.js';

export default {
  name: 'AppShell',
  setup() {
    const router = useRouter();
    const route = useRoute();
    const user = computed(() => auth.state.user);
    const isAdmin = computed(() => user.value?.role === 'admin');

    function logout() {
      auth.clear();
      router.push('/login');
    }

    const roleLabel = computed(() => {
      const r = user.value?.role;
      if (r === 'admin') return 'Administrador';
      if (r === 'tech') return 'Técnico';
      return 'Utilizador';
    });

    function isActive(path) {
      return route.path === path || route.path.startsWith(path + '/');
    }

    return { user, isAdmin, logout, roleLabel, isActive, route };
  },
  template: `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand">TicketSphere</div>
        <div class="brand-sub">Gestão de Tickets</div>

        <nav class="nav">
          <div class="nav-section">Operação</div>
          <router-link to="/tickets" class="nav-item" :class="{active: isActive('/tickets')}">
            <span class="nav-icon">◧</span> Tickets
          </router-link>
          <router-link to="/tickets/new" class="nav-item" :class="{active: route.path === '/tickets/new'}">
            <span class="nav-icon">+</span> Novo Ticket
          </router-link>

          <template v-if="isAdmin">
            <div class="nav-section">Administração</div>
            <router-link to="/admin/dashboard" class="nav-item" :class="{active: isActive('/admin/dashboard')}">
              <span class="nav-icon">▦</span> Dashboard
            </router-link>
            <router-link to="/admin/users" class="nav-item" :class="{active: isActive('/admin/users')}">
              <span class="nav-icon">⚇</span> Utilizadores
            </router-link>
            <router-link to="/admin/trash" class="nav-item" :class="{active: isActive('/admin/trash')}">
              <span class="nav-icon">🗑</span> Lixeira
            </router-link>
          </template>
        </nav>

        <div class="sidebar-footer">
          <div class="sidebar-user">{{ user?.name }}</div>
          <div class="sidebar-role">{{ roleLabel }}</div>
          <a href="#" class="sidebar-logout" @click.prevent="logout">Terminar sessão →</a>
        </div>
      </aside>

      <main class="main">
        <router-view></router-view>
      </main>
    </div>
  `,
};
