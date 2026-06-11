/**
 * Admin Analytics Dashboard — Chart.js initialisation.
 *
 * Data is injected by Django into <script type="application/json"> elements.
 * That type is NOT executed by the browser as JavaScript, so it is NOT
 * subject to CSP script-src. This file (a static asset) reads the text
 * content and parses it — no unsafe-inline required.
 */

(function () {
  'use strict';

  /* ── helpers ──────────────────────────────────────────────────────────── */

  function readJSON(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  var BRAND   = '#B23149';
  var BRAND20 = 'rgba(178,49,73,0.15)';
  var GRAY    = '#343534';
  var GREEN   = '#22c55e';
  var AMBER   = '#f59e0b';
  var BLUE    = '#3b82f6';
  var RED     = '#ef4444';

  var baseFont = {
    family: "'Inter', system-ui, sans-serif",
    size: 11,
  };

  /* ── Chart defaults ───────────────────────────────────────────────────── */

  Chart.defaults.font = baseFont;
  Chart.defaults.color = '#6b7280';
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
  Chart.defaults.plugins.legend.labels.padding  = 14;

  /* ── 1. Weekly Engagement ─────────────────────────────────────────────── */

  var engData = readJSON('data-engagement');
  if (engData) {
    var engCtx = document.getElementById('chart-engagement');
    if (engCtx) {
      new Chart(engCtx, {
        type: 'bar',
        data: {
          labels: engData.labels,
          datasets: [
            {
              label: 'Active students',
              data: engData.active,
              backgroundColor: BRAND,
              borderRadius: 4,
              order: 1,
            },
            {
              label: 'Total students',
              data: engData.total,
              backgroundColor: 'rgba(209,213,219,0.4)',
              borderRadius: 4,
              order: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true, ticks: { stepSize: 1 } },
          },
        },
      });
    }
  }

  /* ── 2. Weekly Reflection Rate ────────────────────────────────────────── */

  var reflData = readJSON('data-reflection');
  if (reflData) {
    var reflCtx = document.getElementById('chart-reflection');
    if (reflCtx) {
      new Chart(reflCtx, {
        type: 'line',
        data: {
          labels: reflData.labels,
          datasets: [
            {
              label: 'Submitted (%)',
              data: reflData.pct,
              borderColor: BRAND,
              backgroundColor: BRAND20,
              fill: true,
              tension: 0.35,
              pointBackgroundColor: BRAND,
              pointRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: {
            x: { grid: { display: false } },
            y: { min: 0, max: 100, ticks: { callback: function (v) { return v + '%'; } } },
          },
        },
      });
    }
  }

  /* ── 3. Goal Status Doughnut ──────────────────────────────────────────── */

  var goalData = readJSON('data-goal');
  if (goalData) {
    var goalCtx = document.getElementById('chart-goal');
    if (goalCtx) {
      new Chart(goalCtx, {
        type: 'doughnut',
        data: {
          labels: goalData.labels,
          datasets: [
            {
              data: goalData.data,
              backgroundColor: [GREEN, BLUE, AMBER, RED],
              borderWidth: 2,
              borderColor: '#fff',
              hoverOffset: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '65%',
          plugins: {
            legend: { position: 'bottom' },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                  var pct = total ? Math.round(ctx.parsed / total * 100) : 0;
                  return ' ' + ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                },
              },
            },
          },
        },
      });
    }
  }

  /* ── 4. Cohort Comparison ─────────────────────────────────────────────── */

  var cohortData = readJSON('data-cohort');
  if (cohortData && cohortData.labels.length > 0) {
    var cohortCtx = document.getElementById('chart-cohort');
    if (cohortCtx) {
      new Chart(cohortCtx, {
        type: 'bar',
        data: {
          labels: cohortData.labels,
          datasets: [
            {
              label: 'Reflection rate %',
              data: cohortData.reflection_rate,
              backgroundColor: BRAND,
              borderRadius: 4,
            },
            {
              label: 'Habit active %',
              data: cohortData.habit_rate,
              backgroundColor: BLUE,
              borderRadius: 4,
            },
            {
              label: 'Goal completion %',
              data: cohortData.goal_rate,
              backgroundColor: GREEN,
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: {
            x: { grid: { display: false } },
            y: { min: 0, max: 100, ticks: { callback: function (v) { return v + '%'; } } },
          },
        },
      });
    }
  }
}());
