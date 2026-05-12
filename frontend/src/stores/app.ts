import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { sidebarCollapsed, toggleSidebar }
})

export interface TagView {
  path: string
  name: string
  title: string
}

export const useTagsViewStore = defineStore('tagsView', () => {
  const visitedViews = ref<TagView[]>([
    { path: '/', name: 'Home', title: '首页' }
  ])

  const addView = (view: TagView) => {
    if (visitedViews.value.some(v => v.path === view.path)) return
    visitedViews.value.push(view)
  }

  const delView = (path: string) => {
    const idx = visitedViews.value.findIndex(v => v.path === path)
    if (idx > -1) visitedViews.value.splice(idx, 1)
    // 返回删除后应该激活的视图
    const last = visitedViews.value[visitedViews.value.length - 1]
    return last?.path || '/'
  }

  const delOthers = (path: string) => {
    visitedViews.value = visitedViews.value.filter(
      v => v.path === '/' || v.path === path
    )
  }

  const delAll = () => {
    visitedViews.value = [{ path: '/', name: 'Home', title: '首页' }]
    return '/'
  }

  return { visitedViews, addView, delView, delOthers, delAll }
})
