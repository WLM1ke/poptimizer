import { persistent } from "$lib/stores/persistent";

interface settingsInterface {
	portfolio: {
		sortByValue: boolean;
		hideZeroPositions: boolean;
	};
}

const defaultSettings: settingsInterface = {
	portfolio: {
		sortByValue: true,
		hideZeroPositions: true
	}
};

export const settings = persistent<settingsInterface>("settings", defaultSettings);
