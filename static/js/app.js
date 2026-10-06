// ============================================================
// Campus Connect 3.0 — Main JavaScript
// ============================================================

document.addEventListener('DOMContentLoaded', function () {

  // --- Sidebar mobile toggle ---
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      if (overlay) overlay.classList.toggle('open');
    });
  }
  if (overlay) {
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('open');
    });
  }

  // --- Alert auto-dismiss ---
  document.querySelectorAll('.alert').forEach(alert => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => alert.remove());
    }
    setTimeout(() => {
      alert.style.transition = 'opacity .4s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

  // --- Tabs ---
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      const tabGroup = btn.closest('.tabs-container');
      if (tabGroup) {
        tabGroup.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        tabGroup.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const panel = tabGroup.querySelector(`#${target}`);
        if (panel) panel.classList.add('active');
      }
    });
  });

  // --- Modal helpers ---
  window.openModal = function (id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('open');
  };
  window.closeModal = function (id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('open');
  };

  document.querySelectorAll('[data-modal-open]').forEach(el => {
    el.addEventListener('click', () => openModal(el.dataset.modalOpen));
  });
  document.querySelectorAll('[data-modal-close]').forEach(el => {
    el.addEventListener('click', () => closeModal(el.dataset.modalClose));
  });
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });

  // --- Toast notification helper ---
  window.showToast = function (message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = 'opacity .35s ease';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 350);
    }, 3500);
  };

  // --- Confirm dialogs for destructive actions ---
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function (e) {
      const msg = this.dataset.confirm || 'Are you sure?';
      if (!confirm(msg)) e.preventDefault();
    });
  });
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', function (e) {
      const msg = this.dataset.confirm || 'Are you sure?';
      if (!confirm(msg)) e.preventDefault();
    });
  });

  // --- Role-based registration form sections ---
  const roleInputs = document.querySelectorAll('.role-option');
  if (roleInputs.length) {
    function updateRoleFields() {
      const selected = document.querySelector('.role-option:checked');
      const role = selected ? selected.value : 'student';
      document.querySelectorAll('[data-role-section]').forEach(sec => {
        sec.style.display = sec.dataset.roleSection === role ? 'block' : 'none';
      });
    }
    roleInputs.forEach(r => r.addEventListener('change', updateRoleFields));
    updateRoleFields();
  }

  // --- Search filter (client-side for already-loaded lists) ---
  const searchInput = document.getElementById('client-search');
  if (searchInput) {
    const targetClass = searchInput.dataset.searchTarget || '.searchable-item';
    searchInput.addEventListener('input', function () {
      const q = this.value.toLowerCase();
      document.querySelectorAll(targetClass).forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(q) ? '' : 'none';
      });
    });
  }

  // --- File input label ---
  document.querySelectorAll('.file-input-wrap input[type="file"]').forEach(input => {
    const label = input.closest('.file-input-wrap')?.querySelector('.file-label-text');
    if (label) {
      input.addEventListener('change', () => {
        label.textContent = input.files[0] ? input.files[0].name : 'No file chosen';
      });
    }
  });

  // --- Admin code field show/hide ---
  const adminToggle = document.getElementById('show-admin-code');
  const adminField = document.getElementById('admin-code-field');
  if (adminToggle && adminField) {
    adminToggle.addEventListener('click', () => {
      adminField.classList.toggle('hidden');
      adminToggle.textContent = adminField.classList.contains('hidden')
        ? 'Admin access'
        : 'Hide admin access';
    });
  }

  // --- Quiz builder ---
  const quizBuilder = document.getElementById('quiz-builder');
  if (quizBuilder) {
    initQuizBuilder();
  }

  // --- Department filter (server-side redirect) ---
  const deptFilter = document.getElementById('dept-filter');
  if (deptFilter) {
    deptFilter.addEventListener('change', function () {
      const url = new URL(window.location.href);
      url.searchParams.set('department', this.value);
      window.location.href = url.toString();
    });
  }

  // --- Notifications Dropdown ---
  const notifBtn = document.getElementById('notif-btn');
  const notifDropdown = document.getElementById('notif-dropdown');
  if (notifBtn && notifDropdown) {
    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifDropdown.classList.toggle('open');
      const dot = notifBtn.querySelector('.notification-dot');
      if(dot) dot.style.display = 'none'; // clear unread state
    });
    document.addEventListener('click', (e) => {
      if (!notifBtn.contains(e.target)) {
        notifDropdown.classList.remove('open');
      }
    });
  }

  // --- Global Search UI Filter ---
  const globalSearch = document.getElementById('global-search');
  if (globalSearch) {
    globalSearch.addEventListener('input', function() {
      const q = this.value.toLowerCase();
      // Search through cards, tasks, notes on the current page
      document.querySelectorAll('.card, .task-item, .searchable-item, .action-card, .exam-card').forEach(item => {
        if(item.id === 'notif-dropdown' || item.classList.contains('sidebar-brand')) return;
        const text = item.textContent.toLowerCase();
        if (text.includes(q) || q === '') {
          item.style.display = '';
        } else {
          item.style.display = 'none';
        }
      });
    });
  }

});

