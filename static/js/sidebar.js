/**
 * Prados Pets — Manejo interactivo de Sidebar Responsive
 */
document.addEventListener('DOMContentLoaded', function() {
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  const closeBtn = document.getElementById('sidebar-close-btn');
  const backdrop = document.getElementById('sidebar-backdrop');
  const sidebar = document.getElementById('sidebar');

  function openSidebar() {
    document.body.classList.add('sidebar-is-open');
  }

  function closeSidebar() {
    document.body.classList.remove('sidebar-is-open');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      openSidebar();
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      closeSidebar();
    });
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }

  // Cerrar al presionar la tecla Escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeSidebar();
    }
  });

  // Cerrar menú al hacer clic en un enlace navegable en pantallas pequeñas
  if (sidebar) {
    const navItems = sidebar.querySelectorAll('a.sidebar__item');
    navItems.forEach(item => {
      item.addEventListener('click', function() {
        if (window.innerWidth <= 768) {
          closeSidebar();
        }
      });
    });
  }
});
