<template>
  <div class="{{RESOURCE_NAME}}-list">
    <!-- 搜索栏 -->
    <el-form :inline="true" :model="queryForm" class="search-form">
      {{SEARCH_FIELDS}}
      <el-form-item>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
        <el-button type="primary" @click="handleCreate">新增</el-button>
      </el-form-item>
    </el-form>

    <!-- 数据表格 -->
    <el-table :data="tableData" v-loading="loading" border>
      {{TABLE_COLUMNS}}
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link @click="handleView(row)">查看</el-button>
          <el-button link @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.size"
      :total="pagination.total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handleSearch"
      @current-change="handleSearch"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { {{RESOURCE_NAME}}API } from '@/api/{{RESOURCE_NAME}}'

// 查询表单
const queryForm = reactive({
  {{QUERY_FIELDS_INIT}}
})

// 表格数据
const tableData = ref([])
const loading = ref(false)

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 查询
const handleSearch = async () => {
  loading.value = true
  try {
    const { data } = await {{RESOURCE_NAME}}API.list({
      ...queryForm,
      page: pagination.page - 1,
      size: pagination.size
    })
    tableData.value = data.content
    pagination.total = data.totalElements
  } finally {
    loading.value = false
  }
}

// 重置
const handleReset = () => {
  Object.assign(queryForm, {
    {{QUERY_FIELDS_RESET}}
  })
  handleSearch()
}

// 新增
const handleCreate = () => {
  // 跳转到新增页面
}

// 查看
const handleView = (row: any) => {
  // 跳转到查看页面
}

// 编辑
const handleEdit = (row: any) => {
  // 跳转到编辑页面
}

// 删除
const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除吗？', '提示', {
      type: 'warning'
    })
    await {{RESOURCE_NAME}}API.delete(row.id)
    ElMessage.success('删除成功')
    handleSearch()
  } catch (error) {
    // 用户取消
  }
}

onMounted(() => {
  handleSearch()
})
</script>

<style scoped>
.{{RESOURCE_NAME}}-list {
  padding: 20px;
}
.search-form {
  margin-bottom: 20px;
}
</style>
