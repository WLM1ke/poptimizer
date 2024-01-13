import { readonly, writable } from "svelte/store";

interface Alert {
	id: number;
	info: boolean;
	msg: string;
}

const _alerts = writable<Array<Alert>>([]);
const removeDelay = 30000;
const removeAlert = (id: number) => _alerts.update((alerts) => alerts.filter((alert) => alert.id !== id));

export const addAlert = (alert: Omit<Alert, "id">) =>
	_alerts.update((alerts) => {
		const id = alerts.length > 0 ? alerts[alerts.length - 1].id + 1 : 0;
		setTimeout(() => removeAlert(id), removeDelay);

		return [...alerts, { ...alert, id }];
	});

export const alerts = readonly<Array<Alert>>(_alerts);
