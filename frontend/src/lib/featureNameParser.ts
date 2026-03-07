export type FeatureSegmentKey =
  | 'source'
  | 'category'
  | 'indicator'
  | 'params'
  | 'operator'
  | 'opParams'
  | 'window'
  | 'suffix';

export interface FeatureSegments {
  source: string;
  category: string;
  indicator: string;
  params: string;
  operator: string;
  opParams: string;
  window: string;
  suffix: string;
}

const CATEGORY_HINT_SET = new Set([
  'trend',
  'momentum',
  'volatility',
  'volume',
  'cycle',
  'pattern',
  'statistics',
  'microstructure',
  'entropy',
  'tail_risk',
  'price_transform',
  'other',
]);

const SIMPLE_OPERATOR_SET = new Set([
  'Distance',
  'Cross',
  'Ratio',
  'SignedStrength',
  'Sign',
  'Log1p',
  'Abs',
  'Clip',
  'CSRank',
  'CSDemean',
  'CSZScore',
]);

const WINDOW_OPERATOR_SET = new Set([
  'Slope',
  'Std',
  'Mean',
  'Min',
  'Max',
  'Range',
  'Rank',
  'ZScore',
  'Skew',
  'Kurt',
  'TsArgmax',
  'TsArgmin',
  'TsRank',
  'DecayLinear',
]);

const INDICATOR_SUFFIX_SET = new Set([
  'Upper',
  'Middle',
  'Lower',
  'Hist',
  'Signal',
  'InPhase',
  'Quadrature',
  'Sine',
  'LeadSine',
  'MAMA',
  'FAMA',
]);

const PREPROCESS_SUFFIX_SET = new Set(['rank', 'gaussian', 'fracdiff', 'pct', 'binary']);

function isTimeframeToken(token: string): boolean {
  return /^\d+[mhdw]$/i.test(token);
}

function isNumericToken(token: string): boolean {
  return /^-?\d+(?:\.\d+)?$/.test(token);
}

function isPackedNumericParamsToken(token: string): boolean {
  // Support both 12-26-9 and 12/26/9 styles as a single Params token.
  return /^\d+(?:\.\d+)?(?:[-/]\d+(?:\.\d+)?)+$/.test(token);
}

function isWindowToken(token: string): boolean {
  return /^W\d+$/i.test(token);
}

function normalizeSegmentToken(token: string): string {
  return token.replace(/_/g, '-');
}

function readSourceTokens(tokens: string[]): { source: string; nextCursor: number } {
  if (tokens.length === 0) return { source: '', nextCursor: 0 };

  // Backward-compatible reconstruction for legacy source tokens that used '_'.
  // New naming already uses hyphen inside source segment (e.g. taker-ratio).
  if (tokens.length >= 3 && tokens[0] === 'taker' && tokens[1] === 'buy' && tokens[2] === 'volume') {
    return { source: 'taker-buy-volume', nextCursor: 3 };
  }
  if (tokens.length >= 2 && tokens[0] === 'taker' && tokens[1] === 'ratio') {
    return { source: 'taker-ratio', nextCursor: 2 };
  }
  if (tokens.length >= 2 && tokens[0] === 'quote' && tokens[1] === 'volume') {
    return { source: 'quote-volume', nextCursor: 2 };
  }
  if (tokens.length >= 2 && tokens[0] === 'open' && tokens[1] === 'interest') {
    return { source: 'open-interest', nextCursor: 2 };
  }

  return { source: normalizeSegmentToken(tokens[0]), nextCursor: 1 };
}

function tryExtractTrailingOperator(tokens: string[]): {
  baseTokens: string[];
  operator: string;
  opParams: string;
  window: string;
} {
  if (tokens.length === 0) {
    return { baseTokens: tokens, operator: '', opParams: '', window: '' };
  }

  const out = {
    baseTokens: [...tokens],
    operator: '',
    opParams: '',
    window: '',
  };

  const n = out.baseTokens.length;

  // ..._Lag_{n}
  if (
    n >= 2
    && out.baseTokens[n - 2] === 'Lag'
    && (/^\d+$/.test(out.baseTokens[n - 1]) || /^L\d+$/i.test(out.baseTokens[n - 1]))
  ) {
    out.operator = 'Lag';
    out.opParams = out.baseTokens[n - 1];
    out.baseTokens = out.baseTokens.slice(0, n - 2);
    return out;
  }

  // ..._Momentum_L{n}
  if (n >= 2 && out.baseTokens[n - 2] === 'Momentum' && /^L\d+$/i.test(out.baseTokens[n - 1])) {
    out.operator = 'Momentum';
    out.opParams = out.baseTokens[n - 1];
    out.baseTokens = out.baseTokens.slice(0, n - 2);
    return out;
  }

  // ..._BinarySignal[_suffix...]
  const binaryIdx = out.baseTokens.lastIndexOf('BinarySignal');
  if (binaryIdx >= 0) {
    out.operator = 'BinarySignal';
    out.opParams = out.baseTokens.slice(binaryIdx + 1).join('_');
    out.baseTokens = out.baseTokens.slice(0, binaryIdx);
    return out;
  }

  // ..._TsCorr_{corr_with}_W{n}
  if (n >= 4 && isWindowToken(out.baseTokens[n - 1])) {
    const tsCorrIdx = out.baseTokens.lastIndexOf('TsCorr');
    if (tsCorrIdx >= 0 && tsCorrIdx < n - 2) {
      out.operator = 'TsCorr';
      out.window = out.baseTokens[n - 1];
      out.opParams = out.baseTokens.slice(tsCorrIdx + 1, n - 1).join('_');
      out.baseTokens = out.baseTokens.slice(0, tsCorrIdx);
      return out;
    }
  }

  // ..._{WindowOperator}_W{n}
  if (n >= 2 && isWindowToken(out.baseTokens[n - 1]) && WINDOW_OPERATOR_SET.has(out.baseTokens[n - 2])) {
    out.operator = out.baseTokens[n - 2];
    out.window = out.baseTokens[n - 1];
    out.baseTokens = out.baseTokens.slice(0, n - 2);
    return out;
  }

  // ..._{SimpleOperator}
  if (SIMPLE_OPERATOR_SET.has(out.baseTokens[n - 1])) {
    out.operator = out.baseTokens[n - 1];
    out.baseTokens = out.baseTokens.slice(0, n - 1);
    return out;
  }

  return out;
}

