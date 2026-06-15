/**
 * Collect privacy-conscious client context for bug reports.
 * No full user-agent string, geolocation, or extension lists.
 */
(function () {
  const FIELD_LABELS = {
    browser: 'Browser',
    os: 'OS',
    viewport: 'Viewport',
    screen: 'Screen',
    pixel_ratio: 'Pixel ratio',
    color_scheme: 'Color scheme',
    timezone: 'Timezone',
    language: 'Language',
    touch: 'Touch',
    connection: 'Connection',
  };

  const TECH_FIELD_ORDER = [
    'browser',
    'os',
    'viewport',
    'screen',
    'pixel_ratio',
    'color_scheme',
    'timezone',
    'language',
    'touch',
    'connection',
  ];

  function browserLabel() {
    const ua = navigator.userAgent;
    if (ua.includes('Firefox/')) {
      const match = ua.match(/Firefox\/(\d+)/);
      return 'Firefox ' + (match ? match[1] : '');
    }
    if (ua.includes('Edg/')) {
      const match = ua.match(/Edg\/(\d+)/);
      return 'Edge ' + (match ? match[1] : '');
    }
    if (ua.includes('Chrome/')) {
      const match = ua.match(/Chrome\/(\d+)/);
      return 'Chrome ' + (match ? match[1] : '');
    }
    if (ua.includes('Safari/') && ua.includes('Version/')) {
      const match = ua.match(/Version\/(\d+)/);
      return 'Safari ' + (match ? match[1] : '');
    }
    return 'Other';
  }

  function osLabel() {
    const ua = navigator.userAgent;
    const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || '';
    if (/Win/i.test(platform) || ua.includes('Windows')) return 'Windows';
    if (/Mac/i.test(platform) || ua.includes('Macintosh')) return 'macOS';
    if (/Linux/i.test(platform) || (ua.includes('Linux') && !ua.includes('Android'))) return 'Linux';
    if (ua.includes('Android')) return 'Android';
    if (/iPhone|iPad|iPod/i.test(ua)) return 'iOS';
    return platform.slice(0, 32) || 'Unknown';
  }

  function dimensions(width, height) {
    const w = Math.round(Number(width));
    const h = Math.round(Number(height));
    if (!w || !h || w > 99999 || h > 99999) return '';
    return w + '\u00d7' + h;
  }

  function formatValue(key, value) {
    if (key === 'touch') return value ? 'Yes' : 'No';
    if (key === 'pixel_ratio') return Number(value).toFixed(1);
    return String(value);
  }

  function siteColorScheme() {
    return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  }

  window.collectBugReportContext = function collectBugReportContext() {
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    const payload = {
      browser: browserLabel(),
      os: osLabel(),
      viewport: dimensions(window.innerWidth, window.innerHeight),
      screen: dimensions(screen.width, screen.height),
      pixel_ratio: window.devicePixelRatio || 1,
      color_scheme: siteColorScheme(),
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
      language: (navigator.language || '').slice(0, 16),
      touch: navigator.maxTouchPoints > 0,
    };
    if (connection && connection.effectiveType) {
      payload.connection = connection.effectiveType;
    }
    return payload;
  };

  function appendRow(list, key, value) {
    if (value === '' || value == null) return;
    const row = document.createElement('div');
    row.className = 'flex gap-2';
    const dt = document.createElement('dt');
    dt.className = 'text-gray-500 shrink-0';
    dt.textContent = FIELD_LABELS[key] + ':';
    const dd = document.createElement('dd');
    dd.className = 'text-gray-700 dark:text-gray-300';
    dd.textContent = value;
    row.appendChild(dt);
    row.appendChild(dd);
    list.appendChild(row);
  }

  function renderSharePreview(context) {
    const list = document.getElementById('bug-report-share-list');
    if (!list) return;
    list.innerHTML = '';
    TECH_FIELD_ORDER.forEach(function (key) {
      if (!(key in context)) return;
      appendRow(list, key, formatValue(key, context[key]));
    });
  }

  function refreshBugReportContext() {
    const input = document.getElementById('bug-report-client-context');
    if (!input) return;
    try {
      const context = window.collectBugReportContext();
      input.value = JSON.stringify(context);
      renderSharePreview(context);
    } catch (err) {
      input.value = '';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', refreshBugReportContext);
  } else {
    refreshBugReportContext();
  }

  document.addEventListener('powerhub-theme-change', refreshBugReportContext);
})();
