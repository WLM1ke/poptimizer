interface Alert {
	id: number;
	info: boolean;
	msg: string;
}

let alerts = $state<Array<Alert>>([]);
const removeDelay = 30000;
const removeAlert = (id: number) => {
	alerts.filter((alert) => alert.id !== id);
};

export const addAlert = (msg: string) => {
	const info = false;
	const id = alerts.length > 0 ? alerts[0].id - 1 : 0;
	setTimeout(() => removeAlert(id), removeDelay);

	alerts = [{ msg, id, info }, ...alerts];
};

export const addInfo = (msg: string) => {
	const info = true;
	const id = alerts.length > 0 ? alerts[0].id - 1 : 0;
	setTimeout(() => removeAlert(id), removeDelay);

	alerts = [{ msg, id, info }, ...alerts];
};

export const getAlerts = () => alerts;
