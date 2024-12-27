class PersistentTheme {
	private state: "system" | "light" | "dark" = $state("system");
	private key = "theme";

	loadFromLocalStorage = () => {
		const saved: string = localStorage[this.key];
		this.state = saved ? JSON.parse(saved) : this.state;
	};
	toggle = () => {
		const current = this.state;
		this.state = current === "system" ? "light" : current === "light" ? "dark" : "system";
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
		this.state = initial;
	}

	loadFromLocalStorage = () => {
		const saved: string = localStorage[this.key];
		this.state = saved ? JSON.parse(saved) : this.state;
	};

	toggle = () => {
		localStorage[this.key] = JSON.stringify(!this.state);
		this.state = !this.state;
	};

	get = () => {
		return this.state;
	};
}

export const theme = new PersistentTheme();

export const portSortByValue = new PersistentToggle("portfolio_sort_by_value", true);

export const accSortByValue = new PersistentToggle("accounts_sort_by_value", false);
export const accHideZeroPositions = new PersistentToggle("accounts_hide_zero_positions", false);

let loaded = $state(false);

export const loadSettingsFromLocalStorage = () => {
	if (loaded) {
		return;
	}

	theme.loadFromLocalStorage();
	portSortByValue.loadFromLocalStorage();
	accSortByValue.loadFromLocalStorage();
	accHideZeroPositions.loadFromLocalStorage();

	loaded = true;
};
