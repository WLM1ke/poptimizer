<script lang="ts">
	import {
		Table,
		TableHead,
		HeadCell,
		TableBody,
		TableRow,
		TextCell,
		NumberCell,
		AddCell,
		DeleteCell,
		InputCell,
		InputTextCell,
		InputSelectCell
	} from "$lib/components/base/table";
	import Button from "$lib/components/base/Button.svelte";
	import { addAlert } from "$lib/stores/alerts";
	import { invalidate } from "$app/navigation";

	export let data;

	let day = data.dividends[data.dividends.length - 1].day;
	let dividend = data.dividends[data.dividends.length - 1].dividend;
	let currency = data.dividends[data.dividends.length - 1].currency.toLocaleUpperCase();

	const toggleRow = (index: number) => {
		switch (data.dividends[index].status) {
			case "extra":
				data.dividends[index].status = "missed";
				break;
			case "missed":
				data.dividends[index].status = "extra";
		}
	};
	const addRow = () => {
		if (typeof dividend !== "number") {
			addAlert({
				info: false,
				msg: "Dividend should be number"
			});
			return;
		}
		const date = new Date(day);
		if (date.toString() === "Invalid Date") {
			addAlert({
				info: false,
				msg: "Invalid Date"
			});
			return;
		}
		const currencyLower = currency.toLocaleLowerCase();
		if (currencyLower != "rur" && currencyLower != "usd") {
			addAlert({
				info: false,
				msg: "Invalid currency"
			});
			return;
		}
		data.dividends = [
			...data.dividends,
			{
				day: date.toISOString().slice(0, 10),
				dividend: dividend,
				currency: currencyLower,
				status: "extra"
			}
		];
	};
	const save = async () => {
		try {
			const res = await fetch(`/api/dividends/${data.ticker}`, {
				method: "PUT",
				body: JSON.stringify({
					dividends: data.dividends
						.filter(({ status }) => {
							return status === "ok" || status === "extra";
						})
						.map(({ day, dividend, currency }) => {
							return { day, dividend, currency };
						})
						.toSorted((a, b) => {
							return a.day !== b.day
								? a.day.localeCompare(b.day)
								: a.dividend !== b.dividend
									? a.dividend - b.dividend
									: a.currency.localeCompare(b.currency);
						})
				})
			});
			if (!res.ok) {
				throw new Error(await res.text());
			}
			invalidate(`/api/dividends/${data.ticker}`);
		} catch (err) {
			let msg: string;
			if (err instanceof Error) {
				msg = err.message;
			} else {
				msg = JSON.stringify(err);
			}
			addAlert({
				info: false,
				msg: msg
			});
			invalidate(`/api/dividends/${data.ticker}`);
		}
	};
</script>

<Table>
	<TableHead>
		<HeadCell>Day</HeadCell>
		<HeadCell>Dividend</HeadCell>
		<HeadCell>Currency</HeadCell>
		<HeadCell>Status</HeadCell>
	</TableHead>
	<TableBody>
		{#each data.dividends as dividend, index (index)}
			{#if dividend.status === "ok"}
				<TableRow>
					<TextCell text={dividend.day} />
					<NumberCell value={dividend.dividend} />
					<TextCell text={dividend.currency.toUpperCase()} center={true} />
					<TextCell text="OK" center={true} />
				</TableRow>
			{:else if dividend.status === "extra"}
				<TableRow>
					<TextCell text={dividend.day} />
					<NumberCell value={dividend.dividend} />
					<TextCell text={dividend.currency.toUpperCase()} center={true} />
					<DeleteCell on:click={() => toggleRow(index)} />
				</TableRow>
			{:else if dividend.status === "missed"}
				<TableRow muted>
					<TextCell text={dividend.day} />
					<NumberCell value={dividend.dividend} />
					<TextCell text={dividend.currency.toUpperCase()} center={true} />
					<AddCell on:click={() => toggleRow(index)} />
				</TableRow>
			{/if}
		{/each}
		<TableRow muted>
			<InputTextCell bind:value={day} />
			<InputCell bind:value={dividend} />
			<InputSelectCell bind:value={currency} options={["RUR", "USD"]} />
			<AddCell on:click={() => addRow()} />
		</TableRow>
	</TableBody>
</Table>
<Button label="Save" on:click={save} />
