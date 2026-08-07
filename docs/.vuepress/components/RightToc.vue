<template>
  <!-- 宽屏：右侧固定目录，标题栏可点击展开/收起 -->
  <aside v-if="wide" class="right-toc" :class="{ collapsed }">
    <div class="rt-head" @click="toggle">
      <span class="rt-title">📑 本页目录</span>
      <span class="rt-arrow" :class="{ open: !collapsed }">▾</span>
    </div>
    <nav v-show="!collapsed" class="rt-body">
      <ul>
        <li v-for="h in headings" :key="h.id" :class="['rt-item', `lv-${h.level}`, { active: h.id === activeId }]">
          <a :href="`#${h.id}`" @click.prevent="jump(h.id)">{{ h.text }}</a>
        </li>
      </ul>
      <p v-if="!headings.length" class="rt-empty">本页暂无章节</p>
    </nav>
  </aside>

  <!-- 窄屏：右下角浮动按钮，点击弹出目录浮层 -->
  <button v-else class="rt-fab" @click="fabOpen = true">☰ 目录</button>
  <div v-if="!wide && fabOpen" class="rt-mask" @click="fabOpen = false">
    <aside class="rt-panel" @click.stop>
      <div class="rt-head">
        <span class="rt-title">📑 本页目录</span>
        <button class="rt-close" @click="fabOpen = false">✕</button>
      </div>
      <nav class="rt-body">
        <ul>
          <li v-for="h in headings" :key="h.id" :class="['rt-item', `lv-${h.level}`, { active: h.id === activeId }]">
            <a :href="`#${h.id}`" @click.prevent="jump(h.id); fabOpen = false">{{ h.text }}</a>
          </li>
        </ul>
        <p v-if="!headings.length" class="rt-empty">本页暂无章节</p>
      </nav>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

interface Heading {
  id: string
  text: string
  level: number
}

const WIDE_QUERY = '(min-width: 1280px)'

const wide = ref(false)
const collapsed = ref(false)
const fabOpen = ref(false)
const headings = ref<Heading[]>([])
const activeId = ref('')

let mql: MediaQueryList | null = null
let observer: IntersectionObserver | null = null

function collectHeadings(): Heading[] {
  const root = document.getElementById('content') ?? document
  return Array.from(root.querySelectorAll<HTMLElement>('h2, h3'))
    .map((el) => ({ id: el.id, text: el.textContent?.trim() ?? '', level: Number(el.tagName.slice(1)) }))
    .filter((h) => h.id && h.text)
}

function jump(id: string) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function toggle() {
  collapsed.value = !collapsed.value
  try {
    localStorage.setItem('wh-rt-collapsed', collapsed.value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

function setupObserver() {
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) activeId.value = entry.target.id
      }
    },
    { rootMargin: '-80px 0px -70% 0px' }
  )
  for (const h of headings.value) {
    const el = document.getElementById(h.id)
    if (el) observer.observe(el)
  }
}

onMounted(() => {
  headings.value = collectHeadings()
  setupObserver()

  mql = window.matchMedia(WIDE_QUERY)
  wide.value = mql.matches
  const onChange = (e: MediaQueryListEvent) => {
    wide.value = e.matches
    if (e.matches) fabOpen.value = false
  }
  mql.addEventListener('change', onChange)

  try {
    collapsed.value = localStorage.getItem('wh-rt-collapsed') === '1'
  } catch {
    /* ignore */
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  mql?.removeEventListener('change', () => {})
})
</script>

<style scoped>
.right-toc {
  position: fixed;
  top: calc(var(--navbar-height, 3.6rem) + 1rem);
  right: 1rem;
  width: 14.5rem;
  max-height: calc(100vh - var(--navbar-height, 3.6rem) - 3rem);
  display: flex;
  flex-direction: column;
  background: var(--vp-c-bg, #fff);
  border: 1px solid var(--vp-c-divider, #e2e2e3);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  font-size: 0.82rem;
  z-index: 20;
}

.rt-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 0.75rem;
  cursor: pointer;
  user-select: none;
  font-weight: 600;
  color: var(--vp-c-text, #2c3e50);
  background: var(--vp-c-bg-alt, #f6f6f7);
  border-bottom: 1px solid var(--vp-c-divider, #e2e2e3);
}

.rt-arrow {
  transition: transform 0.2s;
  font-size: 0.7rem;
  color: var(--vp-c-text-mute, #999);
}
.rt-arrow.open {
  transform: rotate(180deg);
}

.rt-body {
  overflow-y: auto;
  padding: 0.4rem 0.5rem;
}
.rt-body ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.rt-item a {
  display: block;
  padding: 0.28rem 0.45rem;
  color: var(--vp-c-text, #2c3e50);
  text-decoration: none;
  border-radius: 4px;
  line-height: 1.35;
  word-break: break-all;
}
.rt-item a:hover {
  color: var(--vp-c-accent, #3eaf7c);
  background: var(--vp-c-bg-alt, #f6f6f7);
}
.rt-item.active a {
  color: var(--vp-c-accent, #3eaf7c);
  font-weight: 600;
}
.rt-item.lv-3 a {
  padding-inline-start: 1rem;
  color: var(--vp-c-text-mute, #666);
}
.rt-empty {
  margin: 0.5rem;
  color: var(--vp-c-text-mute, #999);
}

/* 窄屏浮动按钮与浮层 */
.rt-fab {
  position: fixed;
  right: 1rem;
  bottom: 1.5rem;
  z-index: 40;
  padding: 0.55rem 0.9rem;
  border: none;
  border-radius: 999px;
  background: var(--vp-c-accent, #3eaf7c);
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
}
.rt-fab:active {
  transform: scale(0.96);
}
.rt-mask {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  justify-content: flex-end;
}
.rt-panel {
  width: min(85vw, 20rem);
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--vp-c-bg, #fff);
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.15);
  font-size: 0.85rem;
}
.rt-close {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--vp-c-text, #2c3e50);
}
</style>
