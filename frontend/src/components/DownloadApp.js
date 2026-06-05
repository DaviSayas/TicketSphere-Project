export const DownloadApp = {
  template: `
    <div class="download-app">
      <button @click="showModal = true" class="download-btn" title="Instalar app">
        📱 Instalar App
      </button>

      <div v-if="showModal" class="modal-overlay" @click="showModal = false">
        <div class="modal" @click.stop>
          <button class="close-btn" @click="showModal = false">✕</button>

          <h2>Instalar Helpdesk</h2>
          <p>Escolha como prefere usar a aplicação</p>

          <div class="options">
            <div class="option" v-if="canInstallPWA">
              <span class="icon">🌐</span>
              <h3>Web App</h3>
              <p>Instale no navegador. Funciona offline.</p>
              <ul>
                <li>✓ Funciona offline</li>
                <li>✓ Sincronização automática</li>
                <li>✓ Notificações</li>
              </ul>
              <button @click="installPWA" class="btn-primary">Instalar Web App</button>
            </div>

            <div class="option">
              <span class="icon">💻</span>
              <h3>Desktop</h3>
              <p>Descarregue como aplicação nativa.</p>
              <ul>
                <li>✓ Windows, Mac, Linux</li>
                <li>✓ Melhor performance</li>
                <li>✓ Atualizações automáticas</li>
              </ul>
              <div class="download-links">
                <a href="https://github.com/seu-usuario/ticket-system/releases/download/v1.0.0/Helpdesk-Setup.exe" target="_blank" class="btn-secondary">📥 Windows</a>
                <a href="https://github.com/seu-usuario/ticket-system/releases/download/v1.0.0/Helpdesk.dmg" target="_blank" class="btn-secondary">📥 macOS</a>
                <a href="https://github.com/seu-usuario/ticket-system/releases/download/v1.0.0/Helpdesk.AppImage" target="_blank" class="btn-secondary">📥 Linux</a>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="showPrompt" class="install-prompt">
        <span class="icon">📱</span>
        <div>
          <p class="title">Instalar Helpdesk?</p>
          <p class="text">Adicione à sua tela inicial</p>
        </div>
        <div class="buttons">
          <button @click="showPrompt = false" class="btn-ghost">Não</button>
          <button @click="installPrompt" class="btn-primary">Instalar</button>
        </div>
      </div>
    </div>
  `,

  data() {
    return {
      showModal: false,
      showPrompt: false,
      canInstallPWA: false
    };
  },

  mounted() {
    // Mostrar prompt nativo
    window.addEventListener('pwa-prompt-ready', () => {
      this.canInstallPWA = true;
      this.showPrompt = true;
    });

    // Verificar se já está instalada
    if (window.matchMedia('(display-mode: standalone)').matches) {
      this.canInstallPWA = false;
    }
  },

  methods: {
    installPWA() {
      window.installPWA?.();
      this.showModal = false;
    },

    async installPrompt() {
      if (window.deferredPrompt) {
        window.deferredPrompt.prompt();
        const { outcome } = await window.deferredPrompt.userChoice;
        console.log(`Instalação: ${outcome}`);
        this.showPrompt = false;
      }
    }
  }
};
