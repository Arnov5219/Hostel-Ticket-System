// Chart.js builders using token colors and strict whole-number ticks (Fix B-05, U-13)

document.addEventListener('DOMContentLoaded', function () {
  initDashboardCharts();
});

function initDashboardCharts() {
  const trendCanvas = document.getElementById('chart-trend');
  const categoryCanvas = document.getElementById('chart-category');
  const resolutionCanvas = document.getElementById('chart-resolution');

  // Chart typography and grid defaults
  const fontConfig = { family: 'Inter, system-ui, sans-serif', size: 11 };
  const gridColor = 'rgba(226, 232, 240, 0.8)';

  if (trendCanvas) {
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
                backgroundColor: '#1a56db',
                borderRadius: 4,
                maxBarThickness: 36,
                categoryPercentage: 0.7,
              },
              {
                label: 'Resolved',
                data: data.resolved,
                backgroundColor: '#059669',
                borderRadius: 4,
                maxBarThickness: 36,
                categoryPercentage: 0.7,
              },
              {
                label: 'Overdue',
                data: data.overdue,
                backgroundColor: '#e03131',
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
                  color: '#475569',
                },
              },
              tooltip: {
                backgroundColor: '#ffffff',
                titleColor: '#0f172a',
                bodyColor: '#334155',
                borderColor: '#e2e8f0',
                borderWidth: 1,
                boxPadding: 4,
                padding: 10,
              },
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { font: fontConfig, color: '#64748b' },
              },
              y: {
                beginAtZero: true,
                grid: { color: gridColor, borderDash: [4, 4] },
                ticks: {
                  font: fontConfig,
                  color: '#64748b',
                  precision: 0,
                  stepSize: 1,
                  callback: function(val) {
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
                // Fix U-13: Muted blue-slate series, NOT brown
                backgroundColor: '#3b82f6',
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
                backgroundColor: '#ffffff',
                titleColor: '#0f172a',
                bodyColor: '#334155',
                borderColor: '#e2e8f0',
                borderWidth: 1,
                padding: 10,
              },
            },
            scales: {
              x: {
                grid: isHorizontal ? { color: gridColor, borderDash: [4, 4] } : { display: false },
                ticks: {
                  font: { family: 'Inter', size: 10 },
                  color: '#64748b',
                  precision: 0,
                  stepSize: isHorizontal ? 1 : undefined,
                  callback: isHorizontal
                    ? function(val) { return Number.isInteger(val) ? val : null; }
                    : undefined,
                },
              },
              y: {
                beginAtZero: true,
                grid: isHorizontal ? { display: false } : { color: gridColor, borderDash: [4, 4] },
                ticks: {
                  font: fontConfig,
                  color: '#64748b',
                  precision: 0,
                  stepSize: isHorizontal ? undefined : 1,
                  callback: isHorizontal
                    ? undefined
                    : function(val) { return Number.isInteger(val) ? val : null; },
                },
              },
            },
          },
        });
      })
      .catch(() => {});
  }

  if (resolutionCanvas) {
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
                // Muted indigo/slate series
                backgroundColor: '#6366f1',
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
                backgroundColor: '#ffffff',
                titleColor: '#0f172a',
                bodyColor: '#334155',
                borderColor: '#e2e8f0',
                borderWidth: 1,
                padding: 10,
                callbacks: {
                  label: function(context) {
                    return `Avg time: ${context.parsed.y}h`;
                  },
                },
              },
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { font: fontConfig, color: '#64748b' },
              },
              y: {
                beginAtZero: true,
                grid: { color: gridColor, borderDash: [4, 4] },
                ticks: {
                  font: fontConfig,
                  color: '#64748b',
                  precision: 0,
                  stepSize: 1,
                  callback: function(val) {
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
