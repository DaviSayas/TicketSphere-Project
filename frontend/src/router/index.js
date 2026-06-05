// Vue Router config — hash mode (works without a build step / dev server config).
const { createRouter, createWebHashHistory } = VueRouter;

import LoginView from '../views/LoginView.js';
import AppShell from '../components/AppShell.js';
import TicketsView from '../views/TicketsView.js';
import NewTicketView from '../views/NewTicketView.js';
import TicketDetailView from '../views/TicketDetailView.js';
import AdminDashboardView from '../views/AdminDashboardView.js';
import AdminUsersView from '../views/AdminUsersView.js';
import TrashView from '../views/TrashView.js';

import { auth } from '../services/auth.js';

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', redirect: '/tickets' },
        { path: 'tickets', component: TicketsView },
        { path: 'tickets/new', component: NewTicketView },
        { path: 'tickets/:id', component: TicketDetailView },
        { path: 'admin/dashboard', component: AdminDashboardView, meta: { roles: ['admin'] } },
        { path: 'admin/users', component: AdminUsersView, meta: { roles: ['admin'] } },
        { path: 'admin/trash', component: TrashView, meta: { roles: ['admin'] } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/tickets' },
  ],
});

router.beforeEach((to, from, next) => {
  const isAuth = auth.isAuthenticated();

  // Public route (login) — if already logged in, send to tickets
  if (to.meta.public) {
    if (isAuth && to.path === '/login') return next('/tickets');
    return next();
  }

  // Protected route requires auth
  if (!isAuth) return next('/login');

  // Role-restricted route
  if (to.meta.roles && !to.meta.roles.includes(auth.state.user?.role)) {
    return next('/tickets');
  }

  next();
});

export default router;
