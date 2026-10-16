// Kanban Board Drag and Drop using SortableJS and 2-way IntersectionObserver sync

document.addEventListener('DOMContentLoaded', function () {
  initKanban();
  initKanbanTabSync();
});

function initKanbanTabSync() {
  const tabStrip = document.getElementById('kanban-tab-strip');
  const board = document.getElementById('kanban-board');
  const columns = document.querySelectorAll('.kanban-column');
  if (!tabStrip || !board || !columns.length) return;

  const tabButtons = tabStrip.querySelectorAll('.kanban-tab-btn');

  function setActiveTab(status) {
    tabButtons.forEach(function (btn) {
      const isActive = btn.getAttribute('data-status') === status;
      btn.classList.toggle('active', isActive);
      if (isActive) {
        btn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }
    });
  }

  tabButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const status = btn.getAttribute('data-status');
      const targetCol = document.querySelector(`.kanban-column[data-status="${status}"]`);
      if (targetCol) {
        targetCol.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        setActiveTab(status);
      }
    });
  });

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          const status = entry.target.getAttribute('data-status');
          if (status) {
            setActiveTab(status);
          }
        }
      });
    }, {
      root: board,
      threshold: 0.5,
    });

    columns.forEach(function (col) {
      observer.observe(col);
    });
  }
}

function updateColumnCounts() {
  const columns = document.querySelectorAll('.kanban-column');
  columns.forEach(function (col) {
    const status = col.getAttribute('data-status');
    const container = col.querySelector('.kanban-cards-container');
    const cards = container ? container.querySelectorAll('.kanban-card') : [];
    const count = cards.length;

    // Update column header count
    const colCountEl = col.querySelector('.kanban-col-count');
    if (colCountEl) colCountEl.textContent = count;

    // Update tab strip count
    const tabBtn = document.getElementById(`tab-btn-${status}`);
    if (tabBtn) {
      const tabCountEl = tabBtn.querySelector('.tab-count');
      if (tabCountEl) tabCountEl.textContent = `(${count})`;
    }

    // Toggle empty column state
    let emptyEl = container.querySelector('.kanban-empty-col');
    if (count === 0) {
      if (!emptyEl) {
        emptyEl = document.createElement('div');
        emptyEl.className = 'kanban-empty-col';
        emptyEl.innerHTML = `<i data-lucide="inbox" style="width: 20px; height: 20px; opacity: 0.5; margin-bottom: 4px;"></i><span>No tickets in ${col.querySelector('.kanban-col-title')?.textContent || status}</span>`;
        container.appendChild(emptyEl);
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    } else if (emptyEl) {
      emptyEl.remove();
    }
  });
}

function initKanban() {
  const containers = document.querySelectorAll('.kanban-cards-container');
  if (!containers.length || typeof Sortable === 'undefined') return;

  containers.forEach(function (container) {
    new Sortable(container, {
      group: 'kanban-board',
      animation: 150,
      delay: 200,
      delayOnTouchOnly: true,
      touchStartThreshold: 5,
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      dragClass: 'sortable-drag',
      onEnd: function (evt) {
        const item = evt.item;
        const ticketNo = item.getAttribute('data-ticket-no');
        const targetColumn = evt.to.closest('.kanban-column');
        const newStatus = targetColumn ? targetColumn.getAttribute('data-status') : null;
        const oldContainer = evt.from;

        if (!ticketNo || !newStatus || evt.from === evt.to) {
          return;
        }

        // Send POST to update status
        const csrfToken = getCookie('csrftoken');
        const formData = new FormData();
        formData.append('status', newStatus);

        fetch(`/tickets/${ticketNo}/move/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: formData,
        })
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, status: res.status, data: data };
            });
          })
          .then(function (result) {
            if (!result.ok) {
              // Illegal transition or permission error: revert card position!
              oldContainer.insertBefore(item, oldContainer.children[evt.oldIndex] || null);
              showToast(result.data.error || 'Cannot move ticket to this status.', 'error');
            } else {
              showToast(`Ticket ${ticketNo} moved to ${newStatus.replace('_', ' ')}.`, 'success');
              // Update badge in card if needed
              const dot = item.querySelector('.status-indicator');
              if (dot) dot.className = `status-indicator ${newStatus.toLowerCase()}`;
              updateColumnCounts();
            }
          })
          .catch(function () {
            oldContainer.insertBefore(item, oldContainer.children[evt.oldIndex] || null);
            showToast('Network error while updating ticket.', 'error');
          });
      },
    });
  });
}
