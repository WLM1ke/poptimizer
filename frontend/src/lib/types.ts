export interface Security {
	lot: number;
	price: number;
	turnover: number;
}

export interface Account {
	cash: number;
	positions: Record<string, number>;
}

export interface Portfolio {
	accounts: Record<string, Account>;
	securities: Record<string, Security>;
}
