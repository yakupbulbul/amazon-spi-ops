import type { AplusLanguage } from "../../lib/api";
import { aplusLanguageOptions } from "./languages";

type LanguageSelectorProps = {
  label: string;
  value: AplusLanguage;
  onChange: (value: AplusLanguage) => void;
  helperText?: string;
  disabled?: boolean;
};

export function LanguageSelector({
  label,
  value,
  onChange,
  helperText,
  disabled = false,
}: LanguageSelectorProps) {
  return (
    <label className="block space-y-2">
      <span className="text-sm text-slate-300">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as AplusLanguage)}
        disabled={disabled}
        className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none disabled:cursor-not-allowed disabled:opacity-60"
      >
        {aplusLanguageOptions.map((option) => (
          <option key={option.value} value={option.value} className="bg-slate-950">
            {option.label}
          </option>
        ))}
      </select>
      {helperText ? <p className="text-xs leading-5 text-slate-500">{helperText}</p> : null}
    </label>
  );
}
