import type { CSSProperties } from "react";
import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";

type EChartProps = {
  option: EChartsOption;
  className?: string;
  style?: CSSProperties;
  loading?: boolean;
};

export function EChart({
  option,
  className,
  style,
  loading = false,
}: EChartProps) {
  return (
    <ReactECharts
      option={option}
      notMerge
      lazyUpdate
      showLoading={loading}
      className={className}
      style={{ height: 220, width: "100%", ...style }}
    />
  );
}
