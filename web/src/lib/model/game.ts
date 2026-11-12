// The game and the memory-1 encoding, exactly as in main.py.
//
// Actions: 0 = C, 1 = D. An outcome (own action, opponent's action) is the state
// 2*own + opp = 0 CC, 1 CD, 2 DC, 3 DD, always written from the player's own point of view.
// Genome: 5 bits [first move, after CC, after CD, after DC, after DD].
// A genome is stored as the integer whose binary digits are those bits read left to right
// (main.genome_index), so ALLD = 0b11111 = 31 and TFT = 0b00101 = 5.

export type Action = 0 | 1;
export type Genome = number; // 0..31

export const T = 5, R = 3, P = 1, S = 0;
export const N_BITS = 5;
export const N_GENOMES = 32;
export const ROUNDS = 150;

/** PAYOFF[2*own + opp] = own payoff. */
export const PAYOFF_OWN = [R, S, T, P] as const;

export const OUTCOMES = ['CC', 'CD', 'DC', 'DD'] as const;

export const NAMED: ReadonlyArray<readonly [string, Genome]> = [
  ['ALLC', 0b00000],
  ['ALLD', 0b11111],
  ['TFT', 0b00101],
  ['PAVLOV', 0b00110],
  ['GRIM', 0b00111],
  ['STFT', 0b10101],
];
export const NAMED_NAMES = NAMED.map(([n]) => n);
/** Columns of the history, as main.COLUMNS. */
export const COLUMNS = [...NAMED_NAMES, 'OTHER'] as const;

const NAME_OF = new Map<Genome, string>(NAMED.map(([n, g]) => [g, n]));
export const genomeOfName = (name: string): Genome | undefined =>
  NAMED.find(([n]) => n === name)?.[1];

/** Bit i (0 = first move, 1..4 = after CC, CD, DC, DD) of a genome. */
export const bit = (g: Genome, i: number): Action => ((g >> (N_BITS - 1 - i)) & 1) as Action;
export const bits = (g: Genome): Action[] => [0, 1, 2, 3, 4].map((i) => bit(g, i));
export const fromBits = (b: ReadonlyArray<number>): Genome => b.reduce<number>((a, x) => a * 2 + (x ? 1 : 0), 0);
export const bitString = (g: Genome): string => bits(g).join('');

/** Named label, or "OTHER" (for frequency charts). */
export const classify = (g: Genome): string => NAME_OF.get(g) ?? 'OTHER';
/** Named label, or the bit string (for display). */
export const label = (g: Genome): string => NAME_OF.get(g) ?? bitString(g);
export const isNamed = (g: Genome): boolean => NAME_OF.has(g);

export const ALL_GENOMES: Genome[] = Array.from({ length: N_GENOMES }, (_, i) => i);

export const actionChar = (a: Action): 'C' | 'D' => (a ? 'D' : 'C');
