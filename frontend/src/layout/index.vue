<template>
  <el-config-provider :locale="zhCn">
    <el-container class="layout-container">
      <Sidebar />
      <el-container class="main-container">
        <Header />
        <TagsView />
        <el-main class="app-main">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>

<script setup lang="ts">
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import TagsView from './TagsView.vue'
</script>

<style scoped>
.layout-container {
  height: 100vh;
  overflow: hidden;
}

.main-container {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-main {
  background-color: var(--main-bg);
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}
</style>
