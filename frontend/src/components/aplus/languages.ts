import type { AplusLanguage } from "../../lib/api";

export const aplusLanguageOptions: Array<{ value: AplusLanguage; label: string }> = [
  { value: "de-DE", label: "German (de-DE)" },
  { value: "en-GB", label: "English UK (en-GB)" },
  { value: "en-US", label: "English US (en-US)" },
  { value: "fr-FR", label: "French (fr-FR)" },
  { value: "it-IT", label: "Italian (it-IT)" },
  { value: "es-ES", label: "Spanish (es-ES)" },
];

export function formatLanguageLabel(language: AplusLanguage): string {
  return aplusLanguageOptions.find((option) => option.value === language)?.label ?? language;
}

export function getDefaultTargetLanguage(sourceLanguage: AplusLanguage): AplusLanguage {
  return aplusLanguageOptions.find((option) => option.value !== sourceLanguage)?.value ?? "en-US";
}
