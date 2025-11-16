import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, ChevronUp, Search, X } from 'lucide-react';

export interface MultiSelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

interface MultiSelectProps {
  label: string;
  options: MultiSelectOption[];
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  description?: string;
  error?: string;
  className?: string;
  searchable?: boolean;
  disabled?: boolean;
}

export function MultiSelect({
  label,
  options,
  value,
  onChange,
  placeholder = '選擇項目…',
  description,
  error,
  className = '',
  searchable = true,
  disabled = false,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const availableValues = useMemo(
    () => options.filter(option => !option.disabled).map(option => option.value),
    [options],
  );

  const filteredOptions = useMemo(() => {
    if (!searchable || !searchTerm.trim()) return options;
    const lower = searchTerm.trim().toLowerCase();
    return options.filter(option => option.label.toLowerCase().includes(lower));
  }, [options, searchTerm, searchable]);

  const toggleDropdown = () => {
    if (disabled) return;
    setIsOpen(prev => !prev);
  };

  const closeDropdown = () => setIsOpen(false);

  const toggleOption = (optionValue: string) => {
    onChange(
      value.includes(optionValue)
        ? value.filter(item => item !== optionValue)
        : [...value, optionValue],
    );
  };

  const handleSelectAll = () => {
    const isAllSelected = availableValues.every(val => value.includes(val));
    onChange(isAllSelected ? value.filter(val => !availableValues.includes(val)) : availableValues);
  };

  const handleClear = () => {
    if (value.length === 0) return;
    onChange([]);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (!isOpen && (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      toggleDropdown();
    }
  };

  const handleListKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (!isOpen) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setHighlightedIndex(prev => Math.min(prev + 1, filteredOptions.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlightedIndex(prev => Math.max(prev - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const option = filteredOptions[highlightedIndex];
      if (option && !option.disabled) {
        toggleOption(option.value);
      }
    } else if (event.key === 'Escape') {
      event.preventDefault();
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
    if (isOpen && searchable) {
      searchInputRef.current?.focus();
    }
  }, [isOpen, searchable]);

  const selectedCount = value.length;
  const isAllSelected = availableValues.length > 0 && availableValues.every(val => value.includes(val));

  return (
    <div className={`flex flex-col gap-1 ${className}`} ref={containerRef}>
      <div className="flex items-center justify-between">
        <label className={`text-sm font-medium ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
          {label}
        </label>
        {selectedCount > 0 && (
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-indigo-600 hover:text-indigo-500"
            disabled={disabled}
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
        <span className="truncate">
          {selectedCount === 0 ? (
            <span className="text-gray-400">{placeholder}</span>
          ) : (
            `${selectedCount} 項已選`
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
          <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-xl">
            {searchable && (
              <div className="flex items-center gap-2 border-b border-gray-100 px-3 py-2">
                <Search className="h-4 w-4 text-gray-400" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchTerm}
                  onChange={event => setSearchTerm(event.target.value)}
                  placeholder="搜尋…"
                  className="w-full border-none bg-transparent text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none"
                />
                {searchTerm && (
                  <button
                    type="button"
                    onClick={() => setSearchTerm('')}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            )}

            <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2 text-xs text-gray-500">
              <button
                type="button"
                onClick={handleSelectAll}
                className="flex items-center gap-1 text-indigo-600 hover:text-indigo-500"
              >
                <Check className="h-3.5 w-3.5" />
                {isAllSelected ? '取消全選' : '全選' }
              </button>
              <span>{filteredOptions.length} 個選項</span>
            </div>

            <div className="max-h-60 overflow-y-auto">
              {filteredOptions.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-gray-400">無符合的選項</p>
              ) : (
                filteredOptions.map((option, index) => {
                  const checked = value.includes(option.value);
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => !option.disabled && toggleOption(option.value)}
                      className={`flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition ${
                        option.disabled
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:bg-indigo-50'
                      } ${
                        index === highlightedIndex ? 'bg-indigo-50' : ''
                      }`}
                      role="option"
                      aria-selected={checked}
                      disabled={option.disabled}
                    >
                      <span className={`flex h-4 w-4 items-center justify-center rounded border text-white ${
                        checked ? 'bg-indigo-600 border-indigo-600' : 'border-gray-300'
                      }`}>
                        {checked && <Check className="h-3 w-3" />}
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