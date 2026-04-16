/* ── AgentHire — Main JS ────────────────────────────────────────────────────── */

// ── Toasts ───────────────────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type]}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-out');
    setTimeout(() => toast.remove(), 200);
  }, duration);
}

// ── Modals ────────────────────────────────────────────────────────────────────
function openModal(id) {
  const overlay = document.getElementById(id);
  if (overlay) { overlay.classList.add('open'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const overlay = document.getElementById(id);
  if (overlay) { overlay.classList.remove('open'); document.body.style.overflow = ''; }
}

document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    closeModal(e.target.id);
  }
  if (e.target.classList.contains('modal-close') || e.target.closest('.modal-close')) {
    const overlay = e.target.closest('.modal-overlay');
    if (overlay) closeModal(overlay.id);
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => closeModal(m.id));
  }
});

// ── Tabs ──────────────────────────────────────────────────────────────────────
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.tab-btn');
  if (!btn) return;
  const target  = btn.dataset.tab;
  const tabsWrap = btn.closest('.tabs-wrapper');
  if (!tabsWrap) return;
  tabsWrap.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  tabsWrap.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  const content = tabsWrap.querySelector(`[data-tab-content="${target}"]`);
  if (content) content.classList.add('active');
});

// ── Role Switcher ─────────────────────────────────────────────────────────────
const rolePaths = {
  buyer:  '/',
  seller: '/seller/dashboard',
  admin:  '/admin/dashboard',
};
document.querySelectorAll('.role-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const role = btn.dataset.role;
    if (rolePaths[role]) window.location.href = rolePaths[role];
  });
});

// ── Wallet Connect Mock ───────────────────────────────────────────────────────
const walletBtn = document.getElementById('wallet-btn');
if (walletBtn) {
  walletBtn.addEventListener('click', () => {
    const connected = walletBtn.dataset.connected === 'true';
    if (!connected) {
      walletBtn.innerHTML = `<span class="dot"></span> 0x3f8a...c12d`;
      walletBtn.dataset.connected = 'true';
      showToast('Wallet connected: 0x3f8a...c12d', 'success');
    } else {
      walletBtn.innerHTML = `<span>Connect Wallet</span>`;
      walletBtn.dataset.connected = 'false';
      showToast('Wallet disconnected', 'info');
    }
  });
}

// ── Live Price Ticker ─────────────────────────────────────────────────────────
function startLivePriceTicker(agentId) {
  const priceEl = document.getElementById('live-price');
  if (!priceEl) return;

  setInterval(async () => {
    try {
      const res  = await fetch(`/api/price/${agentId}`);
      const data = await res.json();
      const formatted = data.price < 1 ? data.price.toFixed(5) : data.price.toFixed(4);
      priceEl.textContent = `$${formatted}`;
      // flash effect
      priceEl.style.color = 'var(--success)';
      setTimeout(() => { priceEl.style.color = ''; }, 600);
    } catch (_) {}
  }, 4000);
}

// ── Tier Selection ────────────────────────────────────────────────────────────
document.querySelectorAll('.tier-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.tier-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    const tier = card.dataset.tier;
    const hidden = document.getElementById('selected-tier');
    if (hidden) hidden.value = tier;
    // update price preview
    const priceEl = document.getElementById('verification-price');
    if (priceEl) priceEl.textContent = tier === 'thorough' ? '$50.00 USDC' : '$10.00 USDC';
  });
});

// ── Star Rating ───────────────────────────────────────────────────────────────
function initStarRating(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const stars = container.querySelectorAll('.star-btn');
  stars.forEach((star, idx) => {
    star.addEventListener('mouseenter', () => {
      stars.forEach((s, i) => s.classList.toggle('active', i <= idx));
    });
    star.addEventListener('click', () => {
      stars.forEach((s, i) => {
        s.classList.toggle('active', i <= idx);
        s.dataset.selected = i <= idx ? 'true' : 'false';
      });
      const ratingInput = document.getElementById('rating-value');
      if (ratingInput) ratingInput.value = idx + 1;
    });
  });
  container.addEventListener('mouseleave', () => {
    const selected = [...stars].findIndex(s => s.dataset.selected === 'true' && [...stars].slice(stars.length - 1)[0] === s);
    const activeStars = [...stars].filter(s => s.dataset.selected === 'true');
    if (activeStars.length === 0) stars.forEach(s => s.classList.remove('active'));
  });
}

// ── Multi-step Form ───────────────────────────────────────────────────────────
let currentStep = 1;
const totalSteps = 4;

