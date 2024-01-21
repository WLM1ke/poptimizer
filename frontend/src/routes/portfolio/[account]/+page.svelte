<script lang="ts">
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

	let account = "";
	let positions: Record<string, number> = { CASH: 0 };
	const setFields = () => {
		positions = { CASH: $accountView.cash };
		$accountView.positions.forEach((pos) => (positions[pos.ticker] = pos.shares));
	};

	$: {
		if (account != $accountView.name) {
			account = $accountView.name;
			setFields();
		}
	}

	interface FormEvent {
		target: EventTarget | null;
	}
	const onChange = async (event: FormEvent, ticker: string) => {
		const target = event.target as HTMLInputElement;
		await $accountView.updatePosition(ticker, target.value);
		setFields();
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
		Positions: {$accountView.positionsCount} / {$accountView.positionsTotal}
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
				bind:value={positions["CASH"]}
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
					bind:value={positions[position.ticker]}
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
