# handoff ic1a-align-review-b1 (Composer)

**正在做**: B1 adversarial review 已完成 → REJECT  
**待辦**: Codex 修 ADV-B1-01~05 → Composer 複審 → B2 派工  
**阻塞**: 4 BLOCKING（覆蓋率/Tier-2 過嚴/rng(0) 漏網/變異區+M1 單點）  
**本次決策**: kernel 方向對但 Tier-2 抽樣與覆蓋率未達 SPEC v3；purge_gap 雙檢正確  
**踩坑**: `rng(0)` 200 列漏 135 中間列；M1 roll 測試掩蓋單點漏網  
**產出**: `handoffs/IC1A-ALIGN-REVIEW-B1-composer.md`  
**VERIFY**: `pytest …test_alignment_contract.py + M7 -q` → 13 passed
