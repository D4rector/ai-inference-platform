<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>AI 推理平台</h2>
      <el-tabs v-model="tab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form ref="loginFormRef" :model="loginForm" :rules="rules">
            <el-form-item prop="username">
              <el-input v-model="loginForm.username" placeholder="用户名" prefix-icon="User" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="密码" prefix-icon="Lock" show-password />
            </el-form-item>
            <el-button type="primary" :loading="loading" @click="handleLogin" class="submit-btn">
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form ref="regFormRef" :model="regForm" :rules="regRules">
            <el-form-item prop="username">
              <el-input v-model="regForm.username" placeholder="用户名" />
            </el-form-item>
            <el-form-item prop="email">
              <el-input v-model="regForm.email" placeholder="邮箱" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="regForm.password" type="password" placeholder="密码" show-password />
            </el-form-item>
            <el-button type="success" :loading="regLoading" @click="handleRegister" class="submit-btn">
              注 册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()
const tab = ref('login')
const loading = ref(false)
const regLoading = ref(false)

const loginForm = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const regForm = reactive({ username: '', email: '', password: '' })
const regRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入有效邮箱', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

async function handleLogin() {
  loading.value = true
  try {
    await auth.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  regLoading.value = true
  try {
    await auth.register(regForm.username, regForm.password, regForm.email)
    ElMessage.success('注册成功，请登录')
    tab.value = 'login'
    loginForm.username = regForm.username
  } catch (e: any) {
    const err = e.response?.data
    const msg = typeof err === 'object' ? Object.values(err).flat().join(', ') : (err?.detail || '注册失败')
    ElMessage.error(msg)
  } finally {
    regLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  padding: 20px;
}
.login-card h2 {
  text-align: center;
  color: #333;
  margin-bottom: 24px;
}
.submit-btn {
  width: 100%;
}
</style>
