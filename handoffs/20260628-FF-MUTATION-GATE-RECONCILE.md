# Mutation 機制 review reconcile(Codex+Composer 兩家收斂 → 硬化)

被審:章程 §B1.1-1.3 + `scripts/mutation_probe_check.sh`(commit 0d377e6)。兩家 adversarial 皆「方向可用,須補 P0 才能當硬閘」,且**各自在 /tmp 跑反例**證明洞。

## 收斂洞(兩家都攻破)→ 已修
| 洞 | 攻擊 | 修法(已實作) |
|---|---|---|
| A1 空心探針 | `test_mutation_x(): assert True` 過閘 | `mutation_probe_static.py` AST:非空心+須 falsification |
| A2 偽 raises | `pytest.raises(ZeroDivisionError): 1/0` 過閘 | 靜態:探針須真碰待測系統(monkeypatch/setattr 或引用 momentum 符號) |
| A4 改名+stub | 真探針名不含 mutation + 空 stub → 只跑 stub | 規則2 `-k test_mutation_`;stub 被靜態擋 |
| A6 N/A docstring | docstring 內嵌 `# MUTATION-PROBE: n/a` 混批濫用 | N/A 須**行首**+非空理由 |
| C1 async def | `async def test_` 未偵測 | regex `(async )?def test_` |
| C3 venv 路徑 | 子目錄跑落系統 python | SCRIPT_DIR/REPO_ROOT 鎖定 |
| C4 collected 誤名 | 取 passed 數誤稱 collected | tail -1 解析 + 改名 passed_count |
| A5 oracle 自指 | 機器未驗 | `ORACLE-SELF-REF WARN` 啟發告警(不宣稱證獨立)+ adversarial 必審 |

## §B8 閉合自驗(委員反例重跑,皆現紅)
- A1 空心→FAIL(靜態);A2 偽raises→FAIL(未碰系統);A4 改名+stub→FAIL;A6 docstring N/A→FAIL(缺探針)。
- 不誤擋:`mutation_probe_check.sh tests/feature_engineering/atomic/` → PASS(6 探針真跑),WARN 正確觸發 test_bug1(注入用 _INPUT_TYPE_MAP,adversarial 判為合格)。

## 誠實邊界(兩家共識,保留人工)
- 機器擋:空心/偽 raises/無探針/混批假 N/A/命名繞過。
- **仍靠 adversarial**:oracle 真獨立性(B1.2,機器只 WARN)、探針是否真綁底層斷言語義。
- 未接 gate_check(A7):目前靠 B1-驗收紀律「驗收方親跑」;後續可接 postflight。

結論:機制硬化後可當 B1 atomic 批次硬閘;誠實邊界明示於章程。
