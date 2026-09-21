export function formatearMmss(segundos: number): string {
  return `${String(Math.floor(segundos / 60)).padStart(2, '0')}:${String(segundos % 60).padStart(2, '0')}`;
}

export function segundosRestantesHasta(fechaIso: string): number {
  return Math.max(0, Math.round((Date.parse(fechaIso) - Date.now()) / 1000));
}
