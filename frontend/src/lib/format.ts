export const formatPercent = (num: number, digits: number | undefined = 1) =>
	num.toLocaleString("RU", {
		style: "percent",
		minimumFractionDigits: digits,
		maximumFractionDigits: digits
	});

export const formatNumber = (num: number, digits: number | undefined = undefined) =>
	num.toLocaleString("RU", {
		minimumFractionDigits: digits,
		maximumFractionDigits: digits
	});
