function tableControls() {
  return {
    search: '',
    perPage: 10,
    page: 0,
    selectedIds: [],
    init() {
      this.$watch('search', () => { this.page = 0; this.update() })
      this.$watch('perPage', () => { this.page = 0; this.update() })
      this.update()
    },
    get rows() {
      return Array.from(this.$el.querySelector('tbody').children)
    },
    get filteredRows() {
      if (!this.search) return this.rows
      const q = this.search.toLowerCase()
      return this.rows.filter(r => r.innerText.toLowerCase().includes(q))
    },
    get start() { return this.page * this.perPage },
    get end() { return Math.min(this.start + this.perPage, this.filteredRows.length) },
    next() { if (this.end < this.filteredRows.length) { this.page++; this.update() } },
    prev() { if (this.page > 0) { this.page--; this.update() } },
    countText() { if (this.filteredRows.length===0) return 'No entries' ; return `Showing ${this.start+1}-${this.end} of ${this.filteredRows.length} entries` },
    toggleAll(state) {
      this.selectedIds = []
      this.$el.querySelectorAll('input[name="selected"]').forEach(cb => {
        cb.checked = state
        if (state) this.selectedIds.push(cb.value)
      })
    },
    bulkDelete() { this.$el.action = '/devices/bulk-delete'; this.$el.submit() },
    bulkUpdate() { this.$el.action = '/devices/bulk-update'; this.$el.submit() },
    update() {
      const start = this.start, end = this.end
      this.filteredRows.forEach((row, i) => { row.style.display = (i>=start && i<end)?'' : 'none' })
    }
  }
}

function setupTablePrefs() {
  const pathId = window.location.pathname.replace(/\W/g, '_')
  document.querySelectorAll('table').forEach((table, idx) => {
    const tableId = `${pathId}_${idx}`
    table.dataset.tableId = tableId
    initResize(table, tableId)
    insertCustomizeButton(table, tableId)
    loadPrefs(table, tableId)
  })
}

function initResize(table, tableId) {
  table.querySelectorAll('th').forEach((th, idx) => {
    th.dataset.colIndex = idx
    th.style.position = 'relative'
    const handle = document.createElement('div')
    handle.className = 'resizer'
    th.appendChild(handle)
    let startX, startWidth
    handle.addEventListener('mousedown', e => {
      startX = e.pageX
      startWidth = th.offsetWidth
      handle.classList.add('active')
      document.body.classList.add('col-resize')
      const move = e2 => {
        const w = startWidth + (e2.pageX - startX)
        th.style.width = w + 'px'
        table.querySelectorAll('tr').forEach(row => {
          const cell = row.children[idx]
          if (cell) cell.style.width = w + 'px'
        })
      }
      const up = () => {
        document.removeEventListener('mousemove', move)
        document.removeEventListener('mouseup', up)
        document.body.classList.remove('col-resize')
        handle.classList.remove('active')
        saveWidths(table, tableId)
      }
      document.addEventListener('mousemove', move)
      document.addEventListener('mouseup', up)
    })
  })
}

function insertCustomizeButton(table, tableId) {
  const btn = document.createElement('button')
  btn.textContent = 'Customize Columns'
  btn.className = 'mb-2 px-2 py-1 bg-[var(--btn-bg)] hover:bg-[var(--btn-hover)] text-[var(--btn-text)] rounded'
  table.parentNode.insertBefore(btn, table)
  btn.addEventListener('click', () => showColumnModal(table, tableId))
}

function showColumnModal(table, tableId) {
  const modal = document.createElement('div')
  modal.className = 'fixed inset-0 bg-black/50 flex items-center justify-center'
  const box = document.createElement('div')
  box.className = 'bg-[var(--card-bg)] p-4'
  const list = document.createElement('div')
  table.querySelectorAll('th').forEach((th, idx) => {
    const label = th.textContent.trim() || `Column ${idx+1}`
    const chk = document.createElement('input')
    chk.type = 'checkbox'
    chk.checked = th.style.display !== 'none'
    chk.dataset.colIndex = idx
    const lbl = document.createElement('label')
    lbl.className = 'block'
    lbl.appendChild(chk)
    lbl.appendChild(document.createTextNode(' ' + label))
    list.appendChild(lbl)
  })
  const saveBtn = document.createElement('button')
  saveBtn.textContent = 'Save'
  saveBtn.className = 'mt-2 px-2 py-1 bg-[var(--btn-bg)] hover:bg-[var(--btn-hover)] text-[var(--btn-text)] rounded'
  box.appendChild(list)
  box.appendChild(saveBtn)
  modal.appendChild(box)
  document.body.appendChild(modal)
  saveBtn.addEventListener('click', () => {
    list.querySelectorAll('input[type=checkbox]').forEach(chk => {
      const idx = chk.dataset.colIndex
      const show = chk.checked
      table.querySelectorAll('tr').forEach(row => {
        const cell = row.children[idx]
        if (cell) cell.style.display = show ? '' : 'none'
      })
    })
    document.body.removeChild(modal)
    saveVisible(table, tableId)
  })
}

function loadPrefs(table, tableId) {
  fetch(`/api/table-prefs/${tableId}`)
    .then(r => r.ok ? r.json() : {column_widths:{}, visible_columns:[]})
    .then(p => {
      Object.entries(p.column_widths).forEach(([i,w]) => {
        table.querySelectorAll('tr').forEach(row => {
          const cell = row.children[i]
          if (cell) cell.style.width = w
        })
      })
      p.visible_columns.forEach(i => {
        table.querySelectorAll('tr').forEach(row => {
          const cell = row.children[i]
          if (cell) cell.style.display = 'none'
        })
      })
    })
}

function savePrefs(tableId, data) {
  fetch(`/api/table-prefs/${tableId}`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  })
}

function saveWidths(table, tableId) {
  const widths = {}
  table.querySelectorAll('th').forEach((th,i)=>{
    widths[i] = th.offsetWidth + 'px'
  })
  savePrefs(tableId, {column_widths: widths, visible_columns: getHidden(table)})
}

function saveVisible(table, tableId) {
  savePrefs(tableId, {column_widths: getWidths(table), visible_columns: getHidden(table)})
}

function getWidths(table) {
  const w = {}
  table.querySelectorAll('th').forEach((th,i)=>{ w[i] = th.offsetWidth + 'px' })
  return w
}

function getHidden(table) {
  const arr = []
  table.querySelectorAll('th').forEach((th,i)=>{ if (th.style.display==='none') arr.push(String(i)) })
  return arr
}

document.addEventListener('DOMContentLoaded', setupTablePrefs)
