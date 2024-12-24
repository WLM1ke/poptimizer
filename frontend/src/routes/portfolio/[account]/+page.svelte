<script lang="ts">
	import Card from "$lib/components/Card.svelte";
	import { Table, EmptyCell, InputCell, NumberCell, TableRow, TextCell } from "$lib/components/table";
	import { formatNumber } from "$lib/format.js";
	import { accountViewFn } from "$lib/stores/accountViewFn";

	export let data;

	$: accountView = $accountViewFn(data.accountName);

	let account = "";
	let positions: Record<string, number> = { CASH: 0 };
	const setFields = () => {
		positions = { CASH: accountView.cash };
		accountView.positions.forEach((pos) => (positions[pos.ticker] = pos.shares));
	};

	$: {
		if (account != accountView.name) {
			account = accountView.name;
			setFields();
		}
	}

	interface FormEvent {
		target: EventTarget | null;
	}
	const onChange = async (event: FormEvent, ticker: string) => {
		const target = event.target as HTMLInputElement;
		await accountView.updatePosition(ticker, target.value);
		setFields();
	};
</script>

<Card
	upper={`Date: ${accountView.day}`}
	main={`Value: ${formatNumber(accountView.value)} ₽`}
	lower={`Positions: ${accountView.positionsCount} / ${accountView.positionsTotal}`}
/>
<Table headers={["Ticker", "Shares", "Lot", "Price", "Value"]}>
	{#snippet rows()}
		<TableRow>
			{#snippet cells()}
				<TextCell text="Cash" />
				<InputCell
					bind:value={positions["CASH"]}
					onchange={(event) => {
						onChange(event, "CASH");
					}}
				/>
				<EmptyCell />
				<EmptyCell />
				<NumberCell value={accountView.cash} />
			{/snippet}
		</TableRow>
		{#each accountView.positions as position (position.ticker)}
			<TableRow>
				{#snippet cells()}
					<TextCell text={position.ticker} />
					<InputCell
						step={position.lot}
						bind:value={positions[position.ticker]}
						onchange={(event) => {
							onChange(event, position.ticker);
						}}
					/>
					<NumberCell value={position.lot} />
					<NumberCell value={position.price} />
					<NumberCell value={position.value} fractionDigits={0} />
				{/snippet}
			</TableRow>
		{/each}
	{/snippet}
</Table>
