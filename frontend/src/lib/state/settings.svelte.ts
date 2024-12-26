class PersistentTheme {
	private state: "system" | "light" | "dark" = $state("system");
	private key = "theme";

	toggle = () => {
		const current = this.state;
		this.state = current === "system" ? "light" : current === "light" ? "dark" : "system";
		localStorage[this.key] = JSON.stringify(this.state);
	};
	get = () => {
		const saved: string = localStorage[this.key];
		this.state = saved ? JSON.parse(saved) : this.state;

		return this.state;
	};
}

class PersistentToggle {
	private state = $state(true);
	private key = "";

	constructor(key: string, initial: boolean) {
		this.key = key;
		this.state = initial;
	}

	toggle = () => {
		localStorage[this.key] = JSON.stringify(!this.state);
		this.state = !this.state;
	};

	get = () => {
		const saved: string = localStorage[this.key];
		this.state = saved ? JSON.parse(saved) : this.state;

		return this.state;
	};
}

export const theme = new PersistentTheme();

export const portfolioSortByValue = new PersistentToggle("portfolio_sort_by_value", true);

export const accountsSortByValue = new PersistentToggle("accounts_sort_by_value", false);
export const accountsHideZeroPositions = new PersistentToggle("accounts_hide_zero_positions", false);
