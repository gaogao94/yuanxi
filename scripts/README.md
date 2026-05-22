# scripts 目录说明

这个目录现在按用途拆成两类：

- `scripts/debug/`
  - 放历史调试脚本，不属于正式测试入口。
  - 主要用于排查 `Agent3` 调模型时的网络、SSL、请求头兼容问题。

## debug 子目录

- `scripts/debug/network/`
  - OpenAI / LiteLLM / httpx / transport / proxy 相关的临时联通性调试脚本。

- `scripts/debug/patches/`
  - 一次性补丁脚本。
  - 例如历史上用于直接修改 `agents/agent3.py` 的 `fix_agent3_api.py`。

## 当前约定

- 以后新增正式测试，统一优先放到 `tests/`，不要再放到 `scripts/`。
- 以后新增临时排障脚本，优先放到 `scripts/debug/` 下对应子目录。
