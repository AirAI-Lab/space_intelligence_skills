<template>
  <div class="tags-view">
    <router-link
      v-for="tag in tagsViewStore.visitedViews"
      :key="tag.path"
      :to="tag.path"
      class="tag-item"
      :class="{ active: isActive(tag.path) }"
      @contextmenu.prevent="openMenu($event, tag)"
    >
      <span>{{ tag.title }}</span>
      <el-icon
        v-if="tag.path !== '/'"
        :size="12"
        class="tag-close"
        @click.prevent.stop="closeTag(tag.path)"
      >
        <Close />
      </el-icon>
    </router-link>
    <!-- 右键菜单 -->
    <ul
      v-show="menuVisible"
      class="context-menu"
      :style="{ left: menuLeft + 'px', top: menuTop + 'px' }"
    >
      <li @click="refreshSelected">刷新</li>
      <li v-if="selectedTag?.path !== '/'" @click="closeSelected">关闭</li>
      <li @click="closeOthers">关闭其他</li>
      <li @click="closeAll">关闭所有</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Close } from '@element-plus/icons-vue'
import { useTagsViewStore, type TagView } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const tagsViewStore = useTagsViewStore()

const menuVisible = ref(false)
const menuLeft = ref(0)
const menuTop = ref(0)
const selectedTag = ref<TagView | null>(null)

const routeTitleMap: Record<string, string> = {
  '/': '首页',
  '/device': '设备管理',
  '/data': '数据管理',
  '/training': '训练管理',
  '/model': '模型管理',
  '/ota': 'OTA升级',
  '/deployment': '部署记录',
  '/inference': '推理结果',
  '/alerts': '告警中心',
  '/alert-rules': '告警规则',
  '/webhooks': 'Webhook'
}

const isActive = (path: string) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const addCurrentView = () => {
  const path = route.path
  // 详情页用列表路径
  const listPath = '/' + path.split('/')[1]
  const title = routeTitleMap[listPath] || routeTitleMap[path]
  if (title) {
    tagsViewStore.addView({
      path: listPath,
      name: route.name as string || listPath,
      title
    })
  }
}

const closeTag = (path: string) => {
  const nextPath = tagsViewStore.delView(path)
  if (isActive(path)) {
    router.push(nextPath)
  }
}

const openMenu = (e: MouseEvent, tag: TagView) => {
  selectedTag.value = tag
  menuLeft.value = e.clientX
  menuTop.value = e.clientY
  menuVisible.value = true
}

const closeMenu = () => {
  menuVisible.value = false
}

const refreshSelected = () => {
  closeMenu()
  router.go(0)
}

const closeSelected = () => {
  closeMenu()
  if (selectedTag.value) closeTag(selectedTag.value.path)
}

const closeOthers = () => {
  closeMenu()
  if (selectedTag.value) {
    tagsViewStore.delOthers(selectedTag.value.path)
    if (!isActive(selectedTag.value.path)) {
      router.push(selectedTag.value.path)
    }
  }
}

const closeAll = () => {
  closeMenu()
  const nextPath = tagsViewStore.delAll()
  router.push(nextPath)
}

watch(() => route.path, addCurrentView)
onMounted(addCurrentView)
onUnmounted(() => document.removeEventListener('click', closeMenu))
document.addEventListener('click', closeMenu)
</script>

<style scoped>
.tags-view {
  height: var(--tags-view-height);
  display: flex;
  align-items: center;
  padding: 0 12px;
  background: #fff;
  border-bottom: 1px solid var(--art-gray-300);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
  overflow-x: auto;
  white-space: nowrap;
  flex-shrink: 0;
}

.tags-view::-webkit-scrollbar {
  height: 0;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 12px;
  color: var(--art-gray-600);
  background: #fff;
  border: 1px solid var(--art-gray-300);
  border-radius: 6px;
  margin-right: 4px;
  text-decoration: none;
  cursor: pointer;
  height: 26px;
  line-height: 22px;
  transition: all 0.2s;
}

.tag-item:hover {
  color: var(--theme-color);
}

.tag-item.active {
  background-color: var(--theme-color);
  color: #fff;
  border-color: var(--theme-color);
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.3);
}

.tag-item.active .tag-close:hover {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
}

.tag-close {
  border-radius: 50%;
  transition: background 0.15s;
}

.tag-close:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.context-menu {
  position: fixed;
  z-index: 3000;
  background: #fff;
  border-radius: var(--custom-radius);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  padding: 6px;
  margin: 0;
  list-style: none;
}

.context-menu li {
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
  color: var(--art-gray-600);
  border-radius: 6px;
  transition: all 0.2s;
}

.context-menu li:hover {
  background: var(--theme-color-light-9);
  color: var(--theme-color);
}
</style>
