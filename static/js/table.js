function tableControls() {
  return {
    search: '',
    perPage: 10,
    page: 0,
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
    update() {
      const start = this.start, end = this.end
      this.filteredRows.forEach((row, i) => { row.style.display = (i>=start && i<end)?'' : 'none' })
    }
  }
}
