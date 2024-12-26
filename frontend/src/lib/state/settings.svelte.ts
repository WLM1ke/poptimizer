class PersistentTheme {
	private state: "system" | "light" | "dark" = $state("system");
	private key = "theme";

	constructor() {
		const saved: string = localStorage[this.key];
		this.state = saved ? JSON.parse(saved) : this.state;
	}

	toggle = () => {
		this.state = this.state === "system" ? "light" : this.state === "light" ? "dark" : "system";
		localStorage[this.key] = JSON.stringify(this.state);
	};
	get = () => {
		return this.state;
	};
}

class PersistentToggle {
	private state = $state(true);
	private key = "";

	constructor(key: string, initial: boolean) {
		this.key = key;
		const saved: string = localStorage[key];
		this.state = saved ? JSON.parse(saved) : initial;
	}

	toggle = () => {
		localStorage[this.key] = JSON.stringify(!this.state);
		this.state = !this.state;
	};

	get = () => {
		return this.state;
	};
}

export const theme = new PersistentTheme();

export const portfolioSortByValue = new PersistentToggle("portfolio_sort_by_value", true);

export const accountsSortByValue = new PersistentToggle("accounts_sort_by_value", false);
export const accountsHideZeroPositions = new PersistentToggle("accounts_hide_zero_positions", false);
