<!-- <script lang="ts">
	import {
		Table,
		TableRow,
		TextCell,
		NumberCell,
		AddCell,
		DeleteCell,
		InputCell,
		InputTextCell
	} from "$lib/components/table";
	import Button from "$lib/components/Button.svelte";
	import { invalidate } from "$app/navigation";
	import { put } from "$lib/request.js";
	import { alerts } from "$lib/state/alerts.svelte";

	export let data;

	let ticker: string;
	let day: string;
	let dividend: number;
	let maxFractionDigits: number;

	$: {
		if (ticker != data.ticker) {
			ticker = data.ticker;
			day = data.dividends[data.dividends.length - 1].day;
			dividend = data.dividends[data.dividends.length - 1].dividend;
			maxFractionDigits = Math.max(...data.dividends.map((currentValue) => fractionDigits(currentValue.dividend)));
		}
	}

	const fractionDigits = (num: number) => {
		const numString = num.toString();
		const pointPos = numString.indexOf(".");

		if (pointPos === -1) {
			return 0;
		}

		return numString.length - pointPos - 1;
	};

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
			alerts.addAlert("Dividend should be number");
			return;
		}
		const date = new Date(day);
		if (date.toString() === "Invalid Date") {
			alerts.addAlert("Invalid Date");
			return;
		}
		data.dividends = [
			...data.dividends,
			{
				day: date.toISOString().slice(0, 10),
				dividend: dividend,
				status: "extra"
			}
		];
	};
	const save = async () => {
		await put(fetch, `/api/dividends/${data.ticker}`, {
			dividends: data.dividends
				.filter(({ status }) => {
					return status === "ok" || status === "extra";
				})
				.map(({ day, dividend }) => {
					return { day, dividend };
				})
				.toSorted((a, b) => {
					return a.day !== b.day ? a.day.localeCompare(b.day) : a.dividend - b.dividend;
				})
		});
		await invalidate((url) => url.pathname.startsWith("/api/dividends"));
	};
</script>

<Table headers={["Day", "Dividend", "Status"]}>
	{#snippet rows()}
		{#each data.dividends as dividend, index (index)}
			{#if dividend.status === "ok"}
				<TableRow>
					{#snippet cells()}
						<TextCell text={dividend.day} />
						<NumberCell value={dividend.dividend} fractionDigits={maxFractionDigits} />
						<TextCell text="OK" center={true} />
					{/snippet}
				</TableRow>
			{:else if dividend.status === "extra"}
				<TableRow>
					{#snippet cells()}
						<TextCell text={dividend.day} />
						<NumberCell value={dividend.dividend} fractionDigits={maxFractionDigits} />
						<DeleteCell onclick={() => toggleRow(index)} />
					{/snippet}
				</TableRow>
			{:else if dividend.status === "missed"}
				<TableRow muted>
					{#snippet cells()}
						<TextCell text={dividend.day} />
						<NumberCell value={dividend.dividend} fractionDigits={maxFractionDigits} />
						<AddCell onclick={() => toggleRow(index)} />
					{/snippet}
				</TableRow>
			{/if}
		{/each}
		<TableRow muted>
			{#snippet cells()}
				<InputTextCell bind:value={day} />
				<InputCell bind:value={dividend} />
				<AddCell onclick={() => addRow()} />
			{/snippet}
		</TableRow>
	{/snippet}
</Table>
<Button label="Save" onclick={save} /> -->
