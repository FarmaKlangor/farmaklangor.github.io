/* BioFarmLab Wiedza: first-party consent and analytics. No third-party tags before opt-in. */
(function () {
  'use strict';
  if (window.__bflKnowledgeConsentLoaded) return;
  window.__bflKnowledgeConsentLoaded = true;

  var KEY = 'bfl_analytics_consent';
  var MAX_AGE = 60 * 60 * 24 * 365;
  var GTM_ID = 'GTM-T99HRRTV';
  var CLARITY_ID = 'yjkcv3h47s';
  var started = false;
  var initialized = false;
  var panel = null;
  var trigger = null;
  var locale = (document.documentElement.lang || 'pl').split('-')[0].toLowerCase();
  var copy = {
    pl: {
      title: 'Prywatność i analityka',
      body: 'Za Twoją zgodą używamy Google Analytics i Microsoft Clarity, aby sprawdzać, które artykuły pomagają czytelnikom. Bez zgody nie uruchamiamy tych narzędzi.',
      yes: 'Zgadzam się',
      no: 'Odrzucam',
      settings: 'Ustawienia cookies'
    },
    en: {
      title: 'Privacy and analytics',
      body: 'With your permission, we use Google Analytics and Microsoft Clarity to understand which articles help readers. Without consent, these tools do not load.',
      yes: 'Accept',
      no: 'Decline',
      settings: 'Cookie settings'
    },
    de: {
      title: 'Datenschutz und Analyse',
      body: 'Mit deiner Einwilligung nutzen wir Google Analytics und Microsoft Clarity, um zu erfahren, welche Artikel hilfreich sind. Ohne Zustimmung laden diese Dienste nicht.',
      yes: 'Akzeptieren',
      no: 'Ablehnen',
      settings: 'Cookie-Einstellungen'
    },
    fr: {
      title: 'Confidentialité et statistiques',
      body: 'Avec votre accord, nous utilisons Google Analytics et Microsoft Clarity pour comprendre quels articles sont utiles. Sans accord, ces outils ne se chargent pas.',
      yes: 'Accepter',
      no: 'Refuser',
      settings: 'Paramètres des cookies'
    },
    it: {
      title: 'Privacy e analisi',
      body: 'Con il tuo consenso utilizziamo Google Analytics e Microsoft Clarity per capire quali articoli sono utili. Senza consenso questi strumenti non si caricano.',
      yes: 'Accetto',
      no: 'Rifiuto',
      settings: 'Impostazioni cookie'
    },
    es: {
      title: 'Privacidad y analítica',
      body: 'Con tu consentimiento usamos Google Analytics y Microsoft Clarity para saber qué artículos son útiles. Sin consentimiento, estas herramientas no se cargan.',
      yes: 'Aceptar',
      no: 'Rechazar',
      settings: 'Configuración de cookies'
    }
  };
  var t = copy[locale] || copy.pl;

  function getCookie() {
    try {
      var parts = document.cookie.split(';');
      for (var i = 0; i < parts.length; i++) {
        var s = parts[i].trim();
        if (s.indexOf(KEY + '=') === 0) {
          var v = decodeURIComponent(s.substring(KEY.length + 1));
          if (v === 'granted' || v === 'denied') return v;
        }
      }
    } catch (_) {}
    return null;
  }
  function getConsent() {
    var cookie = getCookie();
    if (cookie) return cookie;
    try {
      var v = window.localStorage.getItem(KEY);
      return v === 'granted' || v === 'denied' ? v : null;
    } catch (_) {
      return null;
    }
  }
  function saveConsent(v) {
    var domain = location.hostname === 'biofarmlab.pl' ||
      location.hostname.endsWith('.biofarmlab.pl') ?
      '; Domain=.biofarmlab.pl' : '';
    var secure = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = KEY + '=' + encodeURIComponent(v) + domain +
      '; Path=/; Max-Age=' + MAX_AGE + '; SameSite=Lax' + secure;
    try { window.localStorage.setItem(KEY, v); } catch (_) {}
  }
  function gtag() {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(arguments);
  }
  function initConsent() {
    if (initialized) return;
    initialized = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || gtag;
    window.gtag('consent', 'default', {
      analytics_storage: 'denied',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
  }
  function updateConsent(v) {
    initConsent();
    window.gtag('consent', 'update', {
      analytics_storage: v,
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
    if (started && typeof window.clarity === 'function') {
      window.clarity('consentv2', {
        ad_Storage: 'denied',
        analytics_Storage: v
      });
      if (v === 'denied') window.clarity('consent', false);
    }
  }
  function startTracking() {
    if (started) return;
    started = true;
    window.__bflKnowledgeTrackingStarted = true;
    window.clarity = window.clarity || function () {
      (window.clarity.q = window.clarity.q || []).push(arguments);
    };
    window.clarity('consentv2', { ad_Storage: 'denied', analytics_Storage: 'granted' });
    var gtm = document.createElement('script');
    gtm.async = true;
    gtm.src = 'https://www.googletagmanager.com/gtm.js?id=' + encodeURIComponent(GTM_ID);
    document.head.appendChild(gtm);
    var clarity = document.createElement('script');
    clarity.async = true;
    clarity.src = 'https://www.clarity.ms/tag/' + encodeURIComponent(CLARITY_ID);
    document.head.appendChild(clarity);
  }
  function hidePanel() {
    if (panel) panel.hidden = true;
  }
  function setConsent(v) {
    if (v !== 'granted' && v !== 'denied') return;
    saveConsent(v);
    updateConsent(v);
    if (v === 'granted') startTracking();
    hidePanel();
    if (v === 'denied' && started) {
      // Unload previously activated scripts immediately after withdrawing consent.
      location.reload();
    }
  }

  window.BioFarmLabConsent = {
    getAnalyticsConsent: getConsent,
    grantAnalytics: function () { setConsent('granted'); },
    denyAnalytics: function () { setConsent('denied'); },
    showSettings: function () { if (panel) panel.hidden = false; }
  };
  window.addEventListener('bfl:analytics-consent', function (e) {
    setConsent(e.detail && e.detail.granted ? 'granted' : 'denied');
  });

  initConsent();
  if (getConsent() === 'granted') {
    updateConsent('granted');
    startTracking();
  }

  function element(tag, text, cls) {
    var el = document.createElement(tag);
    if (text) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  }
  function makeUI() {
    var style = document.createElement('style');
    style.textContent =
      '.bfl-consent{position:fixed;z-index:2147483000;left:12px;right:12px;bottom:12px;' +
      'max-width:650px;margin:auto;padding:20px 22px;background:#f7f5ee;color:#20372d;' +
      'border:1px solid #ccd7c9;border-radius:12px;box-shadow:0 8px 36px #122d2040;' +
      'font:15px/1.5 system-ui,sans-serif;box-sizing:border-box}' +
      '.bfl-consent[hidden]{display:none!important}' +
      '.bfl-consent h2{font:600 19px/1.3 system-ui,sans-serif;margin:0 0 7px}' +
      '.bfl-consent p{font:14px/1.5 system-ui,sans-serif;margin:0 0 15px}' +
      '.bfl-consent-actions{display:flex;gap:12px;flex-wrap:wrap}' +
      '.bfl-consent button{cursor:pointer;min-width:125px;border:1px solid #214d37;' +
      'border-radius:6px;padding:10px 14px;font:600 14px system-ui,sans-serif}' +
      '.bfl-consent-yes{background:#214d37;color:#fff}' +
      '.bfl-consent-no{background:transparent;color:#214d37}' +
      '.bfl-consent-manage{border:none;background:transparent;cursor:pointer;' +
      'text-decoration:underline;color:inherit;padding:5px;font:13px system-ui,sans-serif}' +
      '@media(max-width:420px){.bfl-consent{padding:15px}.bfl-consent-actions button{flex:1}}';
    document.head.appendChild(style);

    panel = element('section', null, 'bfl-consent');
    panel.id = 'bfl-knowledge-consent';
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-label', t.title);
    var title = element('h2', t.title);
    var description = element('p', t.body);
    var actions = element('div', null, 'bfl-consent-actions');
    var no = element('button', t.no, 'bfl-consent-no');
    var yes = element('button', t.yes, 'bfl-consent-yes');
    no.type = yes.type = 'button';
    no.addEventListener('click', function () { setConsent('denied'); });
    yes.addEventListener('click', function () { setConsent('granted'); });
    actions.appendChild(no);
    actions.appendChild(yes);
    panel.appendChild(title);
    panel.appendChild(description);
    panel.appendChild(actions);
    panel.hidden = getConsent() !== null;
    document.body.appendChild(panel);

    trigger = element('button', t.settings, 'bfl-consent-manage');
    trigger.type = 'button';
    trigger.setAttribute('aria-controls', panel.id);
    trigger.addEventListener('click', function () {
      panel.hidden = false;
      no.focus();
    });
    var footer = document.querySelector('.footer-inner') || document.querySelector('footer') || document.body;
    footer.appendChild(trigger);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', makeUI);
  else makeUI();
})();
