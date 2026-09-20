// Collegue AI - Main App Logic

(function() {
  'use strict';

  // API Base URL (relative to current origin)
  const API_BASE = '/api';

  // Router state
  let currentRoute = '#/accueil';

  // SVG Icons
  const icons = {
    home: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>',
    modules: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>',
    chat: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>',
    profile: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>',
    bell: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>',
    send: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>',
    calendar: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>',
    document: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>',
    grid: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" /></svg>',
    sparkles: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" /></svg>',
    book: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>',
    plus: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>'
  };

  // Module definitions with icon colors
  const modules = [
    { id: 'planification_annuelle', label: i18n.t('module_planification_annuelle'), icon: icons.calendar, colorClass: 'blue' },
    { id: 'planification_unite', label: i18n.t('module_planification_unite'), icon: icons.document, colorClass: 'green' },
    { id: 'preparation_sequence', label: i18n.t('module_preparation_sequence'), icon: icons.grid, colorClass: 'purple' },
    { id: 'calendrier', label: i18n.t('module_calendrier'), icon: icons.calendar, colorClass: 'amber' },
    { id: 'assistant_ia', label: i18n.t('module_assistant_ia'), icon: icons.sparkles, colorClass: 'blue', route: '#/chat' },
    { id: 'ressources', label: i18n.t('module_ressources'), icon: icons.book, colorClass: 'green' }
  ];

  // Format time ago
  function timeAgo(isoString) {
    if (!isoString) return '';
    const saved = new Date(isoString);
    const now = new Date();
    const diffMs = now - saved;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffHours < 24) {
      return i18n.t('time_ago_hours', diffHours);
    } else if (diffDays < 7) {
      return i18n.t('time_ago_days', diffDays);
    } else {
      return saved.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
    }
  }

  // Get plan type label
  function getPlanTypeLabel(type) {
    const labels = {
      'annual': 'Planification annuelle',
      'unit': 'Planification d\'unité',
      'sequence': 'Préparation de séquence'
    };
    return labels[type] || type;
  }

  // Build plan title
  function buildPlanTitle(plan) {
    if (plan.type === 'annual') {
      return `${getPlanTypeLabel(plan.type)} — ${plan.level}`;
    } else if (plan.type === 'unit') {
      return `${getPlanTypeLabel(plan.type)} — ${plan.level} — ${plan.unit}`;
    } else {
      return `${getPlanTypeLabel(plan.type)} — ${plan.title || plan.unit}`;
    }
  }

  // Show toast notification
  function showToast(message) {
    const toast = document.getElementById('toast');
    if (toast) {
      toast.textContent = message;
      toast.classList.add('visible');
      setTimeout(() => toast.classList.remove('visible'), 2500);
    }
  }

  // Fetch recent plans from API
  async function fetchRecentPlans() {
    try {
      const response = await fetch(`${API_BASE}/plans/recent`);
      if (response.ok) {
        return await response.json();
      }
    } catch (e) {
      console.error('Error fetching recent plans:', e);
    }
    return [];
  }

  // Render Home View
  async function renderHome() {
    const container = document.getElementById('view-content');
    if (!container) return;

    // Fetch recent plans
    const recentPlans = await fetchRecentPlans();

    container.innerHTML = `
      <div class="greeting-section card">
        <div class="greeting-line">${i18n.t('greeting')}</div>
        <div class="greeting-bold">${i18n.t('role')}</div>
      </div>

      <div class="search-container">
        <form class="search-form" onsubmit="app.handleSearch(event)">
          <input type="text" class="search-input" placeholder="${i18n.t('search_placeholder')}" name="q" />
          <button type="submit" class="search-button">${icons.send}</button>
        </form>
      </div>

      <div class="card">
        <h2 class="card-title">${i18n.t('explore_modules')}</h2>
        <div class="modules-grid">
          ${modules.map(m => `
            <div class="module-tile" data-module="${m.id}" onclick="app.handleModuleClick('${m.id}', '${m.route || ''}')">
              <div class="tile-icon ${m.colorClass}">${m.icon}</div>
              <div class="tile-label">${m.label}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="recent-section card">
        <div class="section-header">
          <h2 class="section-title">${i18n.t('recent_activity')}</h2>
          <a href="#/plans" class="view-all-link">${i18n.t('view_all')}</a>
        </div>
        <ul class="recent-list">
          ${recentPlans.length > 0 
            ? recentPlans.map(p => `
                <li class="recent-item">
                  <div class="recent-icon ${p.type === 'annual' ? 'blue' : p.type === 'unit' ? 'green' : 'purple'}">
                    ${p.type === 'annual' ? icons.calendar : p.type === 'unit' ? icons.document : icons.grid}
                  </div>
                  <div class="recent-content">
                    <div class="recent-title">${buildPlanTitle(p)}</div>
                    <div class="recent-time">${timeAgo(p.saved_at)}</div>
                  </div>
                </li>
              `).join('')
            : `<li class="recent-item"><div class="recent-content"><div class="recent-title">Aucune activité récente</div></div></li>`
          }
        </ul>
      </div>
    `;

    updateActiveNav('#/accueil');
  }

  // Render Placeholder View
  function renderPlaceholder() {
    const container = document.getElementById('view-content');
    if (!container) return;

    container.innerHTML = `
      <div class="card placeholder-card">
        <div class="placeholder-icon">${icons.modules}</div>
        <div class="placeholder-title">${i18n.t('placeholder_title')}</div>
        <div class="placeholder-text">${i18n.t('placeholder_text')}</div>
      </div>
    `;
  }

  // Update active navigation state
  function updateActiveNav(route) {
    // Bottom nav
    document.querySelectorAll('.bottom-nav .nav-item').forEach(item => {
      item.classList.remove('active');
      if (item.getAttribute('href') === route) {
        item.classList.add('active');
      }
    });

    // Left rail (desktop)
    document.querySelectorAll('.left-rail .rail-item').forEach(item => {
      item.classList.remove('active');
      if (item.getAttribute('href') === route) {
        item.classList.add('active');
      }
    });
  }

  // Handle module click
  function handleModuleClick(moduleId, route) {
    if (route) {
      window.location.hash = route;
    } else {
      showToast(i18n.t('toast_module_bientot'));
    }
  }

  // Handle search submit
  function handleSearch(event) {
    event.preventDefault();
    const form = event.target;
    const query = form.q.value.trim();
    if (query) {
      window.location.hash = `#/chat?q=${encodeURIComponent(query)}`;
    }
  }

  // Router
  function router() {
    const hash = window.location.hash || '#/accueil';
    currentRoute = hash;

    switch (hash.split('?')[0]) {
      case '#/accueil':
        renderHome();
        break;
      case '#/modules':
        renderPlaceholder();
        updateActiveNav('#/modules');
        break;
      case '#/chat':
        renderPlaceholder();
        updateActiveNav('#/chat');
        break;
      case '#/profil':
        renderPlaceholder();
        updateActiveNav('#/profil');
        break;
      default:
        renderHome();
    }
  }

  // Expose app functions globally
  window.app = {
    handleModuleClick,
    handleSearch
  };

  // Initialize app
  function init() {
    // Listen for hash changes
    window.addEventListener('hashchange', router);
    
    // Initial render
    router();

    // Register service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/pwa/sw.js')
        .then(reg => console.log('SW registered:', reg.scope))
        .catch(err => console.error('SW registration failed:', err));
    }
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
