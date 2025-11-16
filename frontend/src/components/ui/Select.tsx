import React, { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

interface SelectProps {
  label: string;
  options: SelectOption[];
  value: string | null;
  onChange: (next: string | null) => void;
  placeholder?: string;
  description?: string;
  error?: string;
  className?: string;
  disabled?: boolean;
  allowClear?: boolean;
}

export function Select({
  label,
  options,
  value,
  onChange,
  placeholder = '請選擇…',
  description,
  error,
  className = '',
  disabled = false,
  allowClear = false,
}: SelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find(option => option.value === value) ?? null;

  const toggleDropdown = () => {
    if (disabled) return;
    setIsOpen(prev => !prev);
  };

  const closeDropdown = () => setIsOpen(false);

  const handleOptionClick = (optionValue: string, optionDisabled?: boolean) => {
    if (optionDisabled) return;
    onChange(optionValue);
    closeDropdown();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (disabled) return;
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setIsOpen(true);
    } else if (event.key === 'Escape') {
      closeDropdown();
    }
  };

  const handleListKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (!isOpen) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setHighlightedIndex(prev => Math.min(prev + 1, options.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlightedIndex(prev => Math.max(prev - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const option = options[highlightedIndex];
      if (option && !option.disabled) {
        handleOptionClick(option.value);
      }
    } else if (event.key === 'Escape') {
      closeDropdown();
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        closeDropdown();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const index = value ? options.findIndex(option => option.value === value) : 0;
    setHighlightedIndex(index >= 0 ? index : 0);
  }, [isOpen, options, value]);

  return (
    <div className={`flex flex-col gap-1 ${className}`} ref={containerRef}>
      <div className="flex items-center justify-between">
        <label className={`text-sm font-medium ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
          {label}
        </label>
        {allowClear && value && (
          <button
            type="button"
            onClick={() => onChange(null)}
            className="text-xs text-indigo-600 hover:text-indigo-500"
          >
            清除
          </button>
        )}
      </div>

      <button
        type="button"
        onClick={toggleDropdown}
        onKeyDown={handleKeyDown}
        className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-sm shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
          disabled
            ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed'
            : 'bg-white text-gray-900 border-gray-300 hover:bg-gray-50'
        }`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className="flex items-center gap-2 truncate">
          {selectedOption ? (
            <>
              {selectedOption.icon && <span className="text-base">{selectedOption.icon}</span>}
              {selectedOption.label}
            </>
          ) : (
            <span className="text-gray-400">{placeholder}</span>
          )}
        </span>
        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {description && <p className="text-xs text-gray-500">{description}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}

      {isOpen && (
        <div
          className="relative"
          onKeyDown={handleListKeyDown}
        >
          <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-xl" role="listbox">
            <div className="max-h-60 overflow-y-auto">
              {options.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-gray-400">沒有可用選項</p>
              ) : (
                options.map((option, index) => {
                  const isSelected = option.value === value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      className={`flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition ${
                        option.disabled
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:bg-indigo-50'
                      } ${
                        index === highlightedIndex ? 'bg-indigo-50' : ''
                      }`}
                      onClick={() => handleOptionClick(option.value, option.disabled)}
                      role="option"
                      aria-selected={isSelected}
                      disabled={option.disabled}
                    >
                      <span className={`flex h-4 w-4 items-center justify-center rounded border ${
                        isSelected ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-gray-300'
                      }`}>
                        {isSelected && <Check className="h-3 w-3" />}
                      </span>
                      {option.icon && (
                        <span className="text-base">{option.icon}</span>
                      )}
                      <span className="flex-1 truncate text-gray-900">{option.label}</span>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}