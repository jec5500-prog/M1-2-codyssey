// frontend/app.js
(() => {
  'use strict';

  // ------------------------------------------------------------------ 설정
  const cfg = window.APP_CONFIG || {};
  const API_BASE = String(cfg.API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
  const COLD_START_DELAY_MS = 2500;
  const DEFAULT_TIMEOUT_MS = 90000;
  const CHAT_TIMEOUT_MS = 120000;

  const TOOL_LABELS = {
    query_data_points: '데이터 조회',
    get_data_summary: '요약 조회',
    get_extreme_points: '최고/최저 조회',
  };

  const state = {
    conversationId: null,
    conversations: [],
    data: [],
    summary: null,
    editingId: null,
    chart: null,
    sending: false,
    loadingConversation: false,
    deletingConversation: false,
    conversationLoadToken: 0,
  };

  // ------------------------------------------------------------------ DOM 헬퍼
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const el = {
    sidebar: $('#sidebar'),
    backdrop: $('#backdrop'),
    menuBtn: $('#menuBtn'),
    newChatBtn: $('#newChatBtn'),
    convList: $('#convList'),
    topbarTitle: $('#topbarTitle'),
    themeToggle: $('#themeToggle'),
    coldBanner: $('#coldBanner'),
    chatScroll: $('#chatScroll'),
    messages: $('#messages'),
    welcome: $('#welcome'),
    chatInput: $('#chatInput'),
    sendBtn: $('#sendBtn'),
    saveStatus: $('#saveStatus'),
    summaryPanel: $('#summaryPanel'),
    refreshBtn: $('#refreshBtn'),
    chartCanvas: $('#dataChart'),
    chartEmpty: $('#chartEmpty'),
    form: $('#dataForm'),
    formTitle: $('#formTitle'),
    fDate: $('#fDate'),
    fValue: $('#fValue'),
    fMemo: $('#fMemo'),
    submitBtn: $('#submitBtn'),
    cancelEditBtn: $('#cancelEditBtn'),
    csvBtn: $('#csvBtn'),
    dataBody: $('#dataBody'),
    dataCount: $('#dataCount'),
    tableEmpty: $('#tableEmpty'),
    toasts: $('#toastContainer'),
  };

  // ------------------------------------------------------------------ 유틸
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function escapeHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtNum(v) {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return '-';
    return Number(v).toLocaleString('ko-KR', { maximumFractionDigits: 2 });
  }

  function todayStr() {
    return new Date().toLocaleDateString('sv-SE'); // YYYY-MM-DD (로컬 시간대)
  }

  function fmtDateTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function toast(message, type = 'info', ms = 4200) {
    const div = document.createElement('div');
    div.className = `toast ${type}`;
    div.textContent = message;
    el.toasts.appendChild(div);
    setTimeout(() => div.remove(), ms);
  }

  // 아주 가벼운 마크다운 렌더러 (HTML 이스케이프 후 코드블록/목록/굵게/인라인코드만 지원)
  function inlineMd(text) {
    return text
      .replace(/`([^`\n]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  }

  function renderMarkdown(text) {
    const blocks = [];
    let src = escapeHtml(text).replace(/```([\s\S]*?)```/g, (_, code) => {
      blocks.push(`<pre><code>${code.replace(/^[\w-]*\n/, '')}</code></pre>`);
      return `@@BLOCK${blocks.length - 1}@@`;
    });

    let html = '';
    let inList = false;
    for (const line of src.split('\n')) {
      const m = line.match(/^\s*[-*•]\s+(.*)$/);
      if (m) {
        if (!inList) { html += '<ul>'; inList = true; }
        html += `<li>${inlineMd(m[1])}</li>`;
      } else {
        if (inList) { html += '</ul>'; inList = false; }
        if (line.trim() !== '') html += `<p>${inlineMd(line)}</p>`;
      }
    }
    if (inList) html += '</ul>';
    return html.replace(/@@BLOCK(\d+)@@/g, (_, i) => blocks[Number(i)]);
  }

  // ------------------------------------------------------------------ API 통신 (콜드스타트 대응)
  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  }

  let pending = 0;
  let coldTimer = null;

  function beginRequest() {
    pending += 1;
    if (pending === 1) {
      coldTimer = setTimeout(() => el.coldBanner.classList.remove('hidden'), COLD_START_DELAY_MS);
    }
  }

  function endRequest() {
    pending = Math.max(0, pending - 1);
    if (pending === 0) {
      clearTimeout(coldTimer);
      coldTimer = null;
      el.coldBanner.classList.add('hidden');
    }
  }

  async function extractError(res) {
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') return j.detail;
      if (Array.isArray(j.detail)) {
        return j.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
      }
      return JSON.stringify(j);
    } catch (_) {
      return res.statusText || `HTTP ${res.status}`;
    }
  }

  async function api(path, opts = {}) {
    const {
      method = 'GET',
      body,
      raw = false,
      timeout = DEFAULT_TIMEOUT_MS,
      retries = method === 'GET' ? 2 : 0,
    } = opts;

    beginRequest();
    try {
      let attempt = 0;
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout);
        try {
          const res = await fetch(API_BASE + path, {
            method,
            headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
            body: body !== undefined ? JSON.stringify(body) : undefined,
            signal: controller.signal,
          });
          clearTimeout(timer);

          if (!res.ok) {
            if ([502, 503, 504].includes(res.status) && attempt < retries) {
              attempt += 1;
              await sleep(3000);
              continue;
            }
            throw new ApiError(await extractError(res), res.status);
          }
          if (raw) return res;
          if (res.status === 204) return null;
          return await res.json();
        } catch (err) {
          clearTimeout(timer);
          if (err instanceof ApiError) throw err;
          if (attempt < retries) {
            attempt += 1;
            await sleep(3000);
            continue;
          }
          if (err.name === 'AbortError') {
            throw new Error('요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.');
          }
          throw new Error('서버에 연결할 수 없습니다. 네트워크 상태와 API 주소, CORS 설정을 확인해 주세요.');
        }
      }
    } finally {
      endRequest();
    }
  }

  // ------------------------------------------------------------------ 테마
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (_) { /* ignore */ }
    el.themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
    updateChartTheme();
  }

  function toggleTheme() {
    const cur = document.documentElement.getAttribute('data-theme');
    applyTheme(cur === 'dark' ? 'light' : 'dark');
  }

  // ------------------------------------------------------------------ 레이아웃 (모바일)
  function openSidebar(open) {
    el.sidebar.classList.toggle('open', open);
    el.backdrop.classList.toggle('show', open);
  }

  function switchPane(targetId) {
    $$('.pane').forEach((p) => p.classList.toggle('active', p.id === targetId));
    $$('.tab').forEach((t) => t.classList.toggle('active', t.dataset.target === targetId));
    if (targetId === 'dataPane' && state.chart) state.chart.resize();
  }

  // ------------------------------------------------------------------ 채팅 UI
  function scrollChatToBottom() {
    el.chatScroll.scrollTop = el.chatScroll.scrollHeight;
  }

  function clearMessages() {
    el.messages.innerHTML = '';
  }

  function showWelcome() {
    clearMessages();
    el.messages.appendChild(el.welcome);
  }

  function appendMessage(role, content, tools = [], isError = false) {
    if (el.welcome.parentNode) el.welcome.remove();

    const wrap = document.createElement('div');
    wrap.className = `msg ${role}${isError ? ' error' : ''}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    if (role === 'assistant' && !isError) bubble.innerHTML = renderMarkdown(content);
    else bubble.textContent = content;
    wrap.appendChild(bubble);

    if (tools && tools.length) {
      const badge = document.createElement('div');
      badge.className = 'tool-badge';
      badge.textContent = '🔧 ' + tools.map((t) => TOOL_LABELS[t] || t).join(', ') + ' 도구 사용';
      wrap.appendChild(badge);
    }

    el.messages.appendChild(wrap);
    scrollChatToBottom();
    return wrap;
  }

  function appendTyping() {
    if (el.welcome.parentNode) el.welcome.remove();
    const wrap = document.createElement('div');
    wrap.className = 'msg assistant';
    wrap.innerHTML = '<div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div>';
    el.messages.appendChild(wrap);
    scrollChatToBottom();
    return wrap;
  }

  function setSending(v) {
    state.sending = v;
    updateComposerState();
    el.sendBtn.textContent = v ? '…' : '전송';
    if (!v) el.chatInput.focus();
  }

  function updateComposerState() {
    const busy = state.sending || state.loadingConversation || state.deletingConversation;
    el.sendBtn.disabled = busy;
    el.chatInput.disabled = busy;
    el.newChatBtn.disabled = state.sending || state.deletingConversation;
  }

  function autosizeInput() {
    el.chatInput.style.height = 'auto';
    el.chatInput.style.height = Math.min(el.chatInput.scrollHeight, 160) + 'px';
  }

  async function sendMessage(text) {
    const message = (text ?? el.chatInput.value).trim();
    if (!message || state.sending || state.loadingConversation || state.deletingConversation) return;

    el.chatInput.value = '';
    autosizeInput();
    appendMessage('user', message);
    setSending(true);
    const typing = appendTyping();
    el.saveStatus.textContent = '답변을 만들고 있습니다…';

    try {
      const res = await api('/api/chat', {
        method: 'POST',
        body: { message, conversation_id: state.conversationId },
        timeout: CHAT_TIMEOUT_MS,
      });
      typing.remove();
      appendMessage('assistant', res.reply, res.tool_calls_used || []);
      el.saveStatus.textContent = '대화가 자동 저장되었습니다.';

      const isNew = state.conversationId !== res.conversation_id;
      state.conversationId = res.conversation_id;
      if (isNew) el.topbarTitle.textContent = message.length > 30 ? message.slice(0, 30) + '…' : message;
      await loadConversations();
    } catch (err) {
      typing.remove();
      appendMessage('assistant', `⚠️ ${err.message}`, [], true);
      toast(err.message, 'error');
      el.saveStatus.textContent = '답변을 저장하지 못했습니다. 오류를 확인해 주세요.';
    } finally {
      setSending(false);
    }
  }

  // ------------------------------------------------------------------ 대화 목록
  function renderConversations() {
    el.convList.innerHTML = '';
    if (!state.conversations.length) {
      el.convList.innerHTML = '<div class="conv-empty">아직 대화가 없어요.</div>';
      return;
    }
    for (const c of state.conversations) {
      const item = document.createElement('div');
      item.className = 'conv-item' + (c.id === state.conversationId ? ' active' : '');
      item.setAttribute('role', 'listitem');
      item.dataset.id = c.id;
      item.innerHTML = `
        <div class="conv-main">
          <div class="conv-title">${escapeHtml(c.title)}</div>
          <div class="conv-time">${escapeHtml(fmtDateTime(c.updated_at))} · ${c.message_count}개</div>
        </div>
        <button class="icon-btn conv-del" data-action="delete" title="삭제" aria-label="대화 삭제">🗑️</button>`;
      el.convList.appendChild(item);
    }
  }

  async function loadConversations() {
    try {
      state.conversations = await api('/api/conversations');
      renderConversations();
    } catch (err) {
      toast(`대화 목록을 불러오지 못했습니다: ${err.message}`, 'error');
    }
  }

  async function openConversation(id) {
    if (state.sending || state.deletingConversation) return;
    const token = ++state.conversationLoadToken;
    state.loadingConversation = true;
    updateComposerState();
    try {
      const conv = await api(`/api/conversations/${encodeURIComponent(id)}`);
      if (token !== state.conversationLoadToken) return;
      state.conversationId = conv.id;
      el.topbarTitle.textContent = conv.title;
      clearMessages();
      if (!conv.messages.length) showWelcome();
      for (const m of conv.messages) appendMessage(m.role, m.content, m.tools_used || []);
      el.saveStatus.textContent = '저장된 대화를 불러왔습니다.';
      renderConversations();
      switchPane('chatPane');
      openSidebar(false);
    } catch (err) {
      if (token === state.conversationLoadToken) toast(`대화를 불러오지 못했습니다: ${err.message}`, 'error');
    } finally {
      if (token === state.conversationLoadToken) {
        state.loadingConversation = false;
        updateComposerState();
      }
    }
  }

  async function deleteConversation(id) {
    if (state.sending || state.loadingConversation || state.deletingConversation) {
      return toast('진행 중인 요청이 끝난 뒤 대화를 삭제해 주세요.');
    }
    if (!confirm('이 대화를 삭제할까요?')) return;
    state.deletingConversation = true;
    updateComposerState();
    try {
      await api(`/api/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
      state.deletingConversation = false;
      if (state.conversationId === id) newChat();
      await loadConversations();
      toast('대화를 삭제했습니다.', 'success');
    } catch (err) {
      toast(`삭제 실패: ${err.message}`, 'error');
    } finally {
      state.deletingConversation = false;
      updateComposerState();
    }
  }

  function newChat() {
    if (state.sending || state.deletingConversation) return;
    ++state.conversationLoadToken;
    state.loadingConversation = false;
    updateComposerState();
    state.conversationId = null;
    el.topbarTitle.textContent = '새 대화';
    el.saveStatus.textContent = '답변을 받으면 대화가 자동 저장됩니다.';
    showWelcome();
    renderConversations();
    switchPane('chatPane');
    openSidebar(false);
    el.chatInput.focus();
  }

  // ------------------------------------------------------------------ 데이터 요약 / 목록 / 차트
  function renderSummary() {
    const s = state.summary;
    if (!s || !s.count) {
      el.summaryPanel.innerHTML =
        '<div class="stat wide"><div class="stat-label">데이터 없음</div><div class="stat-sub">아래 폼에서 첫 데이터를 추가해 보세요.</div></div>';
      return;
    }
    const t = s.trend || {};
    const arrow = t.direction === 'up' ? '↗' : t.direction === 'down' ? '↘' : t.direction === 'flat' ? '→' : '•';
    const cls = t.direction === 'up' ? 'trend-up' : t.direction === 'down' ? 'trend-down' : '';
    const pct = t.change_percent !== null && t.change_percent !== undefined
      ? ` (${t.change_percent > 0 ? '+' : ''}${fmtNum(t.change_percent)}%)` : '';

    el.summaryPanel.innerHTML = `
      <div class="stat"><div class="stat-label">데이터 건수</div><div class="stat-value">${fmtNum(s.count)}</div><div class="stat-sub">${escapeHtml(s.first_date || '')} ~ ${escapeHtml(s.last_date || '')}</div></div>
      <div class="stat"><div class="stat-label">평균</div><div class="stat-value">${fmtNum(s.average)}</div><div class="stat-sub">합계 ${fmtNum(s.total)}</div></div>
      <div class="stat"><div class="stat-label">최소</div><div class="stat-value">${fmtNum(s.minimum?.value)}</div><div class="stat-sub">${escapeHtml(s.minimum?.date || '')}</div></div>
      <div class="stat"><div class="stat-label">최대</div><div class="stat-value">${fmtNum(s.maximum?.value)}</div><div class="stat-sub">${escapeHtml(s.maximum?.date || '')}</div></div>
      <div class="stat"><div class="stat-label">최근 값</div><div class="stat-value">${fmtNum(s.latest?.value)}</div><div class="stat-sub">${escapeHtml(s.latest?.date || '')}</div></div>
      <div class="stat"><div class="stat-label">최근 추세</div><div class="stat-value ${cls}">${arrow} ${escapeHtml(t.label || '-')}</div><div class="stat-sub">최근 ${t.window || 0}건${escapeHtml(pct)}</div></div>`;
  }

  function renderTable() {
    const rows = [...state.data].sort((a, b) => b.date.localeCompare(a.date));
    el.dataCount.textContent = rows.length ? (state.summary?.count > rows.length ? `(최근 ${rows.length}건 / 전체 ${state.summary.count}건)` : `(${rows.length}건)`) : '';
    el.tableEmpty.classList.toggle('hidden', rows.length > 0);
    el.dataBody.innerHTML = rows
      .map(
        (p) => `
      <tr>
        <td>${escapeHtml(p.date)}</td>
        <td class="num">${fmtNum(p.value)}</td>
        <td class="memo" title="${escapeHtml(p.memo)}">${escapeHtml(p.memo)}</td>
        <td class="actions">
          <button class="icon-btn" data-action="edit" data-id="${escapeHtml(p.id)}" title="수정" aria-label="수정">✏️</button>
          <button class="icon-btn" data-action="delete" data-id="${escapeHtml(p.id)}" title="삭제" aria-label="삭제">🗑️</button>
        </td>
      </tr>`
      )
      .join('');
  }

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function chartColors() {
    return { text: cssVar('--text-muted'), grid: cssVar('--border'), line: cssVar('--primary') };
  }

  function updateChartTheme() {
    if (!state.chart) return;
    const c = chartColors();
    const opts = state.chart.options;
    opts.scales.x.ticks.color = c.text;
    opts.scales.y.ticks.color = c.text;
    opts.scales.x.grid.color = c.grid;
    opts.scales.y.grid.color = c.grid;
    const ds = state.chart.data.datasets[0];
    ds.borderColor = c.line;
    ds.pointBackgroundColor = c.line;
    ds.backgroundColor = hexToRgba(c.line, 0.15);
    state.chart.update('none');
  }

  function hexToRgba(hex, alpha) {
    const h = hex.replace('#', '');
    if (h.length !== 6) return hex;
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function renderChart() {
    const sorted = [...state.data].sort((a, b) => a.date.localeCompare(b.date));
    el.chartEmpty.classList.toggle('hidden', sorted.length > 0);

    if (typeof Chart === 'undefined') {
      el.chartEmpty.textContent = '차트 라이브러리를 불러오지 못했습니다.';
      el.chartEmpty.classList.remove('hidden');
      return;
    }

    const labels = sorted.map((p) => p.date);
    const values = sorted.map((p) => p.value);
    const memos = sorted.map((p) => p.memo);

    if (state.chart) {
      state.chart.data.labels = labels;
      state.chart.data.datasets[0].data = values;
      state.chart.$memos = memos;
      state.chart.update();
      return;
    }

    const c = chartColors();
    state.chart = new Chart(el.chartCanvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '값',
            data: values,
            borderColor: c.line,
            backgroundColor: hexToRgba(c.line, 0.15),
            pointBackgroundColor: c.line,
            pointRadius: 3,
            pointHoverRadius: 5,
            tension: 0.3,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: (item) => {
                const memo = state.chart.$memos?.[item.dataIndex];
                return memo ? `메모: ${memo}` : '';
              },
            },
          },
        },
        scales: {
          x: { ticks: { color: c.text, maxRotation: 0, autoSkip: true }, grid: { color: c.grid } },
          y: { ticks: { color: c.text }, grid: { color: c.grid } },
        },
      },
    });
    state.chart.$memos = memos;
  }

  async function loadData() {
    try {
      const [points, summary] = await Promise.all([
        api('/api/data?limit=2000&order=desc'),
        api('/api/data/summary'),
      ]);
      state.data = points;
      state.summary = summary;
      renderSummary();
      renderTable();
      renderChart();
    } catch (err) {
      toast(`데이터를 불러오지 못했습니다: ${err.message}`, 'error');
    }
  }

  // ------------------------------------------------------------------ 데이터 CRUD
  function resetForm() {
    state.editingId = null;
    el.form.reset();
    el.fDate.value = todayStr();
    el.formTitle.textContent = '데이터 추가';
    el.submitBtn.textContent = '추가';
    el.cancelEditBtn.classList.add('hidden');
  }

  function startEdit(id) {
    const p = state.data.find((x) => x.id === id);
    if (!p) return;
    state.editingId = id;
    el.fDate.value = p.date;
    el.fValue.value = p.value;
    el.fMemo.value = p.memo || '';
    el.formTitle.textContent = '데이터 수정';
    el.submitBtn.textContent = '수정 저장';
    el.cancelEditBtn.classList.remove('hidden');
    el.form.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.fValue.focus();
  }

  async function submitForm(e) {
    e.preventDefault();
    const date = el.fDate.value;
    const value = parseFloat(el.fValue.value);
    const memo = el.fMemo.value.trim();

    if (!date) return toast('날짜를 입력해 주세요.', 'error');
    if (!Number.isFinite(value)) return toast('값은 숫자로 입력해 주세요.', 'error');

    el.submitBtn.disabled = true;
    try {
      if (state.editingId) {
        await api(`/api/data/${encodeURIComponent(state.editingId)}`, {
          method: 'PUT',
          body: { date, value, memo },
        });
        toast('데이터를 수정했습니다.', 'success');
      } else {
        await api('/api/data', { method: 'POST', body: { date, value, memo } });
        toast('데이터를 추가했습니다.', 'success');
      }
      resetForm();
      await loadData();
    } catch (err) {
      toast(`저장 실패: ${err.message}`, 'error');
    } finally {
      el.submitBtn.disabled = false;
    }
  }

  async function deletePoint(id) {
    if (!confirm('이 데이터를 삭제할까요?')) return;
    try {
      await api(`/api/data/${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (state.editingId === id) resetForm();
      toast('데이터를 삭제했습니다.', 'success');
      await loadData();
    } catch (err) {
      toast(`삭제 실패: ${err.message}`, 'error');
    }
  }

  async function downloadCsv() {
    el.csvBtn.disabled = true;
    try {
      const res = await api('/api/data/export/csv', { raw: true });
      const blob = await res.blob();
      const cd = res.headers.get('Content-Disposition') || '';
      const m = cd.match(/filename="?([^";]+)"?/i);
      const filename = m ? m[1] : `data_export_${todayStr()}.csv`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast('CSV 파일을 다운로드합니다.', 'success');
    } catch (err) {
      toast(`CSV 다운로드 실패: ${err.message}`, 'error');
    } finally {
      el.csvBtn.disabled = false;
    }
  }

  // ------------------------------------------------------------------ 이벤트 바인딩
  function bindEvents() {
    el.themeToggle.addEventListener('click', toggleTheme);
    el.menuBtn.addEventListener('click', () => openSidebar(true));
    el.backdrop.addEventListener('click', () => openSidebar(false));
    el.newChatBtn.addEventListener('click', newChat);

    $$('.tab').forEach((t) => t.addEventListener('click', () => switchPane(t.dataset.target)));

    el.sendBtn.addEventListener('click', () => sendMessage());
    el.chatInput.addEventListener('input', autosizeInput);
    el.chatInput.addEventListener('keydown', (e) => {
      // 한글 IME 조합 중 Enter 는 무시
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) {
        e.preventDefault();
        sendMessage();
      }
    });

    el.welcome.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (chip) sendMessage(chip.dataset.prompt);
    });

    el.convList.addEventListener('click', (e) => {
      const item = e.target.closest('.conv-item');
      if (!item) return;
      const id = item.dataset.id;
      if (e.target.closest('[data-action="delete"]')) deleteConversation(id);
      else openConversation(id);
    });

    el.form.addEventListener('submit', submitForm);
    el.cancelEditBtn.addEventListener('click', resetForm);
    el.refreshBtn.addEventListener('click', loadData);
    el.csvBtn.addEventListener('click', downloadCsv);

    el.dataBody.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'edit') startEdit(btn.dataset.id);
      if (btn.dataset.action === 'delete') deletePoint(btn.dataset.id);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') openSidebar(false);
    });
  }

  // ------------------------------------------------------------------ 초기화
  async function init() {
    applyTheme(document.documentElement.getAttribute('data-theme') || 'light');
    el.fDate.value = todayStr();
    bindEvents();

    // 서버 깨우기: 콜드스타트 안내 배너가 필요 시 자동 표시됨
    try {
      await api('/health', { retries: 3 });
    } catch (err) {
      toast(err.message, 'error', 7000);
    }

    await Promise.all([loadConversations(), loadData()]);
  }

  // Chart.js 가 defer 로 로드되므로 DOMContentLoaded 이후 실행
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();