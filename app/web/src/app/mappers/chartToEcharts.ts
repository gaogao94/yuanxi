import type { EChartsOption } from "echarts";

import type { ApiChartPayload } from "../types/api";

function buildBarOption(chart: ApiChartPayload): EChartsOption {
  const [primarySeries, benchmarkSeries] = chart.series;

  return {
    animation: false,
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#ffffff",
      borderColor: "#e5e7eb",
      borderWidth: 1,
      textStyle: { color: "#111827", fontSize: 12 },
    },
    legend: {
      top: 0,
      textStyle: { color: "#6b7280", fontSize: 11 },
    },
    grid: {
      top: 36,
      right: 12,
      bottom: 20,
      left: 24,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: chart.categories,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#6b7280", fontSize: 11 },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "#f3f4f6", type: "dashed" } },
      axisLabel: { color: "#6b7280", fontSize: 11 },
    },
    series: [
      {
        name: primarySeries?.name ?? "指标",
        type: "bar",
        barMaxWidth: 28,
        data: primarySeries?.data ?? [],
        itemStyle: {
          color: "#1d4ed8",
          borderRadius: [6, 6, 0, 0],
        },
      },
      ...(benchmarkSeries
        ? [
            {
              name: benchmarkSeries.name,
              type: "line",
              data: benchmarkSeries.data,
              symbol: "none",
              lineStyle: {
                color: "#f97316",
                type: "dashed",
                width: 2,
              },
            },
          ]
        : []),
    ],
  };
}

function buildLineOption(chart: ApiChartPayload): EChartsOption {
  const [primarySeries] = chart.series;

  return {
    animation: false,
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: "#e5e7eb",
      borderWidth: 1,
      textStyle: { color: "#111827", fontSize: 12 },
    },
    grid: {
      top: 24,
      right: 12,
      bottom: 20,
      left: 24,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: chart.categories,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#6b7280", fontSize: 11 },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "#f3f4f6", type: "dashed" } },
      axisLabel: { color: "#6b7280", fontSize: 11 },
    },
    series: [
      {
        name: primarySeries?.name ?? "趋势",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 8,
        data: primarySeries?.data ?? [],
        lineStyle: { color: "#10b981", width: 3 },
        itemStyle: {
          color: "#10b981",
          borderColor: "#ffffff",
          borderWidth: 2,
        },
        areaStyle: { color: "rgba(16, 185, 129, 0.1)" },
      },
    ],
  };
}

export function buildChartOption(chart: ApiChartPayload): EChartsOption {
  return chart.type === "bar" ? buildBarOption(chart) : buildLineOption(chart);
}
