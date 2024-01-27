import { persistent } from "$lib/stores/persistent";
import { derived } from "svelte/store";
import { fetchPortfolioAPI, portfolio } from "$lib/stores/portfolio";

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

const settings = persistent<settingsInterface>("settings", defaultSettings);

export const portfolioSortByValue = derived(settings, (settings) => settings.portfolio.sortByValue);
export const togglePortfolioSortByValue = () => {
	settings.update((settings) => {
		settings.portfolio.sortByValue = !settings.portfolio.sortByValue;

		return settings;
	});
};

export const portfolioHideZeroPositions = derived(settings, (settings) => settings.portfolio.hideZeroPositions);
export const togglePortfolioHideZeroPositions = () => {
	settings.update((settings) => {
		settings.portfolio.hideZeroPositions = !settings.portfolio.hideZeroPositions;

		return settings;
	});
};

export const accountsSortByValue = derived(settings, (settings) => settings.accounts.sortByValue);
export const toggleAccountsSortByValue = () => {
	settings.update((settings) => {
		settings.accounts.sortByValue = !settings.accounts.sortByValue;

		return settings;
	});
};

export const accountsHideZeroPositions = derived(settings, (settings) => settings.accounts.hideZeroPositions);
export const toggleAccountsHideZeroPositions = () => {
	settings.update((settings) => {
		settings.accounts.hideZeroPositions = !settings.accounts.hideZeroPositions;

		return settings;
	});
};

export const removeAccount = async (account: string) => {
	return await fetchPortfolioAPI(`/api/portfolio/${account}`, "DELETE");
};
export const createAccount = async (account: string) => {
	account = account[0].toUpperCase() + account.substring(1);
	return await fetchPortfolioAPI(`/api/portfolio/${account}`, "POST");
};

export const accounts = derived(portfolio, (portfolio) => {
	return Object.keys(portfolio.accounts).toSorted();
});