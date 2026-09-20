// Collegue AI - i18n (Internationalization)
// French is the default language; structure prepared for EN/AR

const i18n = {
  currentLang: 'fr',
  
  dictionaries: {
    fr: {
      // App
      app_name: 'Collegue AI',
      
      // Navigation
      nav_home: 'Accueil',
      nav_modules: 'Modules',
      nav_toolkit: 'Boîte à outils',
      nav_chat: 'Chat',
      nav_profile: 'Profil',
      
      // Home View
      greeting: 'Bonjour,',
      role: 'Enseignant d\'informatique',
      search_placeholder: 'Rechercher une ressource, un conseil, ou demander à l\'IA...',
      search_button: 'Rechercher',
      
      // Modules Section
      explore_modules: 'Explorer les modules',
      module_planification_annuelle: 'Planification annuelle',
      module_planification_unite: 'Planification d\'unité',
      module_preparation_sequence: 'Préparation de séquence',
      module_calendrier: 'Calendrier',
      module_assistant_ia: 'Assistant IA',
      module_ressources: 'Ressources',
      
      // Recent Activity
      recent_activity: 'Activité récente',
      view_all: 'Tout voir',
      
      // Toast messages
      toast_module_bientot: 'Module disponible dans la version bureau (Streamlit) pour l\'instant',
      
      // Placeholder
      placeholder_title: 'Bientôt disponible',
      placeholder_text: 'Cette fonctionnalité sera ajoutée prochainement.',
      
      // Time formatting
      time_ago_hours: 'il y a {0} h',
      time_ago_days: 'il y a {0} j',
      time_ago_today: "aujourd'hui"
    },
    
    en: {
      app_name: 'Collegue AI',
      nav_home: 'Home',
      nav_modules: 'Modules',
      nav_toolkit: 'Toolkit',
      nav_chat: 'Chat',
      nav_profile: 'Profile',
      greeting: 'Hello,',
      role: 'ICT Teacher',
      search_placeholder: 'Search for resources, tips, or ask AI...'
    },
    
    ar: {
      app_name: 'كوليج أي آي',
      nav_home: 'الرئيسية',
      nav_modules: 'الوحدات',
      nav_toolkit: 'مجموعة الأدوات',
      nav_chat: 'الدردشة',
      nav_profile: 'الملف الشخصي'
    }
  },
  
  t(key, ...args) {
    const dict = this.dictionaries[this.currentLang] || this.dictionaries.fr;
    let value = dict[key] || key;
    
    // Simple interpolation: {0}, {1}, etc.
    args.forEach((arg, index) => {
      value = value.replace(new RegExp(`\\{${index}\\}`, 'g'), arg);
    });
    
    return value;
  },
  
  setLang(lang) {
    if (this.dictionaries[lang]) {
      this.currentLang = lang;
      document.documentElement.lang = lang;
      
      // Handle RTL for Arabic
      if (lang === 'ar') {
        document.documentElement.setAttribute('dir', 'rtl');
      } else {
        document.documentElement.removeAttribute('dir');
      }
    }
  },
  
  init() {
    // Set default to French
    this.setLang('fr');
  }
};

// Initialize on load
i18n.init();
