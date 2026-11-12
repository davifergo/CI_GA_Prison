// Settings shared by all views. The memory length is kept in the URL (#view?m=2) so that
// links can be shared.

export type Memory = 1 | 2;

const read = (): Memory => (new URLSearchParams(location.hash.split('?')[1] ?? '').get('m') === '2' ? 2 : 1);

export const settings = $state({ memory: read() as Memory });

export function setMemory(m: Memory): void {
  settings.memory = m;
  const [view] = location.hash.replace(/^#\/?/, '').split('?');
  history.replaceState(null, '', `#${view || 'court'}${m === 2 ? '?m=2' : ''}`);
}

addEventListener('hashchange', () => { settings.memory = read(); });
