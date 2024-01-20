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
	import { accountView, type AccountPosition } from "$lib/stores/portfolio";
	import { accountsHideZeroPositions, accountsSortByValue } from "$lib/stores/settings";

	let cash: number = $accountView.cash;

	const compTickers = (a: AccountPosition, b: AccountPosition) => {
		return a.ticker.localeCompare(b.ticker);
	};
	const compValue = (a: AccountPosition, b: AccountPosition) => {
		return b.value - a.value;
	};
	const preparePositions = (positions: AccountPosition[]) => {
		const filtered = positions.filter((pos) => pos.value !== 0 || !$accountsHideZeroPositions);
		filtered.sort($accountsSortByValue ? compValue : compTickers);
		cash = $accountView.cash;

		return filtered;
	};

	interface FormEvent {
		target: EventTarget | null;
	}
	const onChange = async (event: FormEvent, ticker: string) => {
		const target = event.target as HTMLInputElement;
		if (!(await $accountView.updatePosition(ticker, target.value))) {
			await invalidateAll();
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
			<TableInputCell>
				<input
					bind:value={cash}
					on:change={(event) => {
						onChange(event, "CASH");
					}}
					class="border-bg-accent bg-bg-main rounded-md border p-1"
					type="text"
				/>
			</TableInputCell>
			<TableEmptyCell />
			<TableEmptyCell />
			<TableNumberCell value={cash} />
		</TableRow>
		{#each preparePositions($accountView.positions) as position (position.ticker)}
			<TableRow>
				<TableTickerCell ticker={position.ticker} />
				<TableInputCell>
					<input
						bind:value={position.shares}
						on:change={(event) => {
							onChange(event, position.ticker);
						}}
						class="border-bg-accent bg-bg-main rounded-md border p-1"
						type="text"
					/>
				</TableInputCell>
				<TableNumberCell value={position.lot} />
				<TableNumberCell value={position.price} />
				<TableNumberCell value={position.value} fractionDigits={0} />
			</TableRow>
		{/each}
	</TableBody>
</Table>
