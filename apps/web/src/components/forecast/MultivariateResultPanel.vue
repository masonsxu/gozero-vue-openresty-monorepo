<script setup lang="ts">
import type { MultivariateResult } from '@gozero-monorepo/api-client'
import type { EChartsOption } from 'echarts'
import { computed, ref, watch } from 'vue'
import EChart from '../EChart.vue'
import ComparisonTable from './ComparisonTable.vue'

const props = defineProps<{ result: MultivariateResult }>()

const selectedMode = ref('phase_swap')
watch(
  () => props.result,
  () => {
    selectedMode.value = 'phase_swap'
  },
)

const modeResult = computed(() => props.result.modes[selectedMode.value])
const constants = computed(() => props.result.constants)
const corr = computed(() => modeResult.value.metrics.corr_a_b)
const marginal = computed(() => modeResult.value.metrics.b_marginal)

const METHOD_LABELS: Record<string, string> = {
  mv: '多变量 CNN+Transformer（B 通道评分）',
  uv_b: '单变量 B（仅 B 通道）',
  uv_a: '单变量 A（仅 A 通道）',
  ewma_a: 'EWMA 基线 A',
  ewma_b: 'EWMA 基线 B',
}
const methodRows = computed(() =>
  Object.entries(modeResult.value.metrics.methods).map(([key, stats]) => ({
    key,
    label: METHOD_LABELS[key] ?? key,
    ...stats,
  })),
)

type AreaMark = [{ xAxis: number }, { xAxis: number }]

const segments = computed<{ mark: AreaMark[]; color: string }[]>(() => {
  const { val_start, benign_start, fault_onset } = constants.value
  return [
    { mark: [[{ xAxis: 0 }, { xAxis: val_start }]], color: 'rgba(120,120,120,0.12)' },
    { mark: [[{ xAxis: benign_start }, { xAxis: fault_onset }]], color: 'rgba(50,205,50,0.18)' },
  ]
})

const channelsOption = computed<EChartsOption>(() => ({
  title: {
    text: `双通道数据流（${selectedMode.value}）`,
    left: 'center',
    fontSize: 14,
  },
  grid: { left: 56, right: 24, top: 52, bottom: 36 },
  tooltip: { trigger: 'axis' },
  legend: { top: 4, right: 8 },
  xAxis: { type: 'value', name: 't', min: 0, max: 3999 },
  yAxis: { type: 'value', scale: true },
  series: [
    {
      name: 'A (temp)',
      type: 'line',
      showSymbol: false,
      lineStyle: { color: 'teal', width: 1 },
      itemStyle: { color: 'teal' },
      data: modeResult.value.series.channels.t.map((t, i) => [
        t,
        modeResult.value.series.channels.a[i],
      ]),
      markArea: {
        silent: true,
        itemStyle: { color: segments.value[0].color },
        data: segments.value[0].mark,
      },
    },
    {
      name: 'B (bond force)',
      type: 'line',
      showSymbol: false,
      lineStyle: { color: 'deeppink', width: 1 },
      itemStyle: { color: 'deeppink' },
      data: modeResult.value.series.channels.t.map((t, i) => [
        t,
        modeResult.value.series.channels.b[i],
      ]),
      markLine: {
        symbol: 'none',
        silent: true,
        lineStyle: { color: 'red', type: 'dashed', width: 1.5 },
        data: [{ xAxis: constants.value.fault_onset }],
      },
      markArea: {
        silent: true,
        itemStyle: { color: segments.value[1].color },
        data: segments.value[1].mark,
      },
    },
  ],
}))

