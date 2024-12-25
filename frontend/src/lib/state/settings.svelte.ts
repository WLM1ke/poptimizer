class PersistentState<T> {
	state = $state<T>();
	key = "";

	constructor(key: string, initial: T) {
		this.key = key;
		const saved: string = localStorage[key];
		this.state = saved ? JSON.parse(saved) : initial;
	}

	set = (value: T) => {
		localStorage[this.key] = JSON.stringify(value);
		this.state = value;
	};
	get = () => {
		return this.state!;
	};
}

class PersistentToggle {
	state = $state(true);
	key = "";

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

export const theme = new PersistentState<"system" | "light" | "dark">("theme", "system");

export const portfolioSortByValue = new PersistentToggle("portfolio_sort_by_value", true);
export const portfolioHideZeroPositions = new PersistentToggle("portfolio_hide_zero_positions", true);

export const accountsSortByValue = new PersistentToggle("accounts_sort_by_value", false);
export const accountsHideZeroPositions = new PersistentToggle("accounts_hide_zero_positions", false);
