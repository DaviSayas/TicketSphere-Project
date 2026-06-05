// Admin dashboard — metric cards, daily-series chart, category distribution chart, top techs.
const { ref, onMounted, onBeforeUnmount, nextTick } = Vue;
import { api, API_BASE_URL } from '../services/http.js';
import { auth } from '../services/auth.js';

export default {
  name: 'AdminDashboardView',
  setup() {
    const data = ref(null);
    const loading = ref(true);
    const error = ref('');
    const dailyChartRef = ref(null);
    const categoryChartRef = ref(null);
    let dailyChart = null;
    let categoryChart = null;
    const reportMonth = ref(''); // YYYY-MM
    const downloading = ref(false);

    async function load() {
      loading.value = true;
      error.value = '';
      try {
        data.value = await api.get('/admin/dashboard');
        await nextTick();
        renderCharts();
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    function renderCharts() {
      if (!data.value || !window.Chart) return;

      // Destroy previous instances
      if (dailyChart) { dailyChart.destroy(); dailyChart = null; }
      if (categoryChart) { categoryChart.destroy(); categoryChart = null; }

      const palette = {
        accent: '#0f4d4d',
        accentSoft: '#d6e7e3',
        ink: '#1c1f1e',
        ok: '#15803d',
        warn: '#c2900b',
        danger: '#b91c1c',
      };

      // Daily series bar chart (created vs resolved)
      if (dailyChartRef.value) {
        dailyChart = new Chart(dailyChartRef.value, {
          type: 'bar',
          data: {
            labels: data.value.daily_series.map(d => d.date.slice(5)), // MM-DD
            datasets: [
              {
                label: 'Criados',
                data: data.value.daily_series.map(d => d.created),
                backgroundColor: palette.accent,
                borderRadius: 2,
              },
              {
                label: 'Resolvidos',
                data: data.value.daily_series.map(d => d.resolved),
                backgroundColor: palette.ok,
                borderRadius: 2,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'bottom', labels: { font: { family: 'Inter, sans-serif', size: 12 } } },
            },
            scales: {
              x: { grid: { display: false }, ticks: { font: { family: 'JetBrains Mono, monospace', size: 10 } } },
              y: { beginAtZero: true, grid: { color: '#e8e3d6' }, ticks: { font: { family: 'JetBrains Mono, monospace', size: 10 }, precision: 0 } },
            },
          },
        });
      }

      // Category distribution doughnut
      if (categoryChartRef.value && data.value.category_distribution.length) {
        const colors = ['#0f4d4d', '#c2900b', '#b91c1c', '#1d4ed8', '#7c2d8a', '#475569'];
        categoryChart = new Chart(categoryChartRef.value, {
          type: 'doughnut',
          data: {
            labels: data.value.category_distribution.map(c => c.category),
            datasets: [{
              data: data.value.category_distribution.map(c => c.count),
              backgroundColor: colors,
              borderWidth: 0,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'right', labels: { font: { family: 'Inter, sans-serif', size: 12 }, padding: 12 } },
            },
            cutout: '60%',
          },
        });
      }
    }

    async function downloadReport() {
      downloading.value = true;
      try {
        const params = reportMonth.value ? { month: reportMonth.value } : null;
        const res = await api.raw('/admin/reports/monthly', params);
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(txt || `Erro ${res.status}`);
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `relatorio_${reportMonth.value || 'atual'}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (e) {
        alert(e.message);
      } finally {
        downloading.value = false;
      }
    }

    onMounted(load);
    onBeforeUnmount(() => {
      if (dailyChart) dailyChart.destroy();
      if (categoryChart) categoryChart.destroy();
    });

    return { data, loading, error, dailyChartRef, categoryChartRef, reportMonth, downloading, downloadReport };
  },
  template: `
    <div>
      <div class="page-header">
        <div>
          <h1 class="page-title">Dashboard</h1>
          <div class="page-subtitle">Métricas dos últimos 30 dias</div>
        </div>
        <div class="row">
          <input v-model="reportMonth" type="month" class="input" style="padding:7px 10px; font-size:13px;">
          <button class="btn btn-secondary" @click="downloadReport" :disabled="downloading">
            <span v-if="downloading" class="spinner"></span>
            <span v-else>↓ Exportar CSV</span>
          </button>
        </div>
      </div>

      <div v-if="loading" class="spinner-block"><div class="spinner"></div></div>
      <div v-else-if="error" class="alert alert-error">{{ error }}</div>

      <template v-else-if="data">
        <div class="metric-grid">
          <div class="metric">
            <div class="metric-label">Tickets abertos</div>
            <div class="metric-value">{{ data.cards.open_tickets }}</div>
          </div>
          <div class="metric success">
            <div class="metric-label">Resolvidos (30d)</div>
            <div class="metric-value">{{ data.cards.resolved_last_30d }}</div>
          </div>
          <div class="metric danger">
            <div class="metric-label">SLA excedido (30d)</div>
            <div class="metric-value">{{ data.cards.sla_breached_last_30d }}</div>
          </div>
          <div class="metric warn">
            <div class="metric-label">Tempo médio resolução</div>
            <div class="metric-value">{{ data.cards.avg_resolution_hours }}<span class="metric-unit">h</span></div>
          </div>
        </div>

        <div class="dashboard-grid">
          <div class="chart-card">
            <h3>Volume diário</h3>
            <div class="chart-wrap"><canvas ref="dailyChartRef"></canvas></div>
          </div>
          <div class="chart-card">
            <h3>Distribuição por categoria</h3>
            <div v-if="data.category_distribution.length === 0" class="empty-state">
              <p class="text-mute">Sem dados</p>
            </div>
            <div v-else class="chart-wrap"><canvas ref="categoryChartRef"></canvas></div>
          </div>
        </div>

        <div class="panel mt-5">
          <h3 style="font-family:var(--font-display); font-size:20px; font-weight:500; margin-bottom:16px;">Top técnicos (30d)</h3>
          <table v-if="data.top_techs.length" class="ticket-table" style="border-radius:4px;">
            <thead>
              <tr>
                <th>Técnico</th>
                <th>Resolvidos</th>
                <th>Tempo médio</th>
                <th>Cumprimento SLA</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in data.top_techs" :key="t.user_id">
                <td>{{ t.name }}</td>
                <td><span class="text-mono">{{ t.resolved }}</span></td>
                <td><span class="text-mono">{{ t.avg_resolution_hours }}h</span></td>
                <td><span class="text-mono">{{ t.sla_compliance_pct }}%</span></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-mute">Sem técnicos com tickets resolvidos no período.</div>
        </div>
      </template>
    </div>
  `,
};
