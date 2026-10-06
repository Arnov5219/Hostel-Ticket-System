// Chart.js builders using token colors

document.addEventListener('DOMContentLoaded', function () {
  initDashboardCharts();
});

function initDashboardCharts() {
  const trendCanvas = document.getElementById('chart-trend');
  const categoryCanvas = document.getElementById('chart-category');
  const resolutionCanvas = document.getElementById('chart-resolution');

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
                backgroundColor: '#2490EF',
                borderRadius: 4,
              },
              {
                label: 'Resolved',
                data: data.resolved,
                backgroundColor: '#1F7A4D',
                borderRadius: 4,
              },
              {
                label: 'Overdue',
                data: data.overdue,
                backgroundColor: '#C53030',
                borderRadius: 4,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'top', labels: { boxWidth: 12, font: { family: 'Inter', size: 11 } } },
            },
            scales: {
              x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } },
              y: { beginAtZero: true, grid: { color: '#E5E7EB' }, ticks: { font: { family: 'Inter', size: 11 } } },
            },
          },
        });
      });
  }

  if (categoryCanvas) {
    fetch('/dashboard/api/by-category/')
      .then(res => res.json())
      .then(data => {
        new Chart(categoryCanvas, {
          type: 'bar',
          data: {
            labels: data.labels,
            datasets: [
              {
                label: 'Tickets',
                data: data.data,
                backgroundColor: '#B45309',
                borderRadius: 4,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 10 } } },
              y: { beginAtZero: true, grid: { color: '#E5E7EB' }, ticks: { font: { family: 'Inter', size: 11 } } },
            },
          },
        });
      });
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
                backgroundColor: '#6B3FA0',
                borderRadius: 4,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } },
              y: { beginAtZero: true, grid: { color: '#E5E7EB' }, ticks: { font: { family: 'Inter', size: 11 } } },
            },
          },
        });
      });
  }
}
