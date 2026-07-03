<template>
  <div class="tasks-page">
    <h2>任务管理</h2>

    <!-- 提交表单（不变） -->
    <el-card style="margin-bottom:20px">
      <template #header>提交新任务</template>
      <el-form :model="form" inline>
        <el-form-item label="任务类型">
          <el-select v-model="form.task_type" @change="onTypeChange" style="width:150px">
            <el-option v-for="a in abilities" :key="a.key" :label="a.name" :value="a.key" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="currentConfig.inputType === 'image'" label="上传图片">
          <el-upload :auto-upload="false" :limit="1" :on-change="onFileChange"
            :file-list="fileList" list-type="picture" :accept="currentConfig.accept">
            <el-button type="primary" :icon="Upload">选择图片</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item v-if="currentConfig.inputType === 'text'" style="flex:1">
          <el-input v-model="form.text_input" :placeholder="currentConfig.placeholder"
            style="width:400px" @keyup.enter="submitTask" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submitTask">提交任务</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 — 卡片式 -->
    <el-row :gutter="16">
      <el-col :span="8" v-for="t in tasks" :key="t.id" style="margin-bottom:16px">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <!-- 头部：ID + 类型 + 状态 -->
          <div class="card-head">
            <span class="card-id">#{{ t.id }}</span>
            <el-tag size="small" :type="statusType(t.status)">{{ t.status_display }}</el-tag>
            <span class="card-type">{{ t.task_type_display }}</span>
          </div>

          <!-- 输入预览 -->
          <div class="card-input" v-if="t.text_input">
            <el-text truncated>{{ t.text_input }}</el-text>
          </div>
          <div class="card-image" v-if="t.image">
            <el-image :src="t.image" fit="cover" style="width:100%;height:120px;border-radius:6px" />
          </div>

          <!-- 结果面板 -->
          <div v-if="t.status === 'completed'" class="card-result">
            <!-- 文本摘要 -->
            <template v-if="t.task_type === 'text_summary'">
              <div class="result-summary">{{ t.result?.summary || '—' }}</div>
              <div class="result-meta">
                <span>📝 {{ t.result?.word_count || 0 }} 词</span>
                <el-progress :percentage="(t.result?.confidence || 0) * 100" :stroke-width="6"
                  style="width:120px;margin-left:8px" />
              </div>
            </template>

            <!-- 文本生成 -->
            <template v-else-if="t.task_type === 'text_generation'">
              <div class="result-text">{{ t.result?.generated_text || '—' }}</div>
              <div class="result-meta">🪙 {{ t.result?.tokens || 0 }} tokens</div>
            </template>

            <!-- 图像识别 -->
            <template v-else-if="t.task_type === 'image_classify'">
              <div v-for="p in (t.result?.predictions || [])" :key="p.label" class="predict-item">
                <span class="predict-label">{{ p.label }}</span>
                <el-progress :percentage="(p.confidence || 0) * 100" :stroke-width="8"
                  :color="p === t.result?.predictions?.[0] ? '#67C23A' : '#909399'" style="flex:1;margin:0 8px" />
                <span class="predict-score">{{ ((p.confidence || 0) * 100).toFixed(1) }}%</span>
              </div>
            </template>

            <!-- 图像生成 -->
            <template v-else-if="t.task_type === 'image_generate'">
              <el-image v-if="t.result?.image_url" :src="t.result.image_url" fit="cover"
                style="width:100%;height:150px;border-radius:6px" />
              <div class="result-meta">🎲 seed: {{ t.result?.seed }}</div>
            </template>

            <!-- 代码生成 -->
            <template v-else-if="t.task_type === 'code_generate'">
              <div class="code-block">{{ t.result?.code || '—' }}</div>
            </template>

            <!-- 未知类型 → JSON -->
            <template v-else>
              <div class="result-json">{{ JSON.stringify(t.result, null, 1) }}</div>
            </template>
          </div>

          <!-- 失败 -->
          <el-alert v-if="t.status === 'failed'" type="error" :title="t.error_message"
            :closable="false" style="margin-top:8px" />

          <!-- 处理中 -->
          <div v-if="t.status === 'pending' || t.status === 'processing'" class="card-waiting">
            <el-icon class="is-loading"><Loading /></el-icon> {{ t.status_display }}...
          </div>

          <!-- 底部：时间 + 重试 -->
          <div class="card-foot">
            <span class="card-time">{{ fmt(t.created_at) }}</span>
            <el-button v-if="t.status==='failed'" type="warning" size="small" @click="retryTask(t.id)">重试</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="tasks.length === 0 && !loading" description="暂无任务" />
    <el-pagination v-if="total > 20" layout="prev, pager, next" :total="total" :page-size="20"
      @current-change="loadTasks" style="margin-top:16px; justify-content:center" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Loading } from '@element-plus/icons-vue'
