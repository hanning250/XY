const state = {
  alarms: [],
  selectedId: null,
  ws: null,
  reconnectTimer: null,
};

const els = {
  wsStatus: document.getElementById("ws-status"),
  clientCount: document.getElementById("client-count"),
  statTotal: document.getElementById("stat-total"),
  statActive: document.getElementById("stat-active"),
  statInactive: document.getElementById("stat-inactive"),
  statDevices: document.getElementById("stat-devices"),
  alarmCount: document.getElementById("alarm-count"),
  tableBody: document.getElementById("alarm-table-body"),
  detail: document.getElementById("alarm-detail"),
  filterDevice: document.getElementById("filter-device"),
  filterRule: document.getElementById("filter-rule"),
  btnRefresh: document.getElementById("btn-refresh"),
  btnClearFilters: document.getElementById("btn-clear-filters"),
  btnDeleteSelected: document.getElementById("btn-delete-selected"),
};

function formatTime(value) {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 19);
}

function buildQuery() {
  const params = new URLSearchParams({ limit: "100", offset: "0" });
  if (els.filterDevice.value.trim()) {
    params.set("device_id", els.filterDevice.value.trim());
  }
  return params.toString();
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function loadStats() {
  const stats = await fetchJson("/api/alarms/stats");
  els.statTotal.textContent = stats.total;
  els.statActive.textContent = stats.active;
  els.statInactive.textContent = stats.inactive;
  els.statDevices.textContent = Object.keys(stats.by_device || {}).length;
}

function filterAlarms(items) {
  const ruleKeyword = els.filterRule.value.trim().toLowerCase();
  if (!ruleKeyword) {
    return items;
  }
  return items.filter((alarm) =>
    String(alarm.ruleName || "").toLowerCase().includes(ruleKeyword)
  );
}

async function loadAlarms() {
  const data = await fetchJson(`/api/alarms?${buildQuery()}`);
  state.alarms = filterAlarms(data.items || []);
  renderTable();
  if (state.selectedId) {
    const selected = state.alarms.find((item) => item.id === state.selectedId);
    if (selected) {
      renderDetail(selected);
    } else {
      clearDetail();
    }
  }
}

function clearDetail() {
  state.selectedId = null;
  els.btnDeleteSelected.disabled = true;
  els.detail.innerHTML = `<p class="placeholder">点击列表中的告警查看详情</p>`;
}

function removeAlarm(alarmId) {
  state.alarms = state.alarms.filter((item) => item.id !== alarmId);
  if (state.selectedId === alarmId) {
    clearDetail();
  }
  renderTable();
  loadStats();
}

async function deleteAlarm(alarmId) {
  const alarm = state.alarms.find((item) => item.id === alarmId);
  const label = alarm ? `#${alarm.id} ${alarm.ruleName || ""}` : `#${alarmId}`;
  if (!window.confirm(`确定删除告警 ${label} 吗？`)) {
    return;
  }

  await fetchJson(`/api/alarms/${alarmId}`, { method: "DELETE" });
  removeAlarm(alarmId);
}

function renderTable() {
  els.alarmCount.textContent = `${state.alarms.length} 条`;
  els.tableBody.innerHTML = state.alarms
    .map(
      (alarm) => `
      <tr data-id="${alarm.id}" class="${alarm.id === state.selectedId ? "selected" : ""}">
        <td>${alarm.id}</td>
        <td>${formatTime(alarm.alarmTime)}</td>
        <td>${escapeHtml(alarm.deviceId || "-")}</td>
        <td>${escapeHtml(alarm.ruleName || "-")}</td>
        <td>${escapeHtml(alarm.attrLabel || "-")} (${alarm.attrValue ?? 0})</td>
        <td>${alarm.attrConf ?? 0}</td>
        <td>
          <button class="btn-danger btn-small" data-delete-id="${alarm.id}">删除</button>
        </td>
      </tr>
    `
    )
    .join("");

  els.tableBody.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest("[data-delete-id]")) {
        return;
      }
      state.selectedId = Number(row.dataset.id);
      renderTable();
      const alarm = state.alarms.find((item) => item.id === state.selectedId);
      if (alarm) renderDetail(alarm);
    });
  });

  els.tableBody.querySelectorAll("[data-delete-id]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const alarmId = Number(button.dataset.deleteId);
      try {
        await deleteAlarm(alarmId);
      } catch (error) {
        console.error(error);
        alert(`删除失败: ${error.message}`);
      }
    });
  });
}

