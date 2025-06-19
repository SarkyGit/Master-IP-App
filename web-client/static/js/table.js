function tableControls() {
  return {
    search: '',
    perPage: 10,
    page: 0,
    sortIndex: null,
    sortAsc: true,
    originalOrder: [],
    headers: [],
    selectedIds: [],
    init() {
      this.$watch('search', () => { this.page = 0; this.update() })
      this.$watch('perPage', () => { this.page = 0; this.update() })
      this.originalOrder = this.rows.slice()
      this.initSorting()
      this.loadSortPrefs()
      this.applySort()
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
    sort(idx) {
      if (this.sortIndex === idx) {
        if (this.sortAsc) {
          this.sortAsc = false
        } else {
          this.sortIndex = null
          this.sortAsc = true
        }
      } else {
        this.sortIndex = idx
        this.sortAsc = true
      }
      this.applySort()
      this.page = 0
      this.update()
      this.saveSortPrefs()
    },
    applySort() {
      const body = this.$el.querySelector('tbody')
      if (this.sortIndex === null) {
        this.originalOrder.forEach(r => body.appendChild(r))
        this.updateSortIndicators()
        return
      }
      const idx = this.sortIndex
      const rows = Array.from(body.children)
      const header = this.headers[idx]
      const type = header?.dataset.sortType
      const key = r => {
        const cell = r.children[idx]
        if (!cell) return ''
        const raw = (cell.dataset.ip || cell.innerText).trim()
        if (type === 'ip') return ipSortKey(raw)
        if (type === 'number') {
          const n = parseFloat(raw.replace(/[^0-9.-]/g,''))
          return isNaN(n) ? 0 : n
        }
        if (type === 'date') {
          const t = Date.parse(raw)
          return isNaN(t) ? 0 : t
        }
        const num = parseFloat(raw)
        if (!isNaN(num) && /^\d/.test(raw)) return num
        return raw.toLowerCase()
      }
      rows.sort((a,b)=>{const A=key(a), B=key(b); if(A>B) return 1; if(A<B) return -1; return 0})
      if (!this.sortAsc) rows.reverse()
      rows.forEach(r => body.appendChild(r))
      this.updateSortIndicators()
    },
    initSorting() {
      const headers = Array.from(this.$el.querySelectorAll('th'))
      this.headers = headers
      headers.forEach((th,i)=>{
        if (th.classList.contains('actions-col') || th.classList.contains('checkbox-col')) return
        if (!th.dataset.sortType && /ip/i.test(th.textContent.trim())) th.dataset.sortType = 'ip'
        th.style.cursor = 'pointer'
        const icon = document.createElement('span')
        icon.className = 'sort-indicator inline-block ml-1'
        th.appendChild(icon)
        th.addEventListener('click', () => this.sort(i))
      })
      let idx = headers.findIndex(h => /ip/i.test(h.textContent.trim()))
      if (idx === -1) idx = headers.findIndex(h => /name/i.test(h.textContent.trim()))
      if (idx === -1) idx = headers.findIndex(h => /id/i.test(h.textContent.trim()))
      if (this.sortIndex === null && idx >= 0) {
        this.sortIndex = idx
      }
      this.updateSortIndicators()
    },
    update() {
      const start = this.start, end = this.end
      this.filteredRows.forEach((row, i) => { row.style.display = (i>=start && i<end)?'' : 'none' })
    },
    saveSortPrefs() {
      const table = this.$el.querySelector('table')
      if (!table || !table.dataset.tableId) return
      const key = `table-sort-${table.dataset.tableId}`
      if (this.sortIndex === null) {
        sessionStorage.removeItem(key)
      } else {
        sessionStorage.setItem(key, JSON.stringify({index:this.sortIndex, asc:this.sortAsc}))
      }
    },
    loadSortPrefs() {
      const table = this.$el.querySelector('table')
      if (!table || !table.dataset.tableId) return
      const key = `table-sort-${table.dataset.tableId}`
      const data = sessionStorage.getItem(key)
      if (data) {
        try {
          const obj = JSON.parse(data)
          this.sortIndex = obj.index
          this.sortAsc = obj.asc
        } catch {}
      }
    },
    updateSortIndicators() {
      this.headers.forEach((th,i)=>{
        const icon = th.querySelector('.sort-indicator')
        if (!icon) return
        if (this.sortIndex === i) {
          icon.textContent = this.sortAsc ? '↑' : '↓'
        } else {
          icon.textContent = ''
        }
      })
    }
  }
}

function setupTablePrefs() {
  const pathId = window.location.pathname.replace(/\W/g, '_')
  document.querySelectorAll('table').forEach((table, idx) => {
    if (table.classList.contains('no-prefs')) return
    const tableId = `${pathId}_${idx}`
    table.dataset.tableId = tableId
    initResize(table, tableId)
    insertCustomizeButton(table, tableId)
    loadPrefs(table, tableId)
  })
}

function initResize(table, tableId) {
  table.querySelectorAll('th').forEach((th, idx) => {
    if (th.classList.contains('no-resize') || th.classList.contains('checkbox-col') || th.classList.contains('actions-col')) return
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
      if (Object.keys(p.column_widths).length === 0) {
        setTimeout(() => {
          autoscale(table)
          saveWidths(table, tableId)
        })
      }
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

function autoscale(table) {
  const rows = table.querySelectorAll('tbody tr')
  table.querySelectorAll('th').forEach((th, i) => {
    if (th.classList.contains('checkbox-col') || th.classList.contains('actions-col') || th.classList.contains('no-resize')) return
    if (th.style.display === 'none') return
    let max = th.scrollWidth
    rows.forEach(row => {
      const cell = row.children[i]
      if (cell && cell.style.display !== 'none') {
        const width = cell.scrollWidth
        if (width > max) max = width
      }
    })
    const final = max + 16
    th.style.width = final + 'px'
    rows.forEach(row => {
      const cell = row.children[i]
      if (cell) cell.style.width = final + 'px'
    })
  })
}

function ipSortKey(ip) {
  return ip.split('.').map(p => p.padStart(3,'0')).join('.')
}

document.addEventListener('DOMContentLoaded', setupTablePrefs)