function tryExtractTrailingSuffix(tokens: string[]): {
  baseTokens: string[];
  suffix: string;
  window: string;
} {
  if (tokens.length === 0) {
    return { baseTokens: tokens, suffix: '', window: '' };
  }

  const out = {
    baseTokens: [...tokens],
    suffix: '',
    window: '',
  };

  const n = out.baseTokens.length;

  // ..._zscore_{window}
  if (n >= 2 && /^zscore$/i.test(out.baseTokens[n - 2]) && /^\d+$/.test(out.baseTokens[n - 1])) {
    out.suffix = 'zscore';
    out.window = `W${out.baseTokens[n - 1]}`;
    out.baseTokens = out.baseTokens.slice(0, n - 2);
    return out;
  }

  // ..._diff{n}
  if (/^diff\d+$/i.test(out.baseTokens[n - 1])) {
    out.suffix = out.baseTokens[n - 1];
    out.baseTokens = out.baseTokens.slice(0, n - 1);
    return out;
  }

  // indicator outputs (e.g. BBANDS Upper/Lower, MACD Hist)
  if (INDICATOR_SUFFIX_SET.has(out.baseTokens[n - 1])) {
    out.suffix = out.baseTokens[n - 1];
    out.baseTokens = out.baseTokens.slice(0, n - 1);
    return out;
  }

  // preprocessing or simple value-type suffixes
  if (PREPROCESS_SUFFIX_SET.has(out.baseTokens[n - 1])) {
    out.suffix = out.baseTokens[n - 1];
    out.baseTokens = out.baseTokens.slice(0, n - 1);
    return out;
  }

  return out;
}

export function parseFeatureNameSegments(name: string): FeatureSegments {
  const tokens = name.split('_').filter(Boolean);
  if (tokens.length === 0) {
    return emptySegments();
  }

  // meta / label families do not follow source_category_... format.
  if (tokens[0] === 'meta' || tokens[0] === 'label') {
    return {
      source: tokens[0],
      category: '',
      indicator: tokens.slice(1).join('_'),
      params: '',
      operator: '',
      opParams: '',
      window: '',
      suffix: '',
    };
  }

  const sourceRead = readSourceTokens(tokens);
  let source = sourceRead.source;
  let cursor = sourceRead.nextCursor;

  // Multi-timeframe naming inserts timeframe after source: close_1h_trend_...
  if (cursor < tokens.length && isTimeframeToken(tokens[cursor])) {
    source = `${source}_${tokens[cursor]}`;
    cursor += 1;
  }

  // Category exists in current backend naming (source_category_indicator_...).
  let category = '';
  if (cursor < tokens.length && CATEGORY_HINT_SET.has(tokens[cursor].toLowerCase())) {
    category = normalizeSegmentToken(tokens[cursor]);
    cursor += 1;
  }

  let bodyTokens = tokens.slice(cursor);

  const opParsed = tryExtractTrailingOperator(bodyTokens);
  bodyTokens = opParsed.baseTokens;

  const suffixParsed = tryExtractTrailingSuffix(bodyTokens);
  bodyTokens = suffixParsed.baseTokens;

  let indicator = '';
  let params = '';
  const firstParamIdx = bodyTokens.findIndex(
    (token) => isNumericToken(token) || isPackedNumericParamsToken(token),
  );
  if (firstParamIdx === -1) {
    indicator = bodyTokens.join('_');
  } else if (firstParamIdx === 0) {
    params = bodyTokens.join('_');
  } else {
    indicator = bodyTokens.slice(0, firstParamIdx).join('_');
    params = bodyTokens.slice(firstParamIdx).join('_');
  }

  if (!indicator && opParsed.operator) {
    indicator = 'raw';
  }

  indicator = normalizeSegmentToken(indicator);

  const window = opParsed.window || suffixParsed.window;

  return {
    source,
    category,
    indicator,
    params,
    operator: opParsed.operator,
    opParams: opParsed.opParams,
    window,
    suffix: suffixParsed.suffix,
  };
}

export function emptySegments(): FeatureSegments {
  return {
    source: '',
    category: '',
    indicator: '',
    params: '',
    operator: '',
    opParams: '',
    window: '',
    suffix: '',
  };
}
