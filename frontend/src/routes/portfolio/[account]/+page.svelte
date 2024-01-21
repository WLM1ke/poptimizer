<script lang="ts">
	import { invalidateAll } from "$app/navigation";
	import { Card, CardMain, CardSecondary } from "$lib/components/base/card";
	import {
		Table,
		TableBody,
		TableEmptyCell,
		TableHead,
		TableHeadCell,
		TableInputCell,
		TableNumberCell,
		TableRow,
		TableTickerCell
	} from "$lib/components/base/table";
	import { accountView } from "$lib/stores/accountView";

	let cash: number;
	let page = "";

	$: {
		if (page != $accountView.name) {
			cash = $accountView.cash;
			page = $accountView.name;
		}
	}

	interface FormEvent {
		target: EventTarget | null;
	}
	const onChange = async (event: FormEvent, ticker: string) => {
		const target = event.target as HTMLInputElement;
		if (!(await $accountView.updatePosition(ticker, target.value))) {
			await invalidateAll();
			cash = $accountView.cash;
		}
	};
</script>

<Card>
	<CardSecondary>
		Date: {$accountView.timestamp}
	</CardSecondary>
	<CardMain>
		Value: {$accountView.value.toLocaleString(undefined, {
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		})} &#8381;
	</CardMain>
	<CardSecondary>
		Positions: {$accountView.positionsCount} / {$accountView.positions.length}
	</CardSecondary>
</Card>

<Table>
	<TableHead>
		<TableHeadCell>Ticker</TableHeadCell>
		<TableHeadCell>Shares</TableHeadCell>
		<TableHeadCell>Lot</TableHeadCell>
		<TableHeadCell>Price</TableHeadCell>
		<TableHeadCell>Value</TableHeadCell>
	</TableHead>
	<TableBody>
		<TableRow>
			<TableTickerCell ticker="Cash" />
			<TableInputCell
				bind:value={cash}
				on:change={(event) => {
					onChange(event, "CASH");
				}}
			/>
			<TableEmptyCell />
			<TableEmptyCell />
			<TableNumberCell value={$accountView.cash} />
		</TableRow>
		{#each $accountView.positions as position (position.ticker)}
			<TableRow>
				<TableTickerCell ticker={position.ticker} />
				<TableInputCell
					bind:value={position.shares}
					on:change={(event) => {
						onChange(event, position.ticker);
					}}
				/>
				<TableNumberCell value={position.lot} />
				<TableNumberCell value={position.price} />
				<TableNumberCell value={position.value} fractionDigits={0} />
			</TableRow>
		{/each}
	</TableBody>
</Table>