// ============================================================
// QUIZ BUILDER
// ============================================================
let quizQuestions = [];

function initQuizBuilder() {
  renderQuizQuestions();
  document.getElementById('add-question-btn').addEventListener('click', () => {
    quizQuestions.push({ question: '', options: ['', '', '', ''], correct: '0', marks: 1 });
    renderQuizQuestions();
  });

  document.querySelector('#quiz-form').addEventListener('submit', function () {
    document.getElementById('questions-json').value = JSON.stringify(quizQuestions);
  });
}

function renderQuizQuestions() {
  const container = document.getElementById('questions-container');
  if (!container) return;
  container.innerHTML = '';
  quizQuestions.forEach((q, qi) => {
    const div = document.createElement('div');
    div.className = 'card mb-4';
    div.style.marginBottom = '16px';
    div.innerHTML = `
      <div class="card-header">
        <span class="card-title">Question ${qi + 1}</span>
        <button type="button" class="btn btn-ghost btn-sm" onclick="removeQuestion(${qi})">✕ Remove</button>
      </div>
      <div class="card-body">
        <div class="form-group">
          <label class="form-label">Question Text <span class="required">*</span></label>
          <input type="text" class="form-control" value="${escHtml(q.question)}"
            oninput="quizQuestions[${qi}].question = this.value" placeholder="Enter question..." />
        </div>
        <div class="form-group">
          <label class="form-label">Marks</label>
          <input type="number" class="form-control form-control-sm" value="${q.marks}" min="1"
            style="width:80px" oninput="quizQuestions[${qi}].marks = parseInt(this.value)||1" />
        </div>
        <div class="form-group">
          <label class="form-label">Options (mark correct one)</label>
          ${q.options.map((opt, oi) => `
            <div class="flex items-center gap-2 mt-2">
              <input type="radio" name="correct_${qi}" value="${oi}" ${q.correct == oi ? 'checked' : ''}
                onchange="quizQuestions[${qi}].correct = '${oi}'" />
              <input type="text" class="form-control form-control-sm" value="${escHtml(opt)}"
                oninput="quizQuestions[${qi}].options[${oi}] = this.value"
                placeholder="Option ${oi + 1}" />
            </div>
          `).join('')}
        </div>
      </div>`;
    container.appendChild(div);
  });
}

function removeQuestion(qi) {
  quizQuestions.splice(qi, 1);
  renderQuizQuestions();
}

function escHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ============================================================
// STUDY HUB TIMER
// ============================================================
(function () {
  const timerDisplay = document.getElementById('study-timer');
  if (!timerDisplay) return;

  let seconds = 0;
  let running = false;
  let interval = null;
  let sessionSaved = 0; // seconds already saved this session

  const startBtn = document.getElementById('timer-start');
  const pauseBtn = document.getElementById('timer-pause');
  const resetBtn = document.getElementById('timer-reset');

  function formatTime(s) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${pad(h)}:${pad(m)}:${pad(sec)}`;
  }
  function pad(n) { return String(n).padStart(2, '0'); }

  function updateDisplay() {
    timerDisplay.textContent = formatTime(seconds);
    updateTree();
  }

  function updateTree() {
    // Growth stages: seed → sprout → sapling → tree → big tree
    const hours = seconds / 3600;
    const svg = document.getElementById('study-tree-svg');
    if (!svg) return;
    let stage = 0;
    if (hours >= 0.25) stage = 1;
    if (hours >= 0.5)  stage = 2;
    if (hours >= 1)    stage = 3;
    if (hours >= 2)    stage = 4;

    const label = document.getElementById('tree-stage-label');
    const stageNames = ['🌱 Seed', '🌿 Sprout', '🌳 Sapling', '🌲 Tree', '🌟 Champion'];
    if (label) label.textContent = stageNames[stage];

    // Update SVG appearance
    const trunk = svg.getElementById('trunk');
    const canopy = svg.getElementById('canopy');
    const canopy2 = svg.getElementById('canopy2');
    if (!trunk) return;

    const heights = [10, 20, 35, 50, 65];
    const radii = [0, 18, 28, 38, 50];
    const trunkH = heights[stage];
    trunk.setAttribute('height', trunkH);
    trunk.setAttribute('y', 140 - trunkH);

    if (canopy) {
      if (stage >= 1) {
        canopy.setAttribute('r', radii[stage]);
        canopy.setAttribute('cy', 140 - trunkH);
        canopy.style.display = '';
      } else {
        canopy.style.display = 'none';
      }
    }
    if (canopy2) {
      if (stage >= 3) {
        canopy2.style.display = '';
        canopy2.setAttribute('r', radii[stage] * 0.7);
        canopy2.setAttribute('cy', 140 - trunkH - radii[stage] * 0.8);
      } else {
        canopy2.style.display = 'none';
      }
    }
  }

  if (startBtn) {
    startBtn.addEventListener('click', () => {
      if (!running) {
        running = true;
        interval = setInterval(() => {
          seconds++;
          updateDisplay();
          // Auto-save every 5 minutes
          if (seconds % 300 === 0) saveSession(300);
        }, 1000);
        startBtn.disabled = true;
        if (pauseBtn) pauseBtn.disabled = false;
      }
    });
  }

  if (pauseBtn) {
    pauseBtn.disabled = true;
    pauseBtn.addEventListener('click', () => {
      running = false;
      clearInterval(interval);
      startBtn.disabled = false;
      pauseBtn.disabled = true;
      // Save unsaved seconds
      const unsaved = seconds - sessionSaved;
      if (unsaved > 0) saveSession(unsaved);
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (!confirm('Reset the timer? Your progress will be saved.')) return;
      const unsaved = seconds - sessionSaved;
      if (unsaved > 0) saveSession(unsaved);
      running = false;
      clearInterval(interval);
      seconds = 0;
      sessionSaved = 0;
      if (startBtn) startBtn.disabled = false;
      if (pauseBtn) pauseBtn.disabled = true;
      updateDisplay();
    });
  }

  function saveSession(duration) {
    sessionSaved += duration;
    const today = new Date().toISOString().split('T')[0];
    fetch('/api/study/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ duration_seconds: duration, date: today }),
      credentials: 'same-origin',
    }).catch(() => {});
  }

  updateDisplay();
})();

// ============================================================
// CHAT — polling for new messages
// ============================================================
(function () {
  const chatContainer = document.getElementById('chat-messages-container');
  if (!chatContainer) return;
  const convId = chatContainer.dataset.convId;
  if (!convId) return;

  let lastTs = chatContainer.dataset.lastTs || '';

  function pollMessages() {
    const url = `/api/messages/${convId}/poll${lastTs ? '?since=' + encodeURIComponent(lastTs) : ''}`;
    fetch(url, { credentials: 'same-origin' })
      .then(r => r.json())
      .then(msgs => {
        if (msgs.length === 0) return;
        const currentUid = chatContainer.dataset.currentUid;
        msgs.forEach(msg => {
          if (lastTs && msg.created_at <= lastTs) return;
          lastTs = msg.created_at;
          appendMessage(msg, currentUid);
        });
        chatContainer.scrollTop = chatContainer.scrollHeight;
      })
      .catch(() => {});
  }

  function appendMessage(msg, currentUid) {
    const isSent = msg.sender_uid === currentUid;
    const bubble = document.createElement('div');
    bubble.className = `msg-bubble ${isSent ? 'sent' : 'received'}`;
    bubble.dataset.msgId = msg.id;

    let content = '';
    if (msg.content) content += `<div class="msg-content">${escHtml(msg.content)}</div>`;
    if (msg.file_url) {
      content += `<div class="msg-content">
        <a href="${msg.file_url}" target="_blank" style="color:inherit;text-decoration:underline">
          📎 ${escHtml(msg.file_name || 'File')}
        </a>
      </div>`;
    }
    content += `<span class="msg-time">${formatMsgTime(msg.created_at)}</span>`;
    bubble.innerHTML = content;
    chatContainer.appendChild(bubble);
  }

  function formatMsgTime(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return ''; }
  }

  function escHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Scroll to bottom on load
  chatContainer.scrollTop = chatContainer.scrollHeight;

  // Poll every 4 seconds
  setInterval(pollMessages, 4000);
})();
