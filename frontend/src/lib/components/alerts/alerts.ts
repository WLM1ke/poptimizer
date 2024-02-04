import { writable } from "svelte/store";

interface Alert {
	id: number;
	info: boolean;
	msg: string;
}

export const alerts = writable<Array<Alert>>([]);
const removeDelay = 30000;
const removeAlert = (id: number) => alerts.update((alerts) => alerts.filter((alert) => alert.id !== id));

export const addAlert = (msg: string) =>
	alerts.update((alerts) => {
		const info = false;
		const id = alerts.length > 0 ? alerts[0].id - 1 : 0;
		setTimeout(() => removeAlert(id), removeDelay);

		return [{ msg, id, info }, ...alerts];
	});

export const addInfo = (msg: string) =>
	alerts.update((alerts) => {
		const info = true;
		const id = alerts.length > 0 ? alerts[0].id - 1 : 0;
		setTimeout(() => removeAlert(id), removeDelay);

		return [{ msg, id, info }, ...alerts];
	});