const scoresOption = computed<EChartsOption>(() => {
  const th = modeResult.value.thresholds
  const t = modeResult.value.series.scores.t
  const sc = modeResult.value.series.scores
  return {
    title: { text: '模型异常评分（平滑平方误差，对数轴）', left: 'center', fontSize: 14 },
    grid: { left: 56, right: 24, top: 52, bottom: 36 },
    tooltip: { trigger: 'axis' },
    legend: { top: 4, right: 8 },
    xAxis: { type: 'value', name: 't', min: 0, max: 3999 },
    yAxis: { type: 'log', min: 1e-4, name: 'score' },
    series: [
      {
        name: 'multivariate score',
        type: 'line',
        showSymbol: false,
        lineStyle: { color: 'magenta', width: 1.2 },
        itemStyle: { color: 'magenta' },
        data: t.map((x, i) => [x, sc.mv[i]]),
        markLine: {
          symbol: 'none',
          silent: true,
          lineStyle: { color: 'magenta', type: 'dashed' },
          data: [{ yAxis: th.mv }],
        },
      },
      {
        name: 'univariate-B score',
        type: 'line',
        showSymbol: false,
        lineStyle: { color: 'darkorange', width: 1.2, opacity: 0.9 },
        itemStyle: { color: 'darkorange' },
        data: t.map((x, i) => [x, sc.uv_b[i]]),
        markLine: {
          symbol: 'none',
          silent: true,
          lineStyle: { color: 'darkorange', type: 'dashed' },
          data: [{ yAxis: th.uv_b }],
        },
      },
    ],
  }
})

const ewmaOption = computed<EChartsOption>(() => {
  const th = modeResult.value.thresholds
  const t = modeResult.value.series.scores.t
  const sc = modeResult.value.series.scores
  return {
    title: { text: 'EWMA 基线评分（|EWMA|，经验阈值）', left: 'center', fontSize: 14 },
    grid: { left: 56, right: 24, top: 52, bottom: 36 },
    tooltip: { trigger: 'axis' },
    legend: { top: 4, right: 8 },
    xAxis: { type: 'value', name: 't', min: 0, max: 3999 },
    yAxis: { type: 'value', name: '|EWMA|' },
    series: [
      {
        name: '|EWMA| A',
        type: 'line',
        showSymbol: false,
        lineStyle: { color: 'teal', width: 1 },
        itemStyle: { color: 'teal' },
        data: t.map((x, i) => [x, sc.ewma_a[i]]),
      },
      {
        name: '|EWMA| B',
        type: 'line',
        showSymbol: false,
        lineStyle: { color: 'slateblue', width: 1 },
        itemStyle: { color: 'slateblue' },
        data: t.map((x, i) => [x, sc.ewma_b[i]]),
        markLine: {
          symbol: 'none',
          silent: true,
          lineStyle: { color: 'black', type: 'dashed' },
          data: [{ yAxis: th.ewma_b }],
        },
      },
    ],
  }
})

const couplingOption = computed<EChartsOption>(() => {
  const c = modeResult.value.series.coupling
  return {
    title: {
      text: '耦合劣化：A-B 互相关（训练段 vs 故障段）',
      left: 'center',
      fontSize: 14,
    },
    grid: { left: 64, right: 24, top: 52, bottom: 44 },
    tooltip: {},
    legend: { top: 4, right: 8 },
    xAxis: { type: 'value', name: 'A (temp)' },
    yAxis: { type: 'value', name: 'B (bond force)', scale: true },
    series: [
      {
        name: `train: corr=${corr.value.train}`,
        type: 'scatter',
        symbolSize: 4,
        itemStyle: { color: 'teal', opacity: 0.4 },
        data: c.train.a.map((a, i) => [a, c.train.b[i]]),
      },
      {
        name: `post-onset: corr=${corr.value.post_onset}`,
        type: 'scatter',
        symbolSize: 4,
        itemStyle: { color: 'crimson', opacity: 0.4 },
        data: c.post.a.map((a, i) => [a, c.post.b[i]]),
      },
    ],
  }
})
</script>

