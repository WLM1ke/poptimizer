interface Alert {
	id: number;
	msg: string;
	info: boolean;
}

const removeDelay = 30000;

class Alerts {
	private alerts = $state<Array<Alert>>([]);
	private id = $state(0);

	get = () => {
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
