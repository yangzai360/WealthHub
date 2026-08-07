import { defineClientConfig } from 'vuepress/client'
import DashboardCharts from './components/DashboardCharts.vue'
import EChart from './components/EChart.vue'
import RightToc from './components/RightToc.vue'

// VuePress 2 不会自动注册 .vuepress/components/ 下的组件(那是 VuePress 1 的特性),
// 必须通过 client.ts 手动注册为全局组件, Markdown 中的 <DashboardCharts /> 才能渲染
export default defineClientConfig({
  enhance({ app }) {
    app.component('DashboardCharts', DashboardCharts)
    app.component('EChart', EChart)
    app.component('RightToc', RightToc)
  },
})
