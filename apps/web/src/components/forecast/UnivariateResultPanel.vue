<script setup lang="ts">
import type { UnivariateResult } from '@gozero-monorepo/api-client'
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'
import EChart from '../EChart.vue'
import ComparisonTable from './ComparisonTable.vue'

const props = defineProps<{ result: UnivariateResult }>()

const m = computed(() => props.result.metrics)
const s = computed(() => props.result.series)

const rawOption = computed<EChartsOption>(() => ({
  title: { text: '原始时间序列（趋势 + 双周期 + 突变 + 噪声）', left: 'center', fontSize: 14 },
  grid: { left: 56, right: 24, top: 44, bottom: 36 },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'value', name: 't', min: 0, max: 1999 },
  yAxis: { type: 'value', scale: true },
  series: [
    {
      type: 'line',
      showSymbol: false,
      itemStyle: { color: 'deeppink' },
      lineStyle: { width: 1.5, color: 'deeppink' },
      data: s.value.raw.t.map((t, i) => [t, s.value.raw.value[i]]),
    },
  ],
}))

const lossOption = computed<EChartsOption>(() => ({
  title: { text: '训练/测试损失曲线（MSE，标准化空间）', left: 'center', fontSize: 14 },
  grid: { left: 64, right: 24, top: 44, bottom: 36 },
  tooltip: { trigger: 'axis' },
  legend: { top: 4, right: 8 },
  xAxis: { type: 'category', name: 'epoch', data: s.value.loss.epoch.map(String) },
  yAxis: { type: 'value', scale: true },
  series: [
    {
      name: 'Train Loss',
      type: 'line',
      itemStyle: { color: 'cyan' },
      lineStyle: { color: 'cyan', width: 2 },
      data: s.value.loss.train,
    },
    {
      name: 'Test Loss',
      type: 'line',
      itemStyle: { color: 'orange' },
      lineStyle: { color: 'orange', width: 2 },
      data: s.value.loss.test,
    },
  ],
}))

const predictionOption = computed<EChartsOption>(() => ({
  title: { text: '预测值 vs 真实值（测试集前 200 个样本，反标准化）', left: 'center', fontSize: 14 },
  grid: { left: 56, right: 24, top: 44, bottom: 36 },
  tooltip: { trigger: 'axis' },
  legend: { top: 4, right: 8 },
  xAxis: { type: 'value', name: 'sample', min: 0, max: 199 },
  yAxis: { type: 'value', scale: true },
  series: [
    {
      name: 'True',
      type: 'line',
      showSymbol: false,
      itemStyle: { color: 'lime' },
      lineStyle: { color: 'lime', width: 2 },
      data: s.value.prediction.sample.map((n, i) => [n, s.value.prediction.true[i]]),
    },
    {
      name: 'Predicted',
      type: 'line',
      showSymbol: false,
      itemStyle: { color: 'magenta' },
      lineStyle: { color: 'magenta', width: 2 },
      data: s.value.prediction.sample.map((n, i) => [n, s.value.prediction.pred[i]]),
    },
  ],
}))

