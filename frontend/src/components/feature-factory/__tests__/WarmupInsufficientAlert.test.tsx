import '@testing-library/jest-dom/vitest';

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import WarmupInsufficientAlert from '../WarmupInsufficientAlert';

describe('WarmupInsufficientAlert', () => {
  afterEach(() => {
    cleanup();
  });

  it('shows alert with needed, available, and affected_bars when warmup is insufficient', () => {
    render(
      <WarmupInsufficientAlert
        warmup={{ needed: 500, available: 120, affected_bars: 380 }}
      />,
    );

    expect(screen.getByTestId('warmup-insufficient-alert')).toBeInTheDocument();
    const message = screen.getByTestId('warmup-insufficient-message');
    expect(message).toHaveTextContent('起點前歷史僅 120/500 根，前 380 根特徵品質降級');
    expect(message).toHaveTextContent('120/500');
    expect(message).toHaveTextContent('380');
  });

  it('renders nothing when warmup is absent or sufficient', () => {
    const { container: nullContainer } = render(<WarmupInsufficientAlert warmup={null} />);
    expect(nullContainer.querySelector('[data-testid="warmup-insufficient-alert"]')).toBeNull();

    cleanup();

    const { container: undefinedContainer } = render(<WarmupInsufficientAlert />);
    expect(undefinedContainer.querySelector('[data-testid="warmup-insufficient-alert"]')).toBeNull();
  });
});