import api from '../api'
import { resolveAbility } from '../config/abilities'

const tasks = ref<any[]>([])
const abilities = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const selectedFile = ref<File | null>(null)
const fileList = ref<any[]>([])
const form = reactive({ task_type: 'text_summary', text_input: '' })

const currentConfig = computed(() => resolveAbility(form.task_type))
function onTypeChange() { form.text_input = ''; selectedFile.value = null; fileList.value = [] }
function onFileChange(f: any) { selectedFile.value = f.raw; fileList.value = [f] }

onMounted(async () => {
  const [ab, ts] = await Promise.all([api.get('/abilities/'), api.get('/tasks/?page=1')])
  abilities.value = ab.data
  tasks.value = ts.data.results ?? ts.data
  total.value = ts.data.count ?? tasks.value.length
})

async function loadTasks(p = 1) {
  loading.value = true
  const { data } = await api.get(`/tasks/?page=${p}`)
  tasks.value = data.results ?? data
  loading.value = false
}

async function submitTask() {
  const cfg = currentConfig.value
  if (cfg.inputType === 'image' && !selectedFile.value) { ElMessage.warning('请选择图片'); return }
  if (cfg.inputType === 'text' && !form.text_input.trim()) { ElMessage.warning('请输入内容'); return }
  submitting.value = true
  try {
    let resp
    if (cfg.inputType === 'image') {
      const fd = new FormData()
      fd.append('task_type', form.task_type)
      fd.append('image', selectedFile.value!)
      resp = await api.post('/tasks/', fd)
    } else {
      resp = await api.post('/tasks/', form)
    }
    tasks.value.unshift(resp.data)
    form.text_input = ''
    selectedFile.value = null
    fileList.value = []
    ElMessage.success(`任务 #${resp.data.id} ${resp.data.status_display}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally { submitting.value = false }
}

async function retryTask(id: number) {
  await api.post(`/tasks/${id}/retry/`)
  await loadTasks()
  ElMessage.success('已重试')
}

const statusType = (s: string) => ({ completed: 'success', failed: 'danger', processing: 'warning', pending: 'info' } as any)[s] || 'info'
const fmt = (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'
</script>

<style scoped>
.tasks-page h2 { margin-bottom: 16px }
.card-head { display:flex; align-items:center; gap:8px; margin-bottom:8px }
.card-id { font-weight:bold; color:#409EFF }
.card-type { font-size:12px; color:#999; margin-left:auto }
.card-input { margin:8px 0; color:#666; font-size:13px }
.card-image { margin:8px 0 }
.result-summary { font-size:14px; line-height:1.6; color:#333; margin:8px 0 }
.result-text { font-size:13px; line-height:1.6; color:#333; margin:8px 0; max-height:80px; overflow:hidden }
.result-meta { display:flex; align-items:center; gap:8px; font-size:12px; color:#999; margin-top:6px }
.predict-item { display:flex; align-items:center; margin:4px 0 }
.predict-label { width:50px; font-size:13px; font-weight:500 }
.predict-score { font-size:12px; color:#666; width:45px; text-align:right }
.code-block { background:#1e1e1e; color:#d4d4d4; padding:8px; border-radius:4px; font-size:12px; font-family:monospace; max-height:100px; overflow:auto; margin:8px 0 }
.result-json { font-size:11px; color:#666; max-height:100px; overflow:auto; margin:8px 0 }
.card-waiting { text-align:center; padding:16px; color:#999 }
.card-foot { display:flex; justify-content:space-between; align-items:center; margin-top:10px; padding-top:8px; border-top:1px solid #eee }
.card-time { font-size:11px; color:#bbb }
</style>
