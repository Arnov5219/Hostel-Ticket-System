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
    textPrimary: rootStyle.getPropertyValue('--text-primary').trim() || (isDark ? '#E8EAED' : '#171717'),
    textSecondary: rootStyle.getPropertyValue('--text-secondary').trim() || (isDark ? '#A9B1BE' : '#454D5A'),
    textMuted: rootStyle.getPropertyValue('--text-muted').trim() || (isDark ? '#7D8696' : '#5F6877'),
    border: rootStyle.getPropertyValue('--border').trim() || (isDark ? '#272D37' : '#E3E6EB'),
    bgSurface: rootStyle.getPropertyValue('--bg-surface').trim() || (isDark ? '#161A20' : '#FFFFFF'),
    bgSubtle: rootStyle.getPropertyValue('--bg-subtle').trim() || (isDark ? '#1D222A' : '#F0F2F5'),
    gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
    accent: rootStyle.getPropertyValue('--primary').trim() || (isDark ? '#2F6FEB' : '#2563EB'),
    createdBar: rootStyle.getPropertyValue('--primary').trim() || (isDark ? '#2F6FEB' : '#2563EB'),
    resolvedBar: rootStyle.getPropertyValue('--st-resolved-dot').trim() || (isDark ? '#34D399' : '#10B981'),
    overdueBar: rootStyle.getPropertyValue('--prio-urgent').trim() || (isDark ? '#FF6B6B' : '#E03E3E'),
    categoryBar: rootStyle.getPropertyValue('--chart-2').trim() || (isDark ? '#5A9FE2' : '#3B82C4'),
    resolutionBar: rootStyle.getPropertyValue('--chart-5').trim() || (isDark ? '#A292E0' : '#8573C9'),
    charts: [
      rootStyle.getPropertyValue('--chart-1').trim() || '#5B6B84',
      rootStyle.getPropertyValue('--chart-2').trim() || '#3B82C4',
      rootStyle.getPropertyValue('--chart-3').trim() || '#2A9D8F',
      rootStyle.getPropertyValue('--chart-4').trim() || '#E0A030',
      rootStyle.getPropertyValue('--chart-5').trim() || '#8573C9',
      rootStyle.getPropertyValue('--chart-6').trim() || '#CF6A87',
    ],
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
  const fontConfig = { family: 'Inter, system-ui, sans-serif', size: 12 };

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
        const barColors = data.labels && data.labels.length > 0
          ? data.labels.map((_, i) => tokens.charts[i % tokens.charts.length])
          : tokens.categoryBar;
        new Chart(categoryCanvas, {
          type: 'bar',
          data: {
            labels: data.labels,
            datasets: [
              {
                label: 'Tickets',
                data: data.data,
                backgroundColor: barColors,
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