function goToStep(step) {
  if (step < 1 || step > totalSteps) return;
  document.querySelectorAll('.form-step').forEach((el, i) => {
    el.style.display = i + 1 === step ? 'block' : 'none';
  });
  document.querySelectorAll('.step-item').forEach((el, i) => {
    el.classList.remove('active', 'done');
    if (i + 1 < step) el.classList.add('done');
    if (i + 1 === step) el.classList.add('active');
  });
  currentStep = step;
  const prevBtn = document.getElementById('step-prev');
  const nextBtn = document.getElementById('step-next');
  const submitBtn = document.getElementById('step-submit');
  if (prevBtn)   prevBtn.style.display  = step > 1 ? 'inline-flex' : 'none';
  if (nextBtn)   nextBtn.style.display  = step < totalSteps ? 'inline-flex' : 'none';
  if (submitBtn) submitBtn.style.display = step === totalSteps ? 'inline-flex' : 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

const nextBtn = document.getElementById('step-next');
const prevBtn = document.getElementById('step-prev');
if (nextBtn) nextBtn.addEventListener('click', () => {
  goToStep(currentStep + 1);
  showToast('Progress saved', 'success');
});
if (prevBtn) prevBtn.addEventListener('click', () => goToStep(currentStep - 1));

// ── Fake Checkout Flow ─────────────────────────────────────────────────────────
const confirmPayBtn = document.getElementById('confirm-pay');
if (confirmPayBtn) {
  confirmPayBtn.addEventListener('click', () => {
    confirmPayBtn.disabled = true;
    confirmPayBtn.innerHTML = '<span>Processing...</span>';
    setTimeout(() => {
      showToast('Payment confirmed. Funds in escrow.', 'success');
      setTimeout(() => {
        window.location.href = '/order/ORD-004';
      }, 1200);
    }, 1800);
  });
}

// ── Admin: Approve / Reject ────────────────────────────────────────────────────
document.addEventListener('click', (e) => {
  if (e.target.closest('.approve-btn')) {
    const row = e.target.closest('tr');
    const name = row?.querySelector('td')?.textContent?.trim() || 'Agent';
    showToast(`${name} approved ✓`, 'success');
    e.target.closest('.approve-btn').closest('.action-group')?.querySelectorAll('button').forEach(b => b.disabled = true);
  }
  if (e.target.closest('.reject-btn')) {
    const row = e.target.closest('tr');
    const name = row?.querySelector('td')?.textContent?.trim() || 'Agent';
    showToast(`${name} rejected`, 'error');
  }
  if (e.target.closest('.release-btn')) {
    showToast('Payout released', 'success');
  }
  if (e.target.closest('.hold-btn')) {
    showToast('Payment held', 'warning');
  }
  if (e.target.closest('.refund-btn')) {
    showToast('Refund issued', 'info');
  }
});

// ── Search (client-side filter hint) ──────────────────────────────────────────
const searchInput = document.getElementById('marketplace-search');
if (searchInput) {
  let debounce;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      const form = searchInput.closest('form');
      if (form) form.submit();
    }, 500);
  });
}

// ── Surge badge tooltip ────────────────────────────────────────────────────────
document.querySelectorAll('.badge-surge').forEach(badge => {
  badge.title = 'Price adjusted due to peak demand';
});

// ── Order completion + rating ──────────────────────────────────────────────────
const markCompleteBtn = document.getElementById('mark-complete');
if (markCompleteBtn) {
  markCompleteBtn.addEventListener('click', () => {
    showToast('Task marked as complete. Payment will be released.', 'success');
    setTimeout(() => openModal('rating-modal'), 1500);
  });
}

// ── Submit rating ──────────────────────────────────────────────────────────────
const submitRatingBtn = document.getElementById('submit-rating');
if (submitRatingBtn) {
  submitRatingBtn.addEventListener('click', () => {
    const val = document.getElementById('rating-value')?.value || 0;
    if (!val || val === '0') { showToast('Please select a rating', 'warning'); return; }
    showToast(`Rating submitted: ${val}/5 ★`, 'success');
    closeModal('rating-modal');
  });
}

// ── Chart helpers (called from page scripts) ───────────────────────────────────
function makeLineChart(id, labels, datasets, options = {}) {
  const ctx = document.getElementById(id);
  if (!ctx || typeof Chart === 'undefined') return;
  return new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          labels: { color: '#94A3B8', font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: '#161F2C',
          borderColor: '#243041',
          borderWidth: 1,
          titleColor: '#F8FAFC',
          bodyColor: '#94A3B8',
          padding: 12,
        }
      },
      scales: {
        x: { grid: { color: 'rgba(36,48,65,.5)' }, ticks: { color: '#94A3B8', font: { size: 11 } } },
        y: { grid: { color: 'rgba(36,48,65,.5)' }, ticks: { color: '#94A3B8', font: { size: 11 } } },
        ...options.scales,
      },
      elements: { line: { tension: 0.4 }, point: { radius: 3, hoverRadius: 5 } },
      ...options,
    }
  });
}

function makeBarChart(id, labels, datasets, options = {}) {
  const ctx = document.getElementById(id);
  if (!ctx || typeof Chart === 'undefined') return;
  return new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94A3B8', font: { size: 12 } } },
        tooltip: {
          backgroundColor: '#161F2C',
          borderColor: '#243041',
          borderWidth: 1,
          titleColor: '#F8FAFC',
          bodyColor: '#94A3B8',
          padding: 12,
        }
      },
      scales: {
        x: { grid: { color: 'rgba(36,48,65,.5)' }, ticks: { color: '#94A3B8', font: { size: 11 } } },
        y: { grid: { color: 'rgba(36,48,65,.5)' }, ticks: { color: '#94A3B8', font: { size: 11 } } },
      },
      borderRadius: 4,
      ...options,
    }
  });
}

function makeDoughnutChart(id, labels, data, colors) {
  const ctx = document.getElementById(id);
  if (!ctx || typeof Chart === 'undefined') return;
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { color: '#94A3B8', font: { size: 12 }, padding: 16 } },
        tooltip: {
          backgroundColor: '#161F2C',
          borderColor: '#243041',
          borderWidth: 1,
          titleColor: '#F8FAFC',
          bodyColor: '#94A3B8',
          padding: 12,
        }
      },
      cutout: '65%',
    }
  });
}
