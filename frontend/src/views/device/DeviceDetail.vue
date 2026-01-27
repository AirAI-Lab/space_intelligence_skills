<template>
  <div class="device-detail">
    <h2>设备详情</h2>
    <p>设备ID: {{ deviceId }}</p>
    <el-button @click="goBack">返回</el-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const deviceId = computed(() => route.params.id as string)

const goBack = () => {
  router.back()
}
</script>

<style scoped>
.device-detail {
  padding: 20px;
}
</style>
