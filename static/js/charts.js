// Chart.js builders with dynamic token resolution and themechange re-rendering

document.addEventListener('DOMContentLoaded', function () {
  initDashboardCharts();
});

window.addEventListener('themechange', function () {
  initDashboardCharts();
});

function getChartThemeTokens() {
  const rootStyle = getComputedStyle(document.documentElement);
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

  return {
    isDark: isDark,
    textPrimary: rootStyle.getPropertyValue('--text-primary').trim() || (isDark ? '#E8EAED' : '#0F172A'),
    textSecondary: rootStyle.getPropertyValue('--text-secondary').trim() || (isDark ? '#A9B1BE' : '#475569'),
    textMuted: rootStyle.getPropertyValue('--text-muted').trim() || (isDark ? '#7D8696' : '#64748B'),
    border: rootStyle.getPropertyValue('--border').trim() || (isDark ? '#272D37' : '#E2E8F0'),
    bgSurface: rootStyle.getPropertyValue('--bg-surface').trim() || (isDark ? '#161A20' : '#FFFFFF'),
    bgSubtle: rootStyle.getPropertyValue('--bg-subtle').trim() || (isDark ? '#1D222A' : '#F1F5F9'),
    gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(226, 232, 240, 0.8)',
    accent: rootStyle.getPropertyValue('--accent').trim() || '#3B82F6',
    createdBar: isDark ? '#4DA3FF' : '#1A56DB',
    resolvedBar: isDark ? '#5FD39A' : '#059669',
    overdueBar: isDark ? '#FF8A8A' : '#E03131',
    categoryBar: isDark ? '#7DB8FF' : '#3B82F6',
    resolutionBar: isDark ? '#C3A6FF' : '#6366F1',
  };
}

function initDashboardCharts() {
  const trendCanvas = document.getElementById('chart-trend');
  const categoryCanvas = document.getElementById('chart-category');
  const resolutionCanvas = document.getElementById('chart-resolution');

  if (!trendCanvas && !categoryCanvas && !resolutionCanvas) {
    return;
  }

  const tokens = getChartThemeTokens();
  const fontConfig = { family: 'Inter, system-ui, sans-serif', size: 11 };

  if (trendCanvas) {
    const existing = Chart.getChart(trendCanvas);
    if (existing) existing.destroy();

    fetch('/dashboard/api/trend/')
      .then(res => res.json())
      .then(data => {
        new Chart(trendCanvas, {
          type: 'bar',
          data: {
            labels: data.labels,
            datasets: [
              {
                label: 'Created',
                data: data.created,
                backgroundColor: tokens.createdBar,
                borderRadius: 4,
                maxBarThickness: 36,
                categoryPercentage: 0.7,
              },
              {
                label: 'Resolved',
                data: data.resolved,
                backgroundColor: tokens.resolvedBar,
                borderRadius: 4,
                maxBarThickness: 36,
                categoryPercentage: 0.7,
              },
              {
                label: 'Overdue',
                data: data.overdue,
                backgroundColor: tokens.overdueBar,
                borderRadius: 4,
                maxBarThickness: 36,
                categoryPercentage: 0.7,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'top',
                labels: {
                  boxWidth: 10,
                  boxHeight: 10,
                  usePointStyle: true,
                  pointStyle: 'circle',
                  font: fontConfig,
                  color: tokens.textSecondary,
                },
              },
              tooltip: {
                backgroundColor: tokens.bgSurface,
                titleColor: tokens.textPrimary,
                bodyColor: tokens.textSecondary,
                borderColor: tokens.border,
                borderWidth: 1,
                boxPadding: 4,
                padding: 10,
              },
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { font: fontConfig, color: tokens.textMuted },
              },
              y: {
                beginAtZero: true,
                grid: { color: tokens.gridColor, borderDash: [4, 4] },
                ticks: {
                  font: fontConfig,
                  color: tokens.textMuted,
                  precision: 0,
                  stepSize: 1,
                  callback: function (val) {
                    return Number.isInteger(val) ? val : null;
                  },
                },
              },
            },
          },
        });
      })
      .catch(() => {});
  }

  if (categoryCanvas) {
    const existing = Chart.getChart(categoryCanvas);
    if (existing) existing.destroy();

    fetch('/dashboard/api/by-category/')
      .then(res => res.json())
      .then(data => {
        const isHorizontal = data.labels && data.labels.length > 5;
        new Chart(categoryCanvas, {
          type: 'bar',
          data: {
            labels: data.labels,
            datasets: [
              {
                label: 'Tickets',
                data: data.data,
                backgroundColor: tokens.categoryBar,
                borderRadius: 4,
                maxBarThickness: 40,
                categoryPercentage: 0.7,
              },
            ],
          },
          options: {
            indexAxis: isHorizontal ? 'y' : 'x',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: tokens.bgSurface,
                titleColor: tokens.textPrimary,
                bodyColor: tokens.textSecondary,
                borderColor: tokens.border,
                borderWidth: 1,
                padding: 10,
              },
            },
            scales: {
              x: {
                grid: isHorizontal ? { color: tokens.gridColor, borderDash: [4, 4] } : { display: false },
                ticks: {
                  font: { family: 'Inter', size: 10 },
                  color: tokens.textMuted,
                  precision: 0,
                  stepSize: isHorizontal ? 1 : undefined,
                  callback: isHorizontal
                    ? function (val) { return Number.isInteger(val) ? val : null; }
                    : undefined,
                },
              },
              y: {
                beginAtZero: true,
                grid: isHorizontal ? { display: false } : { color: tokens.gridColor, borderDash: [4, 4] },
                ticks: {
                  font: fontConfig,
                  color: tokens.textMuted,
                  precision: 0,
                  stepSize: isHorizontal ? undefined : 1,
                  callback: isHorizontal
                    ? undefined
                    : function (val) { return Number.isInteger(val) ? val : null; },
                },
              },
            },
          },
        });
      })
      .catch(() => {});
  }

  if (resolutionCanvas) {
    const existing = Chart.getChart(resolutionCanvas);
    if (existing) existing.destroy();

    fetch('/dashboard/api/resolution-time/')
      .then(res => res.json())
      .then(data => {
        new Chart(resolutionCanvas, {
          type: 'bar',
          data: {
            labels: data.labels,
            datasets: [
              {
                label: 'Avg Hours',
                data: data.data,
                backgroundColor: tokens.resolutionBar,
                borderRadius: 4,
                maxBarThickness: 36,
                categoryPercentage: 0.7,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: tokens.bgSurface,
                titleColor: tokens.textPrimary,
                bodyColor: tokens.textSecondary,
                borderColor: tokens.border,
                borderWidth: 1,
                padding: 10,
                callbacks: {
                  label: function (context) {
                    return `Avg time: ${context.parsed.y}h`;
                  },
                },
              },
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { font: fontConfig, color: tokens.textMuted },
              },
              y: {
                beginAtZero: true,
                grid: { color: tokens.gridColor, borderDash: [4, 4] },
                ticks: {
                  font: fontConfig,
                  color: tokens.textMuted,
                  precision: 0,
                  stepSize: 1,
                  callback: function (val) {
                    return Number.isInteger(val) ? val + 'h' : '';
                  },
                },
              },
            },
          },
        });
      })
      .catch(() => {});
  }
}