function renderDetail(alarm) {
  els.btnDeleteSelected.disabled = false;
  els.detail.innerHTML = `
    <dl class="detail-grid">
      <dt>ID</dt><dd>${alarm.id}</dd>
      <dt>告警时间</dt><dd>${formatTime(alarm.alarmTime)}</dd>
      <dt>设备</dt><dd>${escapeHtml(alarm.deviceId || "-")}</dd>
      <dt>规则名称</dt><dd>${escapeHtml(alarm.ruleName || "-")}</dd>
      <dt>属性值</dt><dd>${alarm.attrValue ?? 0}</dd>
      <dt>属性标签</dt><dd>${escapeHtml(alarm.attrLabel || "-")}</dd>
      <dt>置信度</dt><dd>${alarm.attrConf ?? 0}</dd>
    </dl>
    <h3>告警图片</h3>
    <img
      class="alarm-image"
      src="${alarm.imageUrl}"
      alt="告警图片"
      onerror="this.classList.add('hidden'); this.nextElementSibling.classList.remove('hidden');"
    />
    <p class="placeholder hidden">暂无图片</p>
  `;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function prependAlarm(alarm) {
  if (!filterAlarms([alarm]).length) {
    return;
  }
  state.alarms = state.alarms.filter((item) => item.id !== alarm.id);
  state.alarms.unshift(alarm);
  if (state.alarms.length > 100) {
    state.alarms.pop();
  }
  renderTable();
  loadStats();
}

function setWsStatus(online) {
  els.wsStatus.textContent = online ? "WebSocket 已连接" : "WebSocket 未连接";
  els.wsStatus.className = online ? "badge badge-online" : "badge badge-offline";
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws/alarms`);
  state.ws = ws;

  ws.onopen = () => {
    setWsStatus(true);
    if (state.reconnectTimer) {
      clearTimeout(state.reconnectTimer);
      state.reconnectTimer = null;
    }
  };

  ws.onclose = () => {
    setWsStatus(false);
    state.reconnectTimer = setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = () => {
    ws.close();
  };

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === "deleted" && message.id) {
        removeAlarm(message.id);
        return;
      }
      if (message && message.id && message.alarmTime) {
        prependAlarm(message);
      }
    } catch (error) {
      console.error("Invalid WebSocket message", error);
    }
  };
}

async function refreshHealth() {
  try {
    const health = await fetchJson("/api/health");
    els.clientCount.textContent = `客户端: ${health.websocket_clients}`;
  } catch (error) {
    els.clientCount.textContent = "客户端: -";
  }
}

async function bootstrap() {
  els.btnRefresh.addEventListener("click", async () => {
    await Promise.all([loadStats(), loadAlarms()]);
  });

  els.btnClearFilters.addEventListener("click", async () => {
    els.filterDevice.value = "";
    els.filterRule.value = "";
    await loadAlarms();
  });

  els.btnDeleteSelected.addEventListener("click", async () => {
    if (!state.selectedId) {
      return;
    }
    try {
      await deleteAlarm(state.selectedId);
    } catch (error) {
      console.error(error);
      alert(`删除失败: ${error.message}`);
    }
  });

  els.filterDevice.addEventListener("change", loadAlarms);
  els.filterRule.addEventListener("input", () => {
    state.alarms = filterAlarms(state.alarms);
    renderTable();
  });

  await Promise.all([loadStats(), loadAlarms(), refreshHealth()]);
  connectWebSocket();
  setInterval(refreshHealth, 10000);
}

bootstrap().catch((error) => {
  console.error(error);
  els.detail.innerHTML = `<p class="placeholder">加载失败: ${escapeHtml(error.message)}</p>`;
});
