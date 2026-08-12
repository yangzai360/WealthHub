<template>
  <div class="grid-depth">
    <!-- 概览卡片 -->
    <div v-if="data" class="gd-summary">
      <div class="gd-card">
        <div class="gd-num">{{ data.invested_units }}<span class="gd-unit">/{{ data.total_units }}</span></div>
        <div class="gd-label">已投入份数 · {{ data.invested_pct }}%</div>
      </div>
      <div class="gd-card">
        <div class="gd-num">{{ data.cash_units }}</div>
        <div class="gd-label">现金子弹（份）</div>
      </div>
      <div class="gd-card">
        <div class="gd-num">{{ data.holding_count }}</div>
        <div class="gd-label">持仓品种</div>
      </div>
      <div class="gd-card">
        <div class="gd-num gd-deep">{{ maxPos.variety }}</div>
        <div class="gd-label">最深仓 · {{ maxPos.pos }} 份（{{ maxPos.depth_pct }}%）</div>
      </div>
    </div>

    <!-- 筛选 -->
    <div v-if="data" class="gd-filters">
      <button
        v-for="f in filters"
        :key="f.key"
        class="gd-filter"
        :class="{ active: filter === f.key }"
        @click="filter = f.key"
      >
        {{ f.label }}（{{ filteredCount(f.key) }}）
      </button>
    </div>

    <!-- 表格 -->
    <table v-if="data" class="gd-table">
      <thead>
        <tr>
          <th>#</th>
          <th>品种</th>
          <th>投入深度</th>
          <th>当前份数</th>
          <th>累计买入</th>
          <th>累计卖出</th>
          <th>最近操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(p, i) in filtered" :key="p.fund_code">
          <td class="gd-rank">{{ i + 1 }}</td>
          <td class="gd-name">
            <span class="gd-variety">{{ p.variety }}</span>
            <span class="gd-class">{{ p.large_class }}</span>
          </td>
          <td class="gd-depth">
            <div class="gd-bar">
              <div :class="barClass(p)" :style="{ width: barWidth(p) }"></div>
            </div>
            <span :class="['gd-pct', barClass(p)]">{{ p.depth_pct }}%</span>
          </td>
          <td class="gd-pos">{{ p.pos }} 份</td>
          <td class="gd-buy">{{ p.buy }}</td>
          <td class="gd-sell">{{ p.sell }}</td>
          <td class="gd-last">
            <span v-if="p.last_dir" class="gd-dir" :class="p.last_dir === '买入' ? 'dir-buy' : 'dir-sell'">
              {{ p.last_dir }}
            </span>
            <span v-else class="gd-dir">—</span>
            <span class="gd-date">{{ p.last_date || '—' }}</span>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="gd-loading">{{ loadError || '加载中…' }}</div>

    <p v-if="data" class="gd-note">
      数据来源：且慢 LONG_WIN 计划公开数据（组合快照 {{ data.snapshot_date }}）。1 份 ≈ 计划资金的 0.67%；
      深仓（红色）代表 E 大低位持续买入、尚未止盈的品种，可作跟投参考；已开始分批卖出的品种（绿色标签）追高需谨慎。
      此外另有 {{ clearedCount }} 个已清仓品种未展示。每日定时任务增量更新。
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Position {
  fund_code: string
  variety: string
  fund_name: string
  large_class: string
  pos: number
  depth_pct: number
  buy: number
  sell: number
  last_date: string
  last_dir: string
}
interface GridData {
  generated_at: string
  snapshot_date: string
  total_units: number
  cash_units: number
  invested_units: number
  invested_pct: number
  holding_count: number
  positions: Position[]
}

const data = ref<GridData | null>(null)
const loadError = ref('')
const filter = ref('all')

const filters = [
  { key: 'all', label: '全部' },
  { key: 'deep', label: '深仓 ≥5份' },
  { key: 'mid', label: '中仓 2-4份' },
  { key: 'shallow', label: '浅仓 1份' },
]

const maxPos = computed<Position>(() =>
  (activePositions.value ?? []).reduce(
    (m, p) => (p.pos > m.pos ? p : m),
    { variety: '—', pos: 0, depth_pct: 0 } as Position,
  ),
)

const activePositions = computed<Position[]>(() =>
  (data.value?.positions ?? []).filter((p) => p.pos > 0),
)

function matches(key: string, p: Position): boolean {
  if (key === 'deep') return p.pos >= 5
  if (key === 'mid') return p.pos >= 2 && p.pos < 5
  if (key === 'shallow') return p.pos === 1
  return true
}
function filteredCount(key: string): number {
  return activePositions.value.filter((p) => matches(key, p)).length
}
const filtered = computed(() =>
  activePositions.value.filter((p) => matches(filter.value, p)),
)

const clearedCount = computed(
  () => (data.value?.positions ?? []).filter((p) => p.pos <= 0).length,
)

