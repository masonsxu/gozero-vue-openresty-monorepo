<script setup lang="ts">
import type { ComparisonCheck } from '@gozero-monorepo/api-client'
import { computed } from 'vue'

const props = defineProps<{
  source: string
  epochsMatch?: boolean
  checks: Record<string, ComparisonCheck>
  passed: boolean
}>()

const rows = computed(() =>
  Object.entries(props.checks).map(([key, check]) => ({
    key,
    ...check,
    deltaText:
      check.delta === null ? '—' : (check.delta >= 0 ? '+' : '') + check.delta.toFixed(4),
    actualText: check.actual === null ? '未检出' : String(check.actual),
    referenceText: check.reference === null ? '未检出' : String(check.reference),
  })),
)
</script>

<template>
  <div class="comparison card">
    <div class="head">
      <h3>与参考分析结果的一致性比对</h3>
      <span :class="['badge', passed ? 'ok' : 'bad']">
        {{ passed ? '全部一致' : '存在超差项' }}
      </span>
    </div>
    <p class="source">{{ source }}</p>
    <p v-if="epochsMatch === false" class="warn">
      注意：本次运行轮数与参考不同，比对结果仅供参考；使用默认轮数可获得一致结果。
    </p>
    <table>
      <thead>
        <tr>
          <th>指标</th>
          <th>本系统</th>
          <th>参考值</th>
          <th>Δ</th>
          <th>结果</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.key">
          <td class="mono">{{ row.key }}</td>
          <td class="mono">{{ row.actualText }}</td>
          <td class="mono">{{ row.referenceText }}</td>
          <td class="mono" :class="{ bad: !row.within_tolerance }">{{ row.deltaText }}</td>
          <td>
            <span :class="['tag', row.within_tolerance ? 'ok' : 'bad']">
              {{ row.within_tolerance ? '通过' : '超差' }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 8px;
  padding: 20px 24px;
  margin-top: 20px;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
h3 {
  margin: 0;
  font-size: 16px;
}
.source {
  color: #6e7781;
  font-size: 12px;
  margin: 6px 0 12px;
}
.warn {
  color: #9a6700;
  background: #fff8c5;
  border: 1px solid #d4a72c66;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
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
  font-weight: 600;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.bad {
  color: #cf222e;
}
.badge {
  font-size: 13px;
  padding: 3px 10px;
  border-radius: 999px;
}
.badge.ok,
.tag.ok {
  background: #dafbe1;
  color: #116329;
}
.badge.bad,
.tag.bad {
  background: #ffebe9;
  color: #82071e;
}
.tag {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 999px;
}
</style>