<template>
  <div class="multivariate">
    <div class="mode-tabs">
      <button
        v-for="mode in Object.keys(result.modes)"
        :key="mode"
        :class="['mode-tab', { active: mode === selectedMode }]"
        @click="selectedMode = mode"
      >
        {{ mode === 'phase_swap' ? 'phase_swap（相位切换：边际不变，互相关消失）' : 'actuator_lag（执行器延迟：波形不变，响应滞后）' }}
      </button>
    </div>

    <div class="cards">
      <div class="metric-card">
        <span class="k">corr(A,B) 训练段</span>
        <span class="v mono">{{ corr.train }}</span>
      </div>
      <div class="metric-card">
        <span class="k">corr(A,B) 良性段</span>
        <span class="v mono">{{ corr.benign }}</span>
      </div>
      <div class="metric-card">
        <span class="k">corr(A,B) 故障段</span>
        <span class="v mono">{{ corr.post_onset }}</span>
      </div>
      <div class="metric-card">
        <span class="k">B 边际（均值 前段→故障段）</span>
        <span class="v mono">{{ marginal.pre_mean }} → {{ marginal.post_mean }}</span>
      </div>
      <div class="metric-card">
        <span class="k">B 边际（标准差 前段→故障段）</span>
        <span class="v mono">{{ marginal.pre_std }} → {{ marginal.post_std }}</span>
      </div>
    </div>

    <div class="card table-card">
      <h3>各方法异常检测对照（阈值 = 验证段 99.5% 分位）</h3>
      <table>
        <thead>
          <tr>
            <th>方法</th>
            <th>验证段报警率</th>
            <th>良性段报警率（越低越好）</th>
            <th>故障段报警率（越高越好）</th>
            <th>检出延迟（步）</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in methodRows" :key="row.key" :class="{ best: row.key === 'mv' }">
            <td>{{ row.label }}</td>
            <td class="mono">{{ row.val_alarm_rate }}</td>
            <td class="mono">{{ row.benign_alarm_rate }}</td>
            <td class="mono">{{ row.fault_alarm_rate }}</td>
            <td class="mono">{{ row.detection_delay ?? '未检出' }}</td>
          </tr>
        </tbody>
      </table>
      <p class="note">
        时间轴：[0, {{ constants.val_start }}) 训练 · [{{ constants.val_start }},
        {{ constants.benign_start }}) 验证 · [{{ constants.benign_start }},
        {{ constants.fault_onset }}) 良性对照 · [{{ constants.fault_onset }}, 4000] 故障（{{
          constants.ramp
        }}
        步渐变）；EWMA λ={{ constants.ewma_lambda }}，平滑窗 {{ constants.smooth }}
      </p>
    </div>

    <div class="card"><EChart :option="channelsOption" height="340px" /></div>
    <div class="card"><EChart :option="scoresOption" height="340px" /></div>
    <div class="grid2">
      <div class="card"><EChart :option="ewmaOption" height="300px" /></div>
      <div class="card"><EChart :option="couplingOption" height="300px" /></div>
    </div>

    <ComparisonTable
      :source="result.comparison.reference_source"
      :epochs-match="result.comparison.epochs_match"
      :checks="result.comparison.modes[selectedMode].checks"
      :passed="result.comparison.modes[selectedMode].passed"
    />
  </div>
</template>

<style scoped>
.mode-tabs {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.mode-tab {
  padding: 8px 14px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  color: #57606a;
}
.mode-tab.active {
  border-color: #1f6feb;
  color: #1f6feb;
  font-weight: 600;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-top: 16px;
}
.metric-card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 8px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.metric-card .k {
  color: #6e7781;
  font-size: 13px;
}
.metric-card .v {
  font-size: 17px;
  font-weight: 600;
}
.card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
}
.grid2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
@media (max-width: 900px) {
  .grid2 {
    grid-template-columns: 1fr;
  }
}
h3 {
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
tr.best td {
  background: #f3f8ff;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.note {
  color: #6e7781;
  font-size: 12px;
  margin: 10px 0 0;
}
</style>
