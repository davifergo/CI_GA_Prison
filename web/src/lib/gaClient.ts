// Promise wrapper around ga.worker.ts. Requests to one worker are answered in order.
import type { WorkerRequest, WorkerResponse } from './ga.worker';
import GAWorker from './ga.worker?worker';

export class GAClient {
  private worker = new GAWorker();
  private queue: ((m: WorkerResponse) => void)[] = [];
  onProgress: (done: number, total: number) => void = () => {};

  constructor() {
    this.worker.onmessage = (ev: MessageEvent<WorkerResponse>) => {
      if (ev.data.type === 'progress') return this.onProgress(ev.data.done, ev.data.total);
      this.queue.shift()?.(ev.data);
    };
  }

  request<T extends WorkerResponse['type']>(msg: WorkerRequest): Promise<Extract<WorkerResponse, { type: T }>> {
    return new Promise((resolve) => {
      this.queue.push(resolve as (m: WorkerResponse) => void);
      this.worker.postMessage(msg);
    });
  }

  /** Fire-and-forget (no reply). */
  send(msg: WorkerRequest): void {
    this.worker.postMessage(msg);
  }

  terminate(): void {
    this.worker.terminate();
  }
}
