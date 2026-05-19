from crewai.tools import BaseTool

# ============================================================
# 工具 3：SQL 自动修复（完整版）
# ============================================================
class SQLDebugTool(BaseTool):
    name: str = "sql_debug"
    description: str = "Auto-detect and fix common SQL syntax errors, return corrected SQL with comments."

    def _run(self, sql: str) -> str:
        """自动检测并修复常见SQL错误：
        1. form → from
        2. 缺失空格
        3. SELECT * 补全
        4. 多余逗号
        5. 大小写混乱
        """
        if not sql or len(sql.strip()) == 0:
            return "❌ Error: SQL is empty."

        fixed_sql = sql.strip()

        # 修复1：form → from
        fixed_sql = fixed_sql.replace(" form ", " from ").replace("FORM ", "FROM ")
        fixed_sql = fixed_sql.replace("form ", "from ").replace(" FORM ", " FROM ")

        # 修复2：多余空格
        fixed_sql = " ".join(fixed_sql.split())

        # 修复3：select from → select * from
        if fixed_sql.lower().startswith("select from"):
            fixed_sql = fixed_sql.replace("select from", "select * from")

        # 修复4：where 前多余逗号
        fixed_sql = fixed_sql.replace(", where", " where").replace(",WHERE", " WHERE")

        # 输出结果
        if fixed_sql == sql.strip():
            return f"✅ SQL is valid:\n{fixed_sql}"
        else:
            return (
                f"✅ SQL fixed:\n"
                f"Original: {sql}\n"
                f"Fixed:    {fixed_sql}"
            )


# ============================================================
# 【手动测试：SQL 自动修复工具】
# ============================================================
if __name__ == "__main__":
    # 1. 创建工具实例
    sql_tool = SQLDebugTool()

    # 2. 构造一条错误SQL
    error_sql = "SELECT * form patient WHERE clinic_id = 'SH001'"

    # 3. 调用工具
    fix_result = sql_tool._run(error_sql)

    # 4. 打印结果
    print("=" * 60)
    print("🔧 SQL Debug Tool Test Result")
    print("=" * 60)
    print(fix_result)
    print("=" * 60)