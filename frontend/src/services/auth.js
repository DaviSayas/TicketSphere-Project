// Auth state — reactive container with token + user persisted in localStorage.
const { reactive } = Vue;

const STORAGE_TOKEN = 'helpdesk_token';
const STORAGE_USER = 'helpdesk_user';

const state = reactive({
  token: localStorage.getItem(STORAGE_TOKEN) || null,
  user: JSON.parse(localStorage.getItem(STORAGE_USER) || 'null'),
});

export const auth = {
  state,
  getToken() { return state.token; },
  isAuthenticated() { return !!state.token; },
  hasRole(...roles) { return state.user && roles.includes(state.user.role); },
  setSession(token, user) {
    state.token = token;
    state.user = user;
    localStorage.setItem(STORAGE_TOKEN, token);
    localStorage.setItem(STORAGE_USER, JSON.stringify(user));
  },
  clear() {
    state.token = null;
    state.user = null;
    localStorage.removeItem(STORAGE_TOKEN);
    localStorage.removeItem(STORAGE_USER);
  },
};
