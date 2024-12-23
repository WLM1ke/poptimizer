interface Alert {
	id: number;
	msg: string;
	info: boolean;
}

const removeDelay = 30000;

class Alerts {
	alerts = $state<Array<Alert>>([]);
	id = $state(0);

	public getAlerts = () => {
		return this.alerts;
	};

	addAlert = (msg: string) => {
		this.id = this.id + 1;
		this.alerts.push({ id: this.id, msg, info: false });
		setTimeout(() => this.alerts.shift(), removeDelay);
	};
	addInfo = (msg: string) => {
		this.id = this.id + 1;
		this.alerts.push({ id: this.id, msg, info: true });
		setTimeout(() => this.alerts.shift(), removeDelay);
	};
}

export const alerts = new Alerts();
