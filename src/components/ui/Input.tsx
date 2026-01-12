/**
 * Input - shadcn/ui 스타일의 입력 컴포넌트
 *
 * Features:
 * - 에러/성공 상태 표시
 * - 라벨 및 힌트 텍스트
 * - 접근성 (ARIA) 지원
 */

import * as React from "react"
import { cn } from "@/lib/utils"

export interface ValidationRule {
  validate: (value: string) => boolean
  message: string
}

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  isRequired?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  inputSize?: 'sm' | 'md' | 'lg'
}

const inputSizeStyles = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-9 px-3 text-sm',
  lg: 'h-10 px-4 text-base',
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({
    className,
    type,
    label,
    error,
    hint,
    isRequired,
    leftIcon,
    rightIcon,
    inputSize = 'md',
    id,
    ...props
  }, ref) => {
    const inputId = id || React.useId()
    const errorId = `${inputId}-error`
    const hintId = `${inputId}-hint`
    const hasError = Boolean(error)

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5"
          >
            {label}
            {isRequired && (
              <span className="text-[hsl(var(--destructive))] ml-1" aria-hidden="true">*</span>
            )}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" aria-hidden="true">
              {leftIcon}
            </div>
          )}

          <input
            type={type}
            id={inputId}
            ref={ref}
            className={cn(
              "flex w-full rounded-lg border bg-transparent shadow-sm transition-colors",
              "placeholder:text-[hsl(var(--muted-foreground))]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-0",
              "disabled:cursor-not-allowed disabled:opacity-50",
              inputSizeStyles[inputSize],
              hasError
                ? "border-[hsl(var(--destructive))] focus-visible:ring-[hsl(var(--destructive))]"
                : "border-[hsl(var(--input))] focus-visible:ring-[hsl(var(--ring))]",
              leftIcon && "pl-10",
              rightIcon && "pr-10",
              className
            )}
            aria-invalid={hasError}
            aria-describedby={
              [error && errorId, hint && hintId].filter(Boolean).join(' ') || undefined
            }
            aria-required={isRequired}
            {...props}
          />

          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" aria-hidden="true">
              {rightIcon}
            </div>
          )}
        </div>

        {error && (
          <p id={errorId} className="mt-1.5 text-sm text-[hsl(var(--destructive))]" role="alert" aria-live="polite">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={hintId} className="mt-1.5 text-sm text-[hsl(var(--muted-foreground))]">
            {hint}
          </p>
        )}
      </div>
    )
  }
)
Input.displayName = "Input"

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  hint?: string
  isRequired?: boolean
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({
    className,
    label,
    error,
    hint,
    isRequired,
    id,
    ...props
  }, ref) => {
    const textareaId = id || React.useId()
    const errorId = `${textareaId}-error`
    const hintId = `${textareaId}-hint`
    const hasError = Boolean(error)

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5"
          >
            {label}
            {isRequired && (
              <span className="text-[hsl(var(--destructive))] ml-1" aria-hidden="true">*</span>
            )}
          </label>
        )}

        <textarea
          id={textareaId}
          ref={ref}
          className={cn(
            "flex min-h-[80px] w-full rounded-lg border bg-transparent px-3 py-2 text-sm shadow-sm transition-colors",
            "placeholder:text-[hsl(var(--muted-foreground))]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-0",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "resize-none",
            hasError
              ? "border-[hsl(var(--destructive))] focus-visible:ring-[hsl(var(--destructive))]"
              : "border-[hsl(var(--input))] focus-visible:ring-[hsl(var(--ring))]",
            className
          )}
          aria-invalid={hasError}
          aria-describedby={
            [error && errorId, hint && hintId].filter(Boolean).join(' ') || undefined
          }
          aria-required={isRequired}
          {...props}
        />

        {error && (
          <p id={errorId} className="mt-1.5 text-sm text-[hsl(var(--destructive))]" role="alert" aria-live="polite">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={hintId} className="mt-1.5 text-sm text-[hsl(var(--muted-foreground))]">
            {hint}
          </p>
        )}
      </div>
    )
  }
)
Textarea.displayName = "Textarea"

export default Input
