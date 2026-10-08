// Kanban Board Drag and Drop using SortableJS and HTMX

document.addEventListener('DOMContentLoaded', function () {
  initKanban();
});

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
