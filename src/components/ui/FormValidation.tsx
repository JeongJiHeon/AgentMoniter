/**
 * FormValidation - 폼 유효성 검사 유틸리티
 *
 * Features:
 * - 다양한 내장 검증 규칙
 * - 커스텀 검증 규칙 지원
 * - 비동기 검증 지원
 * - 폼 상태 관리 훅
 */

import { useState, useCallback, useMemo } from 'react';
import type { ValidationRule } from './Input';

/**
 * 내장 검증 규칙 생성 함수들
 */
export const validators = {
  required: (message = '필수 입력 항목입니다'): ValidationRule => ({
    validate: (value) => value.trim().length > 0,
    message,
  }),

  minLength: (min: number, message?: string): ValidationRule => ({
    validate: (value) => value.length >= min,
    message: message || `최소 ${min}자 이상 입력해주세요`,
  }),

  maxLength: (max: number, message?: string): ValidationRule => ({
    validate: (value) => value.length <= max,
    message: message || `최대 ${max}자까지 입력 가능합니다`,
  }),

  email: (message = '올바른 이메일 형식이 아닙니다'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    },
    message,
  }),

  url: (message = '올바른 URL 형식이 아닙니다'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      try {
        new URL(value);
        return true;
      } catch {
        return false;
      }
    },
    message,
  }),

  pattern: (regex: RegExp, message: string): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return regex.test(value);
    },
    message,
  }),

  numeric: (message = '숫자만 입력 가능합니다'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return /^\d+$/.test(value);
    },
    message,
  }),

  alphanumeric: (message = '영문과 숫자만 입력 가능합니다'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      return /^[a-zA-Z0-9]+$/.test(value);
    },
    message,
  }),

  noWhitespace: (message = '공백은 사용할 수 없습니다'): ValidationRule => ({
    validate: (value) => !/\s/.test(value),
    message,
  }),

  match: (getMatchValue: () => string, message = '값이 일치하지 않습니다'): ValidationRule => ({
    validate: (value) => value === getMatchValue(),
    message,
  }),

  custom: (validateFn: (value: string) => boolean, message: string): ValidationRule => ({
    validate: validateFn,
    message,
  }),
};

/**
 * 폼 상태 관리 훅
 */
interface UseFormOptions<T extends Record<string, string>> {
  initialValues: T;
  validationRules?: Partial<Record<keyof T, ValidationRule[]>>;
  onSubmit?: (values: T) => void | Promise<void>;
}

interface UseFormReturn<T extends Record<string, string>> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isValid: boolean;
  isSubmitting: boolean;
  setValue: (field: keyof T, value: string) => void;
  setTouched: (field: keyof T) => void;
  validateField: (field: keyof T) => boolean;
  validateAll: () => boolean;
  handleSubmit: (e?: React.FormEvent) => Promise<void>;
  reset: () => void;
  getFieldProps: (field: keyof T) => {
    value: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
    onBlur: () => void;
    error?: string;
  };
}

export function useForm<T extends Record<string, string>>({
  initialValues,
  validationRules = {},
  onSubmit,
}: UseFormOptions<T>): UseFormReturn<T> {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateField = useCallback(
    (field: keyof T): boolean => {
      const rules = validationRules[field];
      if (!rules) return true;

      const value = values[field];
      for (const rule of rules) {
        if (!rule.validate(value)) {
          setErrors((prev) => ({ ...prev, [field]: rule.message }));
          return false;
        }
      }
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
      return true;
    },
    [values, validationRules]
  );

  const validateAll = useCallback((): boolean => {
    let isValid = true;
    const newErrors: Partial<Record<keyof T, string>> = {};

    for (const field of Object.keys(initialValues) as Array<keyof T>) {
      const rules = validationRules[field];
      if (!rules) continue;

      const value = values[field];
      for (const rule of rules) {
        if (!rule.validate(value)) {
          newErrors[field] = rule.message;
          isValid = false;
          break;
        }
      }
    }

    setErrors(newErrors);
    return isValid;
  }, [values, validationRules, initialValues]);

  const isValid = useMemo(() => {
    return Object.keys(errors).length === 0;
  }, [errors]);

  const setValue = useCallback((field: keyof T, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  }, []);

  const setFieldTouched = useCallback((field: keyof T) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  }, []);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();

      // 모든 필드 touched로 설정
      const allTouched = Object.keys(initialValues).reduce(
        (acc, key) => ({ ...acc, [key]: true }),
        {} as Partial<Record<keyof T, boolean>>
      );
      setTouched(allTouched);

      if (!validateAll()) return;

      if (onSubmit) {
        setIsSubmitting(true);
        try {
          await onSubmit(values);
        } finally {
          setIsSubmitting(false);
        }
      }
    },
    [initialValues, validateAll, onSubmit, values]
  );

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  const getFieldProps = useCallback(
    (field: keyof T) => ({
      value: values[field],
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setValue(field, e.target.value);
        if (touched[field]) {
          validateField(field);
        }
      },
      onBlur: () => {
        setFieldTouched(field);
        validateField(field);
      },
      error: touched[field] ? errors[field] : undefined,
    }),
    [values, touched, errors, setValue, setFieldTouched, validateField]
  );

  return {
    values,
    errors,
    touched,
    isValid,
    isSubmitting,
    setValue,
    setTouched: setFieldTouched,
    validateField,
    validateAll,
    handleSubmit,
    reset,
    getFieldProps,
  };
}

export default validators;
