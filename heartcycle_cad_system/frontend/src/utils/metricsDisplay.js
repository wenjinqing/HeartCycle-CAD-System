/**
 * 训练结果 metrics 展示约定：
 * - `accuracy.mean` 等为 K 折交叉验证的折均值，反映泛化能力，宜作为主展示。
 * - `final_accuracy` 等为在全量（常含 SMOTE）训练集上重拟合后的样本内指标，易过拟合、常偏高，仅作参考。
 */

function isValidNumber(v) {
  return typeof v === 'number' && !Number.isNaN(v)
}

/**
 * @param {Record<string, any>|null|undefined} metrics
 * @param {'accuracy'|'precision'|'recall'|'f1'|'roc_auc'} cvKey
 * @param {'final_accuracy'|'final_precision'|'final_recall'|'final_f1'|'final_roc_auc'} finalKey
 * @returns {number|null}
 */
export function primaryMetric(metrics, cvKey, finalKey) {
  if (!metrics) return null
  const block = metrics[cvKey]
  if (block && isValidNumber(block.mean)) return block.mean
  const f = metrics[finalKey]
  if (isValidNumber(f)) return f
  return null
}