function barWidth(p: Position): string {
  const m = Math.max(1, maxPos.value.pos)
  return `${Math.round((p.pos / m) * 100)}%`
}
function barClass(p: Position): string {
  if (p.pos >= 5) return 'lv-deep'
  if (p.pos >= 2) return 'lv-mid'
  return 'lv-shallow'
}

onMounted(async () => {
  for (const base of ['/WealthHub/data/grid-depth.json', '/data/grid-depth.json']) {
    try {
      const res = await fetch(base)
      if (res.ok) {
        data.value = await res.json()
        return
      }
    } catch {
      /* 尝试下一个 base */
    }
  }
  loadError.value = '⚠️ 网格深度数据加载失败'
})
</script>

<style scoped>
.grid-depth {
  margin: 0.5rem 0 1.5rem;
  font-size: 0.9rem;
}
.gd-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.6rem;
  margin-bottom: 0.9rem;
}
.gd-card {
  background: var(--c-bg-light, #f7f8fa);
  border: 1px solid var(--c-border, #eaecef);
  border-radius: 8px;
  padding: 0.7rem 0.9rem;
  text-align: center;
}
.gd-num {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--c-text, #2c3e50);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.gd-num.gd-deep {
  color: #e24b4a;
}
.gd-unit {
  font-size: 0.85rem;
  font-weight: 400;
  color: var(--c-text-light, #7a8ba3);
}
.gd-label {
  margin-top: 0.2rem;
  font-size: 0.75rem;
  color: var(--c-text-light, #7a8ba3);
}
.gd-filters {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.7rem;
  flex-wrap: wrap;
}
.gd-filter {
  border: 1px solid var(--c-border, #eaecef);
  background: var(--c-bg, #fff);
  color: var(--c-text, #2c3e50);
  border-radius: 999px;
  padding: 0.2rem 0.8rem;
  font-size: 0.78rem;
  cursor: pointer;
  transition: all 0.15s;
}
.gd-filter:hover {
  border-color: #3eaf7c;
  color: #3eaf7c;
}
.gd-filter.active {
  background: #3eaf7c;
  border-color: #3eaf7c;
  color: #fff;
}
.gd-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.gd-table th {
  text-align: left;
  font-weight: 600;
  color: var(--c-text-light, #7a8ba3);
  border-bottom: 2px solid var(--c-border, #eaecef);
  padding: 0.45rem 0.5rem;
  white-space: nowrap;
  font-size: 0.78rem;
}
.gd-table td {
  border-bottom: 1px solid var(--c-border-light, #f0f1f3);
  padding: 0.45rem 0.5rem;
  vertical-align: middle;
}
.gd-table tbody tr:hover {
  background: var(--c-bg-light, #f7f8fa);
}
.gd-rank {
  color: var(--c-text-light, #7a8ba3);
  width: 2.2rem;
}
.gd-name {
  min-width: 9rem;
}
.gd-variety {
  font-weight: 600;
  display: block;
}
.gd-class {
  font-size: 0.72rem;
  color: var(--c-text-light, #7a8ba3);
}
.gd-depth {
  min-width: 7.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.gd-bar {
  flex: 1;
  height: 0.55rem;
  background: var(--c-border-light, #f0f1f3);
  border-radius: 999px;
  overflow: hidden;
}
.gd-bar > div {
  height: 100%;
  border-radius: 999px;
  transition: width 0.3s;
}
.lv-deep {
  background: #e24b4a;
  color: #e24b4a;
}
.lv-mid {
  background: #ef9f27;
  color: #ef9f27;
}
.lv-shallow {
  background: #1d9e75;
  color: #1d9e75;
}
.gd-pct {
  font-weight: 600;
  white-space: nowrap;
  min-width: 3rem;
  text-align: right;
}
.gd-pos {
  font-weight: 600;
  white-space: nowrap;
}
.gd-buy,
.gd-sell {
  text-align: center;
  color: var(--c-text, #2c3e50);
}
.gd-dir {
  display: inline-block;
  border-radius: 4px;
  padding: 0.05rem 0.45rem;
  font-size: 0.75rem;
  font-weight: 600;
  margin-right: 0.35rem;
}
.dir-buy {
  background: rgba(226, 75, 74, 0.12);
  color: #e24b4a;
}
.dir-sell {
  background: rgba(29, 158, 117, 0.12);
  color: #1d9e75;
}
.gd-date {
  color: var(--c-text-light, #7a8ba3);
  font-size: 0.78rem;
  white-space: nowrap;
}
.gd-note {
  margin-top: 0.8rem;
  font-size: 0.75rem;
  color: var(--c-text-light, #7a8ba3);
  line-height: 1.6;
}
.gd-loading {
  padding: 2rem;
  text-align: center;
  color: var(--c-text-light, #7a8ba3);
}
@media (max-width: 720px) {
  .gd-table {
    font-size: 0.78rem;
  }
  .gd-class,
  .gd-date {
    display: none;
  }
  .gd-name {
    min-width: 6rem;
  }
}
</style>
