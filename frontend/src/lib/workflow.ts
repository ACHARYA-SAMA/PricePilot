export type Work = (label: string, task: () => Promise<void>) => Promise<void>
export interface WorkProps { busy: boolean; work: Work }
