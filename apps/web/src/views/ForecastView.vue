<script setup lang="ts">
import {
  createForecastJob,
  deleteForecastJob,
  getForecastJob,
  listForecastJobs,
  type ForecastJobSummary,
  type MultivariateResult,
  type UnivariateResult,
} from '@gozero-monorepo/api-client'
import { formatDateTime } from '@gozero-monorepo/shared-utils'
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import MultivariateResultPanel from '../components/forecast/MultivariateResultPanel.vue'
import UnivariateResultPanel from '../components/forecast/UnivariateResultPanel.vue'

type Tab = 'univariate' | 'multivariate'

const tab = ref<Tab>('univariate')
const epochs = reactive({ univariate: 20, multivariate: 30 })
const loggedIn = ref(false)
const running = ref(false)
const statusText = ref('')
const errorText = ref('')
const currentJobId = ref<string | null>(null)
const univariateResult = ref<UnivariateResult | null>(null)
const multivariateResult = ref<MultivariateResult | null>(null)
const history = ref<ForecastJobSummary[]>([])

let pollTimer: number | undefined

onMounted(async () => {
  loggedIn.value = Boolean(localStorage.getItem('token'))
  if (loggedIn.value) {
    await refreshHistory()
    await restoreLatest()
  }
})

onBeforeUnmount(stopPolling)

function stopPolling() {
  if (pollTimer !== undefined) {
    clearInterval(pollTimer)
    pollTimer = undefined
  }
}

async function refreshHistory() {
  try {
    const resp = await listForecastJobs()
    history.value = resp.jobs
  } catch {
    // 历史加载失败不阻塞主流程
  }
}

async function restoreLatest() {
  for (const job of history.value) {
    if (job.status === 'done' && job.has_result) {
      const detail = await getForecastJob(job.id)
      if (detail.result?.kind === 'univariate' && !univariateResult.value) {
        univariateResult.value = detail.result
      }
      if (detail.result?.kind === 'multivariate' && !multivariateResult.value) {
        multivariateResult.value = detail.result
      }
    }
  }
}

async function run() {
  errorText.value = ''
  statusText.value = '提交任务…'
  running.value = true
  try {
    const kind = tab.value
    const job = await createForecastJob({ kind, epochs: epochs[kind] })
    currentJobId.value = job.id
    await refreshHistory()
    startPolling()
  } catch (e) {
    running.value = false
    statusText.value = ''
    errorText.value = e instanceof Error ? e.message : String(e)
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    if (!currentJobId.value) return stopPolling()
    try {
      const detail = await getForecastJob(currentJobId.value)
      statusText.value = detail.status === 'running' ? detail.progress : detail.status
      if (detail.status === 'done' && detail.result) {
        if (detail.result.kind === 'univariate') {
          univariateResult.value = detail.result
        } else {
          multivariateResult.value = detail.result
        }
        running.value = false
        statusText.value = ''
        stopPolling()
        await refreshHistory()
      } else if (detail.status === 'failed') {
        running.value = false
        statusText.value = ''
        errorText.value = detail.error ?? '任务失败'
        stopPolling()
        await refreshHistory()
      }
    } catch (e) {
      stopPolling()
      running.value = false
      statusText.value = ''
      errorText.value = e instanceof Error ? e.message : String(e)
    }
  }, 2000)
}

async function openHistory(job: ForecastJobSummary) {
  if (!job.has_result) return
  const detail = await getForecastJob(job.id)
  if (!detail.result) return
  tab.value = detail.result.kind
  if (detail.result.kind === 'univariate') {
    univariateResult.value = detail.result
  } else {
    multivariateResult.value = detail.result
  }
}

async function removeHistory(job: ForecastJobSummary) {
  await deleteForecastJob(job.id)
  await refreshHistory()
}

function elapsed(job: ForecastJobSummary): string {
  if (!job.started_at || !job.finished_at) return '—'
  return ((job.finished_at - job.started_at) / 1000).toFixed(1) + 's'
}

const STATUS_LABEL: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  done: '完成',
  failed: '失败',
}
</script>

