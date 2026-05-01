function asText(value, fallback) {
  if (value === undefined || value === null || value === '') {
    return fallback || '-';
  }
  return String(value);
}

function asPercent(value) {
  const number = Number(value || 0);
  return `${Math.round(number * 100)}%`;
}

function chartItems(list, labelKey, valueKey, maxValue) {
  const values = (list || []).map((item) => Number(item[valueKey] || 0));
  const max = maxValue || Math.max.apply(null, values.concat([1]));
  return (list || []).map((item) => {
    const value = Number(item[valueKey] || 0);
    return {
      label: item[labelKey],
      value,
      width: Math.max(6, Math.round((value / max) * 100))
    };
  });
}

module.exports = {
  asText,
  asPercent,
  chartItems
};
