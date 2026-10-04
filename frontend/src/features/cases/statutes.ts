/** A statute as the backend names it -> as a student writes it. */
const NAMES: Record<string, (number: string) => string> = {
  RA: (n) => `Republic Act No. ${n}`,
  EO: (n) => `Executive Order No. ${n}`,
  BP: (n) => `Batas Pambansa Blg. ${n}`,
  CA: (n) => `Commonwealth Act No. ${n}`,
  CONST: (n) => `Constitution, ${n}`,
}

export function statuteLabel(type: string, number: string): string {
  return (NAMES[type] ?? ((n: string) => `${type} ${n}`))(number)
}
