import { writable } from "svelte/store";

const errors = writable<Array<string>>([]);

export const addError = (err: string) => errors.update((errs) => [...errs, err]);
