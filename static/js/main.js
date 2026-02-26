// Dynamic form row templates
const rowTemplates = {
    medication: `
        <div class="row align-items-end mb-2 dynamic-row">
            <div class="col-md-3"><label class="form-label">Name</label><input type="text" name="med_name[]" class="form-control"></div>
            <div class="col-md-3"><label class="form-label">Dosage</label><input type="text" name="med_dosage[]" class="form-control"></div>
            <div class="col-md-4"><label class="form-label">Times (comma-separated HH:MM)</label><input type="text" name="med_times[]" class="form-control" placeholder="08:00, 14:00"></div>
            <div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm remove-row"><i class="bi bi-trash"></i></button></div>
        </div>`,
    meal: `
        <div class="row align-items-end mb-2 dynamic-row">
            <div class="col-md-3"><label class="form-label">Type</label>
                <select name="meal_type[]" class="form-select">
                    <option value="breakfast">Breakfast</option><option value="lunch">Lunch</option>
                    <option value="dinner">Dinner</option><option value="snack">Snack</option>
                </select></div>
            <div class="col-md-4"><label class="form-label">Description</label><input type="text" name="meal_description[]" class="form-control"></div>
            <div class="col-md-3"><label class="form-label">Time</label><input type="time" name="meal_time[]" class="form-control"></div>
            <div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm remove-row"><i class="bi bi-trash"></i></button></div>
        </div>`,
    activity: `
        <div class="row align-items-end mb-2 dynamic-row">
            <div class="col-md-3"><label class="form-label">Name</label><input type="text" name="activity_name[]" class="form-control"></div>
            <div class="col-md-3"><label class="form-label">Description</label><input type="text" name="activity_description[]" class="form-control"></div>
            <div class="col-md-2"><label class="form-label">Day</label>
                <select name="activity_day[]" class="form-select">
                    <option value="daily">Daily</option><option value="monday">Mon</option><option value="tuesday">Tue</option>
                    <option value="wednesday">Wed</option><option value="thursday">Thu</option><option value="friday">Fri</option>
                    <option value="saturday">Sat</option><option value="sunday">Sun</option>
                </select></div>
            <div class="col-md-2"><label class="form-label">Time</label><input type="time" name="activity_time[]" class="form-control"></div>
            <div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm remove-row"><i class="bi bi-trash"></i></button></div>
        </div>`,
    habit: `
        <div class="row align-items-end mb-2 dynamic-row">
            <div class="col-md-4"><label class="form-label">Name</label><input type="text" name="habit_name[]" class="form-control"></div>
            <div class="col-md-6"><label class="form-label">Description</label><input type="text" name="habit_description[]" class="form-control"></div>
            <div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm remove-row"><i class="bi bi-trash"></i></button></div>
        </div>`,
    friend: `
        <div class="row align-items-end mb-2 dynamic-row">
            <div class="col-md-3"><label class="form-label">Name</label><input type="text" name="friend_name[]" class="form-control"></div>
            <div class="col-md-3"><label class="form-label">Phone</label><input type="tel" name="friend_phone[]" class="form-control"></div>
            <div class="col-md-4"><label class="form-label">Relationship</label><input type="text" name="friend_relationship[]" class="form-control"></div>
            <div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm remove-row"><i class="bi bi-trash"></i></button></div>
        </div>`,
};

function addRow(containerId, type) {
    const container = document.getElementById(containerId);
    if (container && rowTemplates[type]) {
        container.insertAdjacentHTML('beforeend', rowTemplates[type]);
    }
}

// Remove row handler (event delegation)
document.addEventListener('click', function(e) {
    if (e.target.closest('.remove-row')) {
        e.target.closest('.dynamic-row').remove();
    }
});

// Notification polling (every 30 seconds)
function pollNotifications() {
    fetch('/api/notifications/unread')
        .then(r => r.json())
        .then(data => {
            const badge = document.querySelector('.notification-badge');
            const list = document.getElementById('notif-list');
            if (!badge || !list) return;

            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'inline';
                list.innerHTML = data.notifications.map(n =>
                    `<li><span class="dropdown-item-text small">${n.message}<br><small class="text-muted">${n.created_at}</small></span></li>`
                ).join('');
            } else {
                badge.style.display = 'none';
                list.innerHTML = '<span class="dropdown-item-text text-muted">No new notifications</span>';
            }
        })
        .catch(() => {});
}

// Start polling if logged in
if (document.querySelector('.notification-badge')) {
    pollNotifications();
    setInterval(pollNotifications, 30000);
}
