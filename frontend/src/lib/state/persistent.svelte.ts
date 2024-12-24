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

export const theme = new PersistentState<"system" | "light" | "dark">("theme", "system");
