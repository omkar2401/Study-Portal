document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!confirm(form.dataset.confirm || 'Are you sure?')) event.preventDefault();
    });
  });
  document.querySelectorAll('.flash').forEach(flash => {
    window.setTimeout(() => {
      flash.style.transition = 'opacity .3s ease, transform .3s ease';
      flash.style.opacity = '0';
      flash.style.transform = 'translateY(-5px)';
      window.setTimeout(() => flash.remove(), 350);
    }, 6000);
  });
});