const residualOption = computed<EChartsOption>(() => {
  const centers = s.value.residual_histogram.bin_left.map(
    (l, i) => (l + s.value.residual_histogram.bin_right[i]) / 2,
  )
  return {
    title: { text: '残差分布（真实 − 预测，反标准化）', left: 'center', fontSize: 14 },
    grid: { left: 56, right: 24, top: 44, bottom: 36 },
    tooltip: {},
    xAxis: {
      type: 'category',
      name: 'residual',
      data: centers.map((c) => c.toFixed(2)),
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value', name: 'count' },
    series: [
      {
        type: 'bar',
        itemStyle: { color: 'dodgerblue' },
        data: s.value.residual_histogram.counts,
      },
    ],
  }
})

const scatterOption = computed<EChartsOption>(() => {
  const limMin = Math.min(...s.value.scatter.actual)
  const limMax = Math.max(...s.value.scatter.actual)
  return {
    title: { text: '预测-真实散点（对角线为理想预测）', left: 'center', fontSize: 14 },
    grid: { left: 56, right: 24, top: 44, bottom: 40 },
    tooltip: {},
    xAxis: { type: 'value', name: 'Actual', min: limMin, max: limMax },
    yAxis: { type: 'value', name: 'Predicted', scale: true },
    series: [
      {
        type: 'scatter',
        symbolSize: 5,
        itemStyle: { color: '#5470c6', opacity: 0.7 },
        data: s.value.scatter.actual.map((a, i) => [a, s.value.scatter.predicted[i]]),
        markLine: {
          symbol: 'none',
          silent: true,
          lineStyle: { color: '#333', type: 'dashed', width: 2 },
          data: [[{ coord: [limMin, limMin] }, { coord: [limMax, limMax] }]],
        },
      },
    ],
  }
})

const metricRows = computed(() => {
  const rows = [
    { name: 'MAE', ...m.value.model_inverse },
    { name: 'RMSE', ...m.value.model_inverse },
    { name: 'R2', ...m.value.model_inverse },
  ]
  return rows.map((r) => ({
    name: r.name,
    model: m.value.model_inverse[r.name as 'MAE' | 'RMSE' | 'R2'],
    persistence: m.value.persistence_inverse[r.name as 'MAE' | 'RMSE' | 'R2'],
  }))
})
</script>

<template>
  <div class="univariate">
    <div class="cards">
      <div class="metric-card">
        <span class="k">模型参数量</span>
        <span class="v">{{ m.params.toLocaleString() }}</span>
      </div>
      <div class="metric-card">
        <span class="k">训练/测试样本</span>
        <span class="v">{{ m.train_samples }} / {{ m.test_samples }}</span>
      </div>
      <div class="metric-card">
        <span class="k">最终 MSE（标准化）</span>
        <span class="v">train {{ m.train_mse_scaled }} · test {{ m.test_mse_scaled }}</span>
      </div>
      <div class="metric-card">
        <span class="k">训练耗时</span>
        <span class="v">{{ m.train_seconds }}s（{{ m.device }}）</span>
      </div>
    </div>

    <div class="card table-card">
      <h3>回归指标（反标准化空间）：模型 vs 持久性基线</h3>
      <table>
        <thead>
          <tr>
            <th>指标</th>
            <th>CNN+Transformer</th>
            <th>持久性基线（复用上一时刻值）</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in metricRows" :key="row.name">
            <td>{{ row.name }}</td>
            <td class="mono">{{ row.model }}</td>
            <td class="mono">{{ row.persistence }}</td>
          </tr>
        </tbody>
      </table>
      <p class="note">
        残差 mean={{ m.residual.mean }}，std={{ m.residual.std }}；seed={{ result.seed }}，
        epochs={{ result.epochs }}，torch={{ result.torch_version }}
      </p>
    </div>

    <div class="grid2">
      <div class="card"><EChart :option="rawOption" height="300px" /></div>
      <div class="card"><EChart :option="lossOption" height="300px" /></div>
      <div class="card"><EChart :option="predictionOption" height="300px" /></div>
      <div class="card"><EChart :option="residualOption" height="300px" /></div>
    </div>
    <div class="card center"><EChart :option="scatterOption" height="380px" /></div>

    <ComparisonTable
      :source="result.comparison.reference_source"
      :epochs-match="result.comparison.epochs_match"
      :checks="result.comparison.checks"
      :passed="result.comparison.passed"
    />
  </div>
</template>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
  font-variant-numeric: tabular-nums;
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
.grid2 .card {
  margin-top: 0;
}
.grid2 {
  margin-top: 16px;
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
  font-size: 14px;
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
.note {
  color: #6e7781;
  font-size: 12px;
  margin: 10px 0 0;
}
</style>
