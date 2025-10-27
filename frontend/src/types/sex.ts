// types/sex.ts
export const Sex = {
  ManCis: 'MC',
  ManTrans: 'MT',
  WomanCis: 'WC',
  WomanTrans: 'WT',
  Other: 'OT',
  NotSpecified: 'NS',
} as const;

export type Sex = typeof Sex[keyof typeof Sex];

export const sexOptions: { value: Sex; label: string }[] = [
  { value: Sex.ManCis,       label: 'Homem cis' },
  { value: Sex.ManTrans,     label: 'Homem trans' },
  { value: Sex.WomanCis,     label: 'Mulher cis' },
  { value: Sex.WomanTrans,   label: 'Mulher trans' },
  { value: Sex.Other,        label: 'Outro' },
  { value: Sex.NotSpecified, label: 'Prefiro não responder' },
];
