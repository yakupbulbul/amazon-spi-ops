import { Languages } from "lucide-react";

import type { AplusLanguage } from "../../lib/api";
import { LanguageSelector } from "./LanguageSelector";
import { formatLanguageLabel } from "./languages";

type TranslationToggleProps = {
  autoTranslate: boolean;
  sourceLanguage: AplusLanguage;
  targetLanguage: AplusLanguage;
  onToggle: (value: boolean) => void;
  onTargetLanguageChange: (value: AplusLanguage) => void;
  disabled?: boolean;
};

export function TranslationToggle({
  autoTranslate,
  sourceLanguage,
  targetLanguage,
  onToggle,
  onTargetLanguageChange,
  disabled = false,
}: TranslationToggleProps) {
  return (
    <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3 text-sky-200">
            <Languages className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-white">Auto-translate generated draft</p>
            <p className="mt-1 text-sm leading-6 text-slate-400">
              Generate the structured base draft in {formatLanguageLabel(sourceLanguage)} and translate
              the shopper-facing copy into another language while preserving the JSON shape.
            </p>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={autoTranslate}
          onClick={() => onToggle(!autoTranslate)}
          disabled={disabled}
          className={[
            "relative inline-flex h-7 w-12 shrink-0 rounded-full border transition disabled:cursor-not-allowed disabled:opacity-60",
            autoTranslate
              ? "border-sky-300/30 bg-sky-400/30"
              : "border-white/10 bg-white/[0.06]",
          ].join(" ")}
        >
          <span
            className={[
              "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition",
              autoTranslate ? "left-6" : "left-0.5",
            ].join(" ")}
          />
        </button>
      </div>

      {autoTranslate ? (
        <div className="mt-4">
          <LanguageSelector
            label="Target language"
            value={targetLanguage}
            onChange={onTargetLanguageChange}
            helperText="Only shopper-facing text is translated. Schema keys and module types stay unchanged."
            disabled={disabled}
          />
        </div>
      ) : (
        <p className="mt-4 rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
          The draft will be generated directly in {formatLanguageLabel(sourceLanguage)}.
        </p>
      )}
    </div>
  );
}
