// How each strategy column is drawn everywhere (gallery seats, stacked chart, legends).
// Cooperative strategies use verdigris, defecting ones oxblood; within a family they are told
// apart by the hatching (and a letter on the seats), never by colour alone.

import { COLUMNS } from './model/game';

export type Column = (typeof COLUMNS)[number];

export interface StrategyStyle {
  /** fill: url(#pattern) defined in Patterns.svelte */
  fill: string;
  /** one-letter mark for seats */
  mark: string;
  /** one-line description for legends */
  blurb: string;
}

export const STYLE: Record<Column, StrategyStyle> = {
  ALLC: { fill: 'url(#pat-allc)', mark: 'C', blurb: 'always cooperates' },
  TFT: { fill: 'url(#pat-tft)', mark: 'T', blurb: 'copies the opponent’s last move' },
  PAVLOV: { fill: 'url(#pat-pavlov)', mark: 'P', blurb: 'win–stay, lose–shift' },
  GRIM: { fill: 'url(#pat-grim)', mark: 'G', blurb: 'cooperates until betrayed once' },
  STFT: { fill: 'url(#pat-stft)', mark: 'S', blurb: 'tit-for-tat that opens with D' },
  ALLD: { fill: 'url(#pat-alld)', mark: 'D', blurb: 'always defects' },
  OTHER: { fill: 'url(#pat-other)', mark: '·', blurb: 'any of the other 26 genomes' },
};

/** Stacking and legend order: cooperative at the bottom, defecting at the top. */
export const ORDER: Column[] = ['ALLC', 'TFT', 'PAVLOV', 'GRIM', 'STFT', 'ALLD', 'OTHER'];
