<template>
  <div class="models-page">
    <h2>模型管理</h2>
    <el-row :gutter="20">
      <el-col :span="8" v-for="m in models" :key="m.id">
        <el-card shadow="hover" class="model-card">
          <template #header>
            <div class="model-header">
              <span class="model-name">{{ m.name }}</span>
              <el-tag size="small" :type="m.is_active ? 'success' : 'info'">
                {{ m.is_active ? '启用' : '停用' }}
              </el-tag>
            </div>
          </template>
          <p><strong>版本：</strong>{{ m.version }}</p>
          <p><strong>任务类型：</strong>{{ m.task_type }}</p>
          <p class="desc">{{ m.description }}</p>
          <p class="time">注册时间：{{ fmt(m.created_at) }}</p>
        </el-card>
      </el-col>
    </el-row>
    <el-empty v-if="models.length===0" description="暂无注册模型" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'

const models = ref<any[]>([])

onMounted(async () => {
  const { data } = await api.get('/models/')
  models.value = data.results ?? data
})

function fmt(t: string) { return t ? new Date(t).toLocaleString('zh-CN') : '-' }
</script>

<style scoped>
.model-card { margin-bottom: 16px; }
.model-header { display: flex; justify-content: space-between; align-items: center; }
.model-name { font-weight: bold; font-size: 16px; }
.desc { color: #666; font-size: 14px; margin-top: 8px; }
.time { color: #999; font-size: 12px; margin-top: 4px; }
</style>
