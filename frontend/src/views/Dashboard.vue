<template>
  <div class="dashboard">
    <h2>仪表盘</h2>
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="s in stats" :key="s.label">
        <el-card shadow="hover">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <h3 style="margin-top:24px">最近任务</h3>
    <el-table :data="recentTasks" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="task_type_display" label="任务类型" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status_display }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="text_input" label="输入" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'

interface Stat { label: string; value: number | string; key: string }

const stats = ref<Stat[]>([])
const recentTasks = ref<any[]>([])

onMounted(async () => {
  const { data } = await api.get('/tasks/dashboard/')
  stats.value = [
    { label: '今日任务', value: data.today_tasks, key: '' },
    { label: '总任务数', value: data.total_tasks, key: '' },
    { label: '已完成', value: data.completed_tasks, key: '' },
    { label: '平均耗时(s)', value: data.avg_duration_seconds, key: '' },
  ]
  recentTasks.value = data.recent_tasks
})

function statusType(status: string) {
  const map: Record<string, string> = {
    completed: 'success', failed: 'danger', processing: 'warning', pending: 'info',
  }
  return map[status] || 'info'
}

function formatTime(t: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style scoped>
.dashboard h2 { margin-bottom: 16px; }
.stat-value { font-size: 32px; font-weight: bold; color: #409EFF; }
.stat-label { color: #999; margin-top: 4px; }
</style>
