<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import EChart from './EChart.vue'

interface TrackDist { name: string; value: number }
interface Quote { name: string; close: number; pct: number }
interface EtfQuote { name: string; pct: number }
interface FundNav { name: string; nav: number; pct: number }
interface Sentiment { name: string; value: number }
interface Charts {
  track_dist: TrackDist[]
  indices: Quote[]
  etf_quotes: EtfQuote[]
  fund_navs: FundNav[]
  sentiment: Sentiment[]
}

const charts = ref<Charts>({
  track_dist: [], indices: [], etf_quotes: [], fund_navs: [], sentiment: [],
})
const loaded = ref(false)

const COLOR_BY_TRACK: Record<string, string> = {
  'A股医药': '#E24B4A',
  '大消费': '#EF9F27',
  '美股标普医药': '#378ADD',
  '恒生科技': '#7F77DD',
  '其他/宽基': '#888780',
}

const pieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
  series: [{
    type: 'pie',
    radius: ['42%', '70%'],
    avoidLabelOverlap: true,
    label: { formatter: '{b}\n{d}%' },
    data: charts.value.track_dist.map(t => ({
      name: t.name, value: t.value,
      itemStyle: { color: COLOR_BY_TRACK[t.name] || '#888780' },
    })),
  }],
}))

const indexBarOption = computed(() => {
  const d = charts.value.indices.filter(i => i.pct !== undefined)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 60 },
    xAxis: { type: 'category', data: d.map(i => i.name), axisLabel: { interval: 0, rotate: 25 } },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [{
      type: 'bar',
      data: d.map(i => ({
        value: i.pct,
        itemStyle: { color: i.pct >= 0 ? '#E24B4A' : '#1D9E75' },
      })),
      label: { show: true, position: 'top', formatter: '{c}%' },
    }],
  }
})

const etfBarOption = computed(() => {
  const d = charts.value.etf_quotes
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 90, right: 40, top: 20, bottom: 30 },
    xAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    yAxis: { type: 'category', data: d.map(i => i.name).reverse() },
    series: [{
      type: 'bar',
      data: d.map(i => ({
        value: i.pct,
        itemStyle: { color: i.pct >= 0 ? '#E24B4A' : '#1D9E75' },
      })).reverse(),
      label: { show: true, position: 'right', formatter: '{c}%' },
    }],
  }
})

const fundBarOption = computed(() => {
  const d = charts.value.fund_navs
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 130, right: 50, top: 20, bottom: 30 },
    xAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    yAxis: { type: 'category', data: d.map(i => i.name).reverse() },
    series: [{
      type: 'bar',
      data: d.map(i => ({
        value: i.pct,
        itemStyle: { color: i.pct >= 0 ? '#E24B4A' : '#1D9E75' },
      })).reverse(),
      label: { show: true, position: 'right', formatter: '{c}%' },
    }],
  }
})

const sentimentBarOption = computed(() => {
  const d = charts.value.sentiment
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 100, right: 40, top: 20, bottom: 30 },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}' } },
    yAxis: { type: 'category', data: d.map(i => i.name).reverse() },
    series: [{
      type: 'bar',
      data: d.map(i => ({
        value: i.value,
        itemStyle: { color: i.value >= 60 ? '#E24B4A' : i.value >= 40 ? '#EF9F27' : '#1D9E75' },
      })).reverse(),
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  }
})

onMounted(async () => {
  try {
    const res = await fetch('/WealthHub/data/charts.json')
    const data = await res.json()
    charts.value = { ...charts.value, ...data }
  } catch {
    try {
      const res = await fetch('/data/charts.json')
      charts.value = { ...charts.value, ...(await res.json()) }
    } catch { /* ignore */ }
  }
  loaded.value = true
})
</script>

<template>
  <div v-if="loaded" class="dashboard">
    <h3>赛道配置分布</h3>
    <EChart v-if="charts.track_dist.length" :option="pieOption" height="300px" />
    <p v-else class="empty">暂无数据</p>

    <h3>指数行情涨跌（%）</h3>
    <EChart v-if="charts.indices.length" :option="indexBarOption" height="300px" />
    <p v-else class="empty">暂无数据</p>

    <h3>场内 ETF 盘中涨跌（%）</h3>
    <EChart v-if="charts.etf_quotes.length" :option="etfBarOption" height="320px" />
    <p v-else class="empty">暂无数据</p>

    <h3>场外基金净值涨跌（%）</h3>
    <EChart v-if="charts.fund_navs.length" :option="fundBarOption" height="340px" />
    <p v-else class="empty">暂无数据</p>

    <h3>新闻情绪强度（0-100）</h3>
    <EChart v-if="charts.sentiment.length" :option="sentimentBarOption" height="260px" />
    <p v-else class="empty">暂无数据</p>
  </div>
  <p v-else>图表加载中…</p>
</template>

<style scoped>
.dashboard h3 {
  margin-top: 28px;
  font-size: 15px;
  font-weight: 500;
}
.empty { color: #888; font-size: 13px; }
</style>
