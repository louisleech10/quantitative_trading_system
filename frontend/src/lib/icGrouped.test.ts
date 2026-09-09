/** ICRESULT_PAGING B2 review GROK-R1-P1-01：三層 grouped_ic 還原後，Regime／Grouped 圖表能取到該特徵的有限值。 */
import { describe, expect, it } from 'vitest';
import { reshapeGroupedForFeature } from '@/lib/icGrouped';

describe('reshapeGroupedForFeature', () => {
  it('{kind:{label:value}} ⇒ {kind:{label:{feature:value}}}；null kind 略過、非數值不補', () => {
    const out = reshapeGroupedForFeature({ by_regime: { bull: -0.23, bear: -0.18, x: null }, by_data_source: null }, 'f1');
    expect(out).toEqual({ by_regime: { bull: { f1: -0.23 }, bear: { f1: -0.18 } } });
    expect(reshapeGroupedForFeature(null, 'f1')).toBeNull();
    expect(reshapeGroupedForFeature({ by_regime: { bull: 0.1 } }, null)).toBeNull();
  });
});
