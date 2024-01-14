import { persistent } from "$lib/stores/persistent";

interface settingsInterface {
	portfolio: {
		sortByValue: boolean;
		hideZeroPositions: boolean;
	};
	accounts: {
		sortByValue: boolean;
		hideZeroPositions: boolean;
	};
}

const defaultSettings: settingsInterface = {
	portfolio: {
		sortByValue: true,
		hideZeroPositions: true
	},
	accounts: {
		sortByValue: false,
		hideZeroPositions: false
	}
};

export const settings = persistent<settingsInterface>("settings", defaultSettings);
