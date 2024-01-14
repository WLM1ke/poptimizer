import { writable, type Updater } from "svelte/store";

export const persistent = <T>(key: string, initial: T) => {
	const saved = localStorage[key];
	if (!saved) {
		localStorage[key] = JSON.stringify(initial);
	}

	const { subscribe, set, update } = writable<T>(saved ? JSON.parse(saved) : initial);

	return {
		subscribe,
		set: (value: T) => {
			set(value);
		},
		update: (updater: Updater<T>) => {
			update((value: T) => {
				const newValue = updater(value);
				localStorage[key] = JSON.stringify(newValue);

				return newValue;
			});
		}
	};
};
