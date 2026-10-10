import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { emptyAccount } from './broker.mjs';

export function createStore(filePath) {
  let queue = Promise.resolve();
  let memory = null;

  async function load() {
    if (memory) return memory;
    try {
      memory = JSON.parse(await readFile(filePath, 'utf8'));
    } catch {
      memory = emptyAccount();
      await persist();
    }
    return memory;
  }

  async function persist() {
    await mkdir(path.dirname(filePath), { recursive: true });
    await writeFile(filePath, JSON.stringify(memory, null, 2));
  }

  function update(mutator) {
    const run = queue.then(async () => {
      const account = await load();
      const result = await mutator(account);
      await persist();
      return result;
    });
    queue = run.then(
      () => {},
      () => {},
    );
    return run;
  }

  async function read() {
    return update(async (account) => account);
  }

  return { read, update };
}
