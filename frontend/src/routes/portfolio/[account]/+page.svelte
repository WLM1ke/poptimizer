<script lang="ts">
	import { Card, CardMain, CardSecondary } from "$lib/components/card";
	import {
		Table,
		TableBody,
		EmptyCell,
		TableHead,
		HeadCell,
		InputCell,
		NumberCell,
		TableRow,
		TextCell
	} from "$lib/components/table";
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

<Card>
	<CardSecondary>
		Date: {accountView.day}
	</CardSecondary>
	<CardMain>
		Value: {accountView.value.toLocaleString(undefined, {
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		})} &#8381;
	</CardMain>
	<CardSecondary>
		Positions: {accountView.positionsCount} / {accountView.positionsTotal}
	</CardSecondary>
</Card>

<Table>
	<TableHead>
		<HeadCell>Ticker</HeadCell>
		<HeadCell>Shares</HeadCell>
		<HeadCell>Lot</HeadCell>
		<HeadCell>Price</HeadCell>
		<HeadCell>Value</HeadCell>
	</TableHead>
	<TableBody>
		<TableRow>
			<TextCell text="Cash" />
			<InputCell
				bind:value={positions["CASH"]}
				on:change={(event) => {
					onChange(event, "CASH");
				}}
			/>
			<EmptyCell />
			<EmptyCell />
			<NumberCell value={accountView.cash} />
		</TableRow>
		{#each accountView.positions as position (position.ticker)}
			<TableRow>
				<TextCell text={position.ticker} />
				<InputCell
					step={position.lot}
					bind:value={positions[position.ticker]}
					on:change={(event) => {
						onChange(event, position.ticker);
					}}
				/>
				<NumberCell value={position.lot} />
				<NumberCell value={position.price} />
				<NumberCell value={position.value} fractionDigits={0} />
			</TableRow>
		{/each}
	</TableBody>
</Table>
