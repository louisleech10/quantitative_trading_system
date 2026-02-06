"use client"

import * as React from "react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { Check, ChevronDown, ChevronUp } from "lucide-react"

import { cn } from "@/lib/utils"

const Select = SelectPrimitive.Root

const SelectGroup = SelectPrimitive.Group

const SelectValue = SelectPrimitive.Value

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex h-10 w-full items-center justify-between rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 ring-offset-background placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-white/5 [&>span]:line-clamp-1",
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName

const SelectScrollUpButton = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.ScrollUpButton>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollUpButton>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollUpButton
    ref={ref}
    className={cn(
      "flex cursor-default items-center justify-center py-1",
      className
    )}
    {...props}
  >
    <ChevronUp className="h-4 w-4" />
  </SelectPrimitive.ScrollUpButton>
))
SelectScrollUpButton.displayName = SelectPrimitive.ScrollUpButton.displayName

const SelectScrollDownButton = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.ScrollDownButton>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollDownButton>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollDownButton
    ref={ref}
    className={cn(
      "flex cursor-default items-center justify-center py-1",
      className
    )}
    {...props}
  >
    <ChevronDown className="h-4 w-4" />
  </SelectPrimitive.ScrollDownButton>
))
SelectScrollDownButton.displayName =
  SelectPrimitive.ScrollDownButton.displayName

const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = "popper", ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      className={cn(
        "relative z-50 max-h-96 min-w-[8rem] overflow-hidden rounded-md border border-white/10 bg-[#1a233a] text-slate-100 shadow-xl shadow-black/30 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
        position === "popper" &&
          "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
        className
      )}
      position={position}
      {...props}
    >
      <SelectScrollUpButton />
      <SelectPrimitive.Viewport
        className={cn(
          "p-1",
          position === "popper" &&
            "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]"
        )}
      >
        {children}
      </SelectPrimitive.Viewport>
      <SelectScrollDownButton />
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
))
SelectContent.displayName = SelectPrimitive.Content.displayName

const SelectLabel = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Label
    ref={ref}
    className={cn("py-1.5 pl-8 pr-2 text-sm font-semibold", className)}
    {...props}
  />
))
SelectLabel.displayName = SelectPrimitive.Label.displayName

const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none focus:bg-white/10 focus:text-slate-100 data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>

    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = SelectPrimitive.Item.displayName

const SelectSeparator = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Separator
    ref={ref}
    className={cn("-mx-1 my-1 h-px bg-white/10", className)}
    {...props}
  />
))
SelectSeparator.displayName = SelectPrimitive.Separator.displayName

// 導出 Radix UI 組件（用於 ParamHeatmap 等組件）
export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton,
}

// ==================== 自定義 Select 組件（保留向後兼容）====================
// 用於不使用 Radix UI 的舊版組件

export interface CustomSelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

// 類型別名，向後兼容
export type SelectOption = CustomSelectOption;

interface CustomSelectProps {
  label: string;
  options: CustomSelectOption[];
  value: string | null;
  onChange: (next: string | null) => void;
  placeholder?: string;
  description?: string;
  error?: string;
  className?: string;
  disabled?: boolean;
  allowClear?: boolean;
}

export function CustomSelect({
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
}: CustomSelectProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [highlightedIndex, setHighlightedIndex] = React.useState(0);
  const containerRef = React.useRef<HTMLDivElement>(null);

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

  React.useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        closeDropdown();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  React.useEffect(() => {
    if (!isOpen) return;
    const index = value ? options.findIndex(option => option.value === value) : 0;
    setHighlightedIndex(index >= 0 ? index : 0);
  }, [isOpen, options, value]);

  return (
    <div className={`flex flex-col gap-1 ${className}`} ref={containerRef}>
      <div className="flex items-center justify-between">
        <label className={`text-sm font-medium ${disabled ? 'text-slate-500' : 'text-slate-200'}`}>
          {label}
        </label>
        {allowClear && value && (
          <button
            type="button"
            onClick={() => onChange(null)}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            清除
          </button>
        )}
      </div>

      <button
        type="button"
        onClick={toggleDropdown}
        onKeyDown={handleKeyDown}
        className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
          disabled
            ? 'bg-white/5 text-slate-500 border-white/10 cursor-not-allowed'
            : 'bg-white/5 text-slate-100 border-white/10 hover:bg-white/10'
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
            <span className="text-slate-500">{placeholder}</span>
          )}
        </span>
        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {description && <p className="text-xs text-slate-400">{description}</p>}
      {error && <p className="text-xs text-rose-400">{error}</p>}

      {isOpen && (
        <div
          className="relative"
          onKeyDown={handleListKeyDown}
        >
          <div className="absolute z-20 mt-1 w-full rounded-md border border-white/10 bg-[#1a233a] shadow-xl shadow-black/30" role="listbox">
            <div className="max-h-60 overflow-y-auto">
              {options.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-slate-500">沒有可用選項</p>
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
                          : 'hover:bg-white/5'
                      } ${
                        index === highlightedIndex ? 'bg-white/10' : ''
                      }`}
                      onClick={() => handleOptionClick(option.value, option.disabled)}
                      role="option"
                      aria-selected={isSelected}
                      disabled={option.disabled}
                    >
                      <span className={`flex h-4 w-4 items-center justify-center rounded border ${
                        isSelected ? 'border-blue-400 bg-blue-400 text-white' : 'border-white/20'
                      }`}>
                        {isSelected && <Check className="h-3 w-3" />}
                      </span>
                      {option.icon && (
                        <span className="text-base">{option.icon}</span>
                      )}
                      <span className="flex-1 truncate text-slate-100">{option.label}</span>
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

// CustomSelect 已在上面 Line 187 通過函數聲明導出