<template>
  <section v-if="!loggedIn" class="card">
    <h2>需要登录</h2>
    <p>时序预测系统的接口经网关鉴权保护，请先在首页登录（admin / admin123）。</p>
    <RouterLink to="/">前往登录</RouterLink>
  </section>

  <section v-else class="forecast">
    <header class="head">
      <div>
        <h1>时序预测与耦合失效检测系统</h1>
        <p class="sub">
          CNN（局部模式）+ Transformer（全局依赖）时间序列预测；多变量耦合失效检测对比
          多变量/单变量模型与 EWMA 基线。后端为 forecast-api（PyTorch CPU），
          结果与参考分析（seed=42）逐项比对。
        </p>
      </div>
    </header>

    <div class="tabs">
      <button :class="{ active: tab === 'univariate' }" @click="tab = 'univariate'">
        单变量时序预测
      </button>
      <button :class="{ active: tab === 'multivariate' }" @click="tab = 'multivariate'">
        多变量耦合失效检测
      </button>
    </div>

    <div class="controls card">
      <template v-if="tab === 'univariate'">
        <label>
          epochs
          <input v-model.number="epochs.univariate" type="number" min="1" max="200" :disabled="running" />
        </label>
        <span class="hint">与参考一致为 20（约 10–60s）</span>
      </template>
      <template v-else>
        <label>
          epochs
          <input v-model.number="epochs.multivariate" type="number" min="1" max="200" :disabled="running" />
        </label>
        <span class="hint">与参考一致为 30；两种故障模式顺序训练 6 个模型（约 2–5min）</span>
      </template>
      <button class="run" :disabled="running" @click="run">
        {{ running ? '运行中…' : '运行实验' }}
      </button>
      <span v-if="statusText" class="status">{{ statusText }}</span>
      <span v-if="errorText" class="error">{{ errorText }}</span>
    </div>

    <UnivariateResultPanel v-if="tab === 'univariate' && univariateResult" :result="univariateResult" />
    <MultivariateResultPanel
      v-if="tab === 'multivariate' && multivariateResult"
      :result="multivariateResult"
    />

    <div v-if="tab === 'univariate' && !univariateResult" class="card empty">
      尚无结果：点击「运行实验」训练模型并查看预测效果与参考比对。
    </div>
    <div v-if="tab === 'multivariate' && !multivariateResult" class="card empty">
      尚无结果：点击「运行实验」执行两模式（phase_swap / actuator_lag）检测实验。
    </div>

    <div v-if="history.length" class="card history">
      <h3>任务历史（服务内存保留最近 20 个）</h3>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>类型</th>
            <th>轮数</th>
            <th>状态</th>
            <th>耗时</th>
            <th>创建时间</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in history" :key="job.id">
            <td class="mono">{{ job.id }}</td>
            <td>{{ job.kind }}</td>
            <td class="mono">{{ job.params.epochs ?? '默认' }}</td>
            <td>
              <span :class="['tag', job.status]">{{ STATUS_LABEL[job.status] ?? job.status }}</span>
            </td>
            <td class="mono">{{ elapsed(job) }}</td>
            <td>{{ formatDateTime(job.created_at * 1000) }}</td>
            <td>
              <button class="link" :disabled="!job.has_result" @click="openHistory(job)">查看</button>
              <button
                class="link"
                :disabled="job.status === 'running' || job.status === 'queued'"
                @click="removeHistory(job)"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 8px;
  padding: 20px 24px;
}
.head h1 {
  margin: 0;
  font-size: 22px;
}
.sub {
  color: #57606a;
  font-size: 13px;
  margin: 8px 0 0;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}
.tabs button {
  padding: 9px 18px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  color: #57606a;
}
.tabs button.active {
  border-color: #1f6feb;
  color: #1f6feb;
  font-weight: 600;
}
.controls {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.controls label {
  font-size: 13px;
  color: #57606a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.controls input {
  width: 90px;
  padding: 7px 8px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
}
.hint {
  color: #6e7781;
  font-size: 12px;
}
.run {
  padding: 8px 22px;
  border: none;
  border-radius: 6px;
  background: #1f6feb;
  color: #fff;
  cursor: pointer;
}
.run:disabled {
  opacity: 0.55;
  cursor: default;
}
.status {
  color: #1f6feb;
  font-size: 13px;
}
.error {
  color: #cf222e;
  font-size: 13px;
}
.empty {
  margin-top: 16px;
  color: #6e7781;
}
.history {
  margin-top: 24px;
}
.history h3 {
  margin: 0 0 10px;
  font-size: 15px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th,
td {
  text-align: left;
  padding: 6px 10px;
  border-bottom: 1px solid #eef1f4;
}
th {
  color: #57606a;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.tag {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 999px;
}
.tag.done {
  background: #dafbe1;
  color: #116329;
}
.tag.failed {
  background: #ffebe9;
  color: #82071e;
}
.tag.running,
.tag.queued {
  background: #ddf4ff;
  color: #0969da;
}
.link {
  border: none;
  background: none;
  color: #1f6feb;
  cursor: pointer;
  padding: 0;
  margin-right: 10px;
  font-size: 13px;
}
.link:disabled {
  color: #aeaeae;
  cursor: default;
}
</style>
