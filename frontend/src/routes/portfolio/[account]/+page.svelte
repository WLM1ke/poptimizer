<script lang="ts">
	import Card from "$lib/components/Card.svelte";
	import { Table, EmptyCell, InputCell, NumberCell, TableRow, TextCell } from "$lib/components/table";
	import { formatNumber } from "$lib/format.js";
	import { type PageData } from "./$types";

	let { data }: { data: PageData } = $props();
	const account = $derived(data.account);

	interface FormEvent {
		target: EventTarget | null;
	}
	const onChange = async (event: FormEvent, ticker: string) => {
		const target = event.target as HTMLInputElement;
		await account.updatePosition(ticker, target.value);
	};
</script>

<Card
	upper={`Date: ${account.day}`}
	main={`Value: ${formatNumber(account.value, 0)} ₽`}
	lower={`Positions: ${account.posCount} / ${account.posTotal}`}
/>
<Table headers={["Ticker", "Shares", "Lot", "Price", "Value"]}>
	{#snippet rows()}
		<TableRow>
			{#snippet cells()}
				<TextCell text="Cash" />
				<InputCell
					bind:value={account.cash}
					onchange={(event) => {
						onChange(event, "CASH");
					}}
				/>
				<EmptyCell />
				<EmptyCell />
				<NumberCell value={account.cash} />
			{/snippet}
		</TableRow>
		{#each account.positions as position (position.ticker)}
			<TableRow>
				{#snippet cells()}
					<TextCell text={position.ticker} />
					<InputCell
						step={position.lot}
						bind:value={position.shares}
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
