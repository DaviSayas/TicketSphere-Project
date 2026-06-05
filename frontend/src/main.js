// Application entry point.
const { createApp, h } = Vue;
import router from './router/index.js';

const AppRoot = { template: '<router-view></router-view>' };

createApp(AppRoot).use(router).mount('#app');
