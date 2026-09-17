document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-offer-end]').forEach((el) => {
    const end = new Date(el.dataset.offerEnd).getTime();
    const units = {};
    el.querySelectorAll('.cd-box').forEach((box) => {
      units[box.dataset.unit] = box;
    });

    function pad(n) { return String(n).padStart(2, '0'); }
    const timer = setInterval(tick, 1000);
    function tick() {
      const now = Date.now();
      const diff = Math.max(0, Math.floor((end - now) / 1000));
      const d = Math.floor(diff / 86400);
      const h = Math.floor((diff % 86400) / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      if (units.d) units.d.textContent = pad(d);
      if (units.h) units.h.textContent = pad(h);
      if (units.m) units.m.textContent = pad(m);
      if (units.s) units.s.textContent = pad(s);
      if (diff <= 0) {
        clearInterval(timer);
        const block = el.closest('.offer-banner, .offer-section, .offer-tile') || el;
        block.remove();
      }
    }
    tick();
  });

  document.querySelectorAll('.qty-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const input = btn.parentElement.querySelector('.qty-input');
      if (!input) return;
      const step = parseInt(btn.dataset.qty, 10);
      let val = parseInt(input.value || '1', 10) + step;
      val = Math.max(parseInt(input.min || '1', 10), Math.min(parseInt(input.max || '99', 10), val));
      input.value = val;
    });
  });

  setTimeout(() => {
    document.querySelectorAll('.alert').forEach((a) => {
      a.style.transition = 'opacity .6s';
      a.style.opacity = '0';
      setTimeout(() => a.remove(), 600);
    });
  }, 5000);

  // Prevent duplicate submissions: disable submit buttons once a form is sent.
  document.querySelectorAll('form.js-checkout-form').forEach((form) => {
    form.addEventListener('submit', (e) => {
      if (form.dataset.submitting === '1') {
        e.preventDefault();
        e.stopImmediatePropagation();
        return false;
      }
      form.dataset.submitting = '1';
      form.querySelectorAll('button[data-disable-on-submit]').forEach((btn) => {
        btn.disabled = true;
        btn.dataset.originalLabel = btn.textContent;
        btn.textContent = 'Processing…';
      });
    });
  });
});